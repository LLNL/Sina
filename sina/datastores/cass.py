"""Contains Cassandra-specific implementations of our DAOs."""
import numbers
import logging
# Used for temporary implementation of LIKE-ish functionality
import fnmatch
import six
import collections
from cassandra.cqlengine.query import DoesNotExist, BatchQuery

import sina.dao as dao
import sina.model as model
import sina.datastores.cass_schema as schema

LOGGER = logging.getLogger(__name__)


class RecordDAO(dao.RecordDAO):
    """The DAO specifically responsible for handling Records in Cassandra."""

    def insert(self, record, force_overwrite=False):
        """
        Given a Record, insert it into the current Cassandra database.

        :param record: A Record to insert
        :param force_overwrite: Whether to forcibly overwrite a preexisting
                                record that shares this record's id.
        :raises LWTException: If force_overwrite is False and an entry with the
                              id exists.
        """
        LOGGER.debug('Inserting {} into Cassandra with force_overwrite={}.'
                     .format(record, force_overwrite))
        create = (schema.Record.create if force_overwrite
                  else schema.Record.if_not_exists().create)
        create(record_id=record.record_id,
               record_type=record.record_type,
               raw=record.raw,
               user_defined=record.user_defined)
        if record.values:
            self._insert_values(record_id=record.record_id,
                                values=record.values,
                                force_overwrite=force_overwrite)
        if record.files:
            self._insert_files(record_id=record.record_id,
                               files=record.files,
                               force_overwrite=force_overwrite)

    def insert_many(self, list_to_insert, force_overwrite=False, _type_managed=False):
        """
        Given a list of Records, insert each into Cassandra.

        This method relies heavily on batching--if you're only inserting a few
        records, you may not see performance gains, and may even see some
        slowdowns due to batch logic overhead.

        :param list_to_insert: A list of Records to insert
        :param force_overwrite: Whether to forcibly overwrite a preexisting run
                                that shares this run's id. Currently only used
                                by Cassandra DAOs.
        :param _type_managed: Whether all records inserted are the same type
                              AND insert_many is called from a method that has
                              special handling for this type. See Run's
                              insert_many()
        """
        LOGGER.debug('Inserting {} records to Cassandra with'
                     'force_overwrite={} and _type_managed={}.'
                     .format(len(list_to_insert),
                             force_overwrite,
                             _type_managed))
        # Because batch is done by partition key, we'll need to store info for
        # tables whose full per-partition info isn't supplied by one Record
        from_scalar_batch = collections.defaultdict(list)
        from_value_batch = collections.defaultdict(list)

        for record in list_to_insert:
            # Insert the Record itself
            create = (schema.Record.create if force_overwrite
                      else schema.Record.if_not_exists().create)
            create(record_id=record.record_id,
                   record_type=record.record_type,
                   raw=record.raw,
                   user_defined=record.user_defined)
            if record.values:
                value_from_rec_batch = []
                scalar_from_rec_batch = []
                for value in record.values:
                    tags = [str(x) for x in value['tags']] if 'tags' in value else None
                    if isinstance(value['value'], numbers.Real):
                        from_scalar_batch[value['name']].append((value['value'],
                                                                 record.record_id,
                                                                 value.get('units'),
                                                                 tags))
                        scalar_from_rec_batch.append((value['name'],
                                                      value['value'],
                                                      value.get('units'),
                                                      tags))
                    else:
                        from_value_batch[value['name']].append((value['value'],
                                                                record.record_id,
                                                                value.get('units'),
                                                                tags))
                        value_from_rec_batch.append((value['name'],
                                                     value['value'],
                                                     value.get('units'),
                                                     tags))

                # We've finished this record's values--do the batch inserts
                for table, batchlist in ((schema.ScalarFromRecord, scalar_from_rec_batch),
                                         (schema.ValueFromRecord, value_from_rec_batch)):
                    with BatchQuery() as b:
                        create = (table.batch(b).create if force_overwrite
                                  else table.batch(b).if_not_exists().create)
                        for value in batchlist:
                            create(record_id=record.record_id,
                                   name=value[0],
                                   value=value[1],
                                   units=value[2],
                                   tags=value[3])
            if record.files:
                document_batch = []
                for entry in record.files:
                    # Mimetype and tags can be None, use get() for safety
                    document_batch.append((entry['uri'],
                                           entry.get('mimetype'),
                                           entry.get('tags')))
                table = schema.DocumentFromRecord
                with BatchQuery() as b:
                    create = (table.batch(b).create if force_overwrite
                              else table.batch(b).if_not_exists().create)
                    for doc in document_batch:
                        create(record_id=record.record_id,
                               uri=doc[0],
                               mimetype=doc[1],
                               tags=doc[2])
            if not _type_managed:
                if record.record_type == "run":
                    self.RunDAO._insert_sans_rec(record, force_overwrite)

        # We've gone through every record we were given. The from_scalar_batch
        # and from_value_batch dictionaries are ready for batch inserting.
        for table, batchlist in ((schema.RecordFromScalar, from_scalar_batch),
                                 (schema.RecordFromValue, from_value_batch)):
            for partition, values in six.iteritems(batchlist):
                with BatchQuery() as b:
                    create = (table.batch(b).create if force_overwrite
                              else table.batch(b).if_not_exists().create)
                    for value in values:
                        create(name=partition,
                               value=value[0],
                               record_id=value[1],
                               units=value[2],
                               tags=value[3])

    def _insert_values(self, values, record_id, force_overwrite=False):
        """
        Insert values into two of the four query tables depending on value.

        Values that are numbers (12.0) go in the Scalar tables. Values that
        aren't ("Tuesday","12.0") go in the Value tables.

        :param values: The list of values to insert.
        :param record_id: The Record ID to associate the values to.
        :param force_overwrite: Whether to forcibly overwrite preexisting values.
                                Currently only used by Cassandra DAOs.
        """
        LOGGER.debug('Inserting {} values to Record ID {} and force_overwrite={}.'
                     .format(len(values), record_id, force_overwrite))
        for value in values:
            tags = [str(x) for x in value['tags']] if 'tags' in value else None
            # Check if it's a scalar
            insert_value = (schema.cross_populate_scalar_and_record
                            if isinstance(value['value'], numbers.Real)
                            else schema.cross_populate_value_and_record)
            insert_value(record_id=record_id,
                         name=value['name'],
                         value=value['value'],
                         units=value.get('units'),
                         tags=tags,
                         force_overwrite=True)

    def _insert_files(self, record_id, files, force_overwrite=False):
        """
        Insert files into the DocumentFromRecord table.

        :param record_id: The Record ID to associate the files to.
        :param files: The list of files to insert.
        :param force_overwrite: Whether to forcibly overwrite preexisting files.
                                Currently only used by Cassandra DAOs.
        """
        LOGGER.debug('Inserting {} files to record id={} and force_overwrite={}.'
                     .format(len(files), record_id, force_overwrite))
        create = (schema.DocumentFromRecord.create if force_overwrite
                  else schema.DocumentFromRecord.if_not_exists().create)
        for entry in files:
            create(record_id=record_id,
                   uri=entry['uri'],
                   mimetype=entry.get('mimetype'),
                   tags=entry.get('tags'))

    def get(self, record_id):
        """
        Given a record_id, return match (if any) from Cassandra database.

        :param record_id: The id of the record to return

        :returns: A record matching that id or None
        """
        LOGGER.debug('Getting record with id={}'.format(record_id))
        query = schema.Record.objects.filter(record_id=record_id).get()
        return model.Record(record_id=query.record_id,
                            record_type=query.record_type,
                            raw=query.raw)

    def get_all_of_type(self, record_type):
        """
        Given a type of record, return all Records of that type.

        :param record_type: The type of record to return, ex: run

        :returns: a list of Records of that type
        """
        LOGGER.debug('Getting all records of type {}.'.format(record_type))
        query = (schema.Record.objects.filter(record_type=record_type))
        # TODO: If type query table introduced, change this:
        return [model.Record(record_id=x.record_id,
                             record_type=x.record_type,
                             raw=x.raw) for x in query.allow_filtering().all()]

    def get_given_document_uri(self, uri, accepted_ids_list=None):
        """
        Return all records associated with documents whose uris match some arg.

        Temporary implementation. THIS IS A VERY SLOW, BRUTE-FORCE STRATEGY!
        You use it at your own risk! Do not expect it to be performant or
        particularly stable.

        Supports the use of % as a wildcard character.

        :param uri: The uri to use as a search term, such as "foo.png"
        :param accepted_ids_list: A list of ids to restrict the search to.
                                  If not provided, all ids will be used.

        :returns: A list of matching records (or an empty list)
        """
        LOGGER.debug('Getting all records related to uri={}.'.format(uri))
        if accepted_ids_list:
            LOGGER.debug('Restricting to {} ids.'.format(len(accepted_ids_list)))
        LOGGER.warning('Temporary implementation of getting Records based on '
                       'Document URI. This is a very slow, brute-force '
                       'strategy.')
        base_query = (schema.DocumentFromRecord.objects.allow_filtering()
                      if accepted_ids_list is None else
                      schema.DocumentFromRecord.objects
                      .filter(record_id__in=accepted_ids_list))
        # If there's a wildcard
        if '%' in uri:
            # Special case: get all record_ids with associated docs.
            if len(uri) == 1:
                all_documents = (base_query.all())
                return self.get_many(set(x.record_id for x in all_documents))
            # If a wildcard is in any position besides last, we do it in Python
            if '%' in uri[:-1]:
                matches = set()
                # Change searched URI into a fnmatch-friendly version
                search_uri = uri.replace('*', '[*]').replace('%', '*')
                for entry in base_query.all():
                    if fnmatch.fnmatch(entry.uri, search_uri):
                        matches.add(entry.record_id)
                return self.get_many(matches)

            # As long as the wildcard's in last place, we can do it in CQL
            else:
                # Cassandra orders lexographically by UTF-8
                # Thus, we can search from ex: 'foo' through 'fop' to
                # simulate a 'LIKE foo%' query.
                alphabetical_end = uri[:-2]+chr(ord(uri[-2]) + 1)
                query = (base_query.filter(uri__gte=uri[:-1])
                         .filter(uri__lt=alphabetical_end).all())
                return self.get_many(set(x.record_id for x in query))
        # If no wildcard
        # Note: it's completely possible for multiple documents to have the
        # same URI but different record_ids. Should this be changed?
        return self.get_many([x.record_id for x in
                              base_query.filter(uri=uri).all()])

    def get_given_scalars(self, scalar_range_list):
        """
        Return all records with scalars fulfilling some criteria.

        Note that this is a logical 'and'--the record must satisfy every
        conditional provided (which is also why this can't simply call
        get_given_scalar() as get_many() does with get()).

        :param scalar_range_list: A list of 'sina.ScalarRange's describing the
                                  different criteria.

        :returns: A list of Records fitting the criteria
        """
        LOGGER.debug('Getting all records with scalars within the following '
                     'ranges: {}'.format(scalar_range_list))
        query = schema.RecordFromScalar.objects
        rec_ids = list(self
                       ._configure_query_for_scalar_range(query,
                                                          scalar_range_list[0])
                       .values_list('record_id', flat=True).all())
        for scalar_range in scalar_range_list[1:]:
            query = (schema.ScalarFromRecord.objects
                     .filter(record_id__in=rec_ids))
            query = self._configure_query_for_scalar_range(query, scalar_range)
            rec_ids = list(query.values_list('record_id', flat=True).all())
        return self.get_many(rec_ids)

    def get_given_scalar(self, scalar_range):
        """
        Return all records with scalars fulfilling some criteria.

        :param scalar_range: A 'sina.ScalarRange's describing the
                             different criteria.

        :returns: A list of Records fitting the criteria
        """
        LOGGER.debug('Getting all records with scalars within the range: {}'
                     .format(scalar_range))
        query = schema.RecordFromScalar.objects
        out = self._configure_query_for_scalar_range(query, scalar_range).all()
        if out:
            return self.get_many(x.record_id for x in out)
        else:
            return []

    def _configure_query_for_scalar_range(self, query, scalar_range):
        """
        Use a ScalarRange to build a query.

        Note that this returns a query object, not a completed query. It's
        used by the scalar query methods to build the queries they execute.

        :param query: The query object to consider
        :param scalar_range: The ScalarRange we're building the query from.

        :returns: The query object with scalar_range appropriate filters
                  applied.
        """
        LOGGER.debug('Configuring <query={}> with <scalar_range={}>.'
                     .format(query, scalar_range))
        query = query.filter(name=scalar_range.name)
        if scalar_range.min is not None:
            if scalar_range.min_inclusive:
                query = query.filter(value__gte=scalar_range.min)
            else:
                query = query.filter(value__gt=scalar_range.min)
        if scalar_range.max is not None:
            if scalar_range.max_inclusive:
                query = query.filter(value__lte=scalar_range.max)
            else:
                query = query.filter(value__lt=scalar_range.max)
        return query

    def get_scalars(self, record_id, scalar_names):
        """
        Retrieve scalars for a given record id.

        Scalars are returned in alphabetical order.

        :param record_id: The record id to find scalars for
        :param scalar_names: A list of the names of scalars to return

        :return: A list of scalar JSON objects matching the Mnoda specification
        """
        LOGGER.debug('Getting scalars={} for record id={}'
                     .format(scalar_names, record_id))
        scalars = []
        # Cassandra has special restrictions on list types that prevents us
        # from filtering on IN when they're present in a table. Hence this
        # workaround.
        for name in sorted(scalar_names):
            try:
                entry = (schema.ScalarFromRecord.objects
                         .filter(record_id=record_id)
                         .filter(name=name)
                         .values_list('name', 'value', 'units', 'tags')).get()
                scalars.append({'name': entry[0],
                                'value': entry[1],
                                'units': entry[2],
                                'tags': entry[3]})
            except DoesNotExist:
                # If scalar doesn't exist, continue
                pass
        return scalars

    def get_files(self, record_id):
        """
        Retrieve files for a given record id.

        Files are returned in the alphabetical order of their URIs

        :param record_id: The record id to find files for
        :return: A list of file JSON objects matching the Mnoda specification
        """
        LOGGER.debug('Getting files for record id={}'.format(record_id))
        files = (schema.DocumentFromRecord.objects
                 .filter(record_id=record_id)
                 .values_list('uri', 'mimetype', 'tags')).all()
        return [{'uri': x[0], 'mimetype': x[1], 'tags': x[2]} for x in files]


class RelationshipDAO(dao.RelationshipDAO):
    """The DAO responsible for handling Relationships in Cassandra."""

    def insert(self, relationship=None, subject_id=None,
               object_id=None, predicate=None):
        """
        Given some Relationship, import it into the Cassandra database.

        This can create an entry from either an existing relationship object
        or from its components (subject id, object id, predicate). If all four
        are provided, the Relationship will be used.

        A Relationship describes the connection between two objects in the
        form <subject_id> <predicate> <object_id>, ex:

        Task44 contains Run2001

        :param subject_id: The record_id of the subject.
        :param object_id: The record_id of the object.
        :param predicate: A string describing the relationship.
        :param relationship: A Relationship object to build entry from.

        :raises: A ValueError if neither Relationship nor the subject_id,
                 object_id, and predicate args are provided.
        """
        LOGGER.debug('Inserting relationship={}, subject_id={}, object_id={}, '
                     'and predicate={}.'.format(relationship,
                                                subject_id,
                                                object_id,
                                                predicate))
        if relationship and subject_id and object_id and predicate:
            LOGGER.warning('Given relationship object and '
                           'subject_id/object_id/predicate objects. Using '
                           'relationship.')
        if not (relationship or (subject_id and object_id and predicate)):
            msg = ("Must supply either Relationship or subject_id, "
                   "object_id, and predicate.")
            LOGGER.error(msg)
            raise ValueError(msg)
        if relationship:
            subject_id = relationship.subject_id
            object_id = relationship.object_id
            predicate = relationship.predicate
        schema.cross_populate_object_and_subject(subject_id=subject_id,
                                                 object_id=object_id,
                                                 predicate=predicate)

    def insert_many(self, list_to_insert):
        """
        Given a list of Relationships, insert each into Cassandra.

        This method relies heavily on batching--if you're only inserting a few
        Relationships, you may not see performance gains, and may even see some
        slowdowns due to batch logic overhead.

        :param list_to_insert: A list of Relationships to insert
        """
        LOGGER.debug('Inserting {} relationships.'.format(len(list_to_insert)))
        # Batching is done per partition key--we won't know per-partition
        # contents until we've gone through the full list of Relationships.
        from_subject_batch = collections.defaultdict(list)
        from_object_batch = collections.defaultdict(list)

        for rel in list_to_insert:
            from_subject_batch[rel.subject_id].append((rel.predicate,
                                                       rel.object_id))
            from_object_batch[rel.object_id].append((rel.predicate,
                                                     rel.subject_id))
        # Our dictionaries are populated and ready for batch insertion
        for object_id, insert_info in six.iteritems(from_object_batch):
            # Only having one entry is a common use case. Skip the overhead!
            if len(insert_info) == 1:
                schema.cross_populate_object_and_subject(subject_id=insert_info[0][1],
                                                         object_id=object_id,
                                                         predicate=insert_info[0][0])
            else:
                with BatchQuery() as b:
                    for entry in insert_info:
                        (schema.SubjectFromObject
                         .batch(b).create(object_id=object_id,
                                          predicate=entry[0],
                                          subject_id=entry[1]))
        for subject_id, insert_info in six.iteritems(from_subject_batch):
            # We already handled this use case with the cross_populate above
            if len(insert_info) == 1:
                pass
            else:
                with BatchQuery() as b:
                    for entry in insert_info:
                        (schema.ObjectFromSubject
                         .batch(b).create(subject_id=subject_id,
                                          predicate=entry[0],
                                          object_id=entry[1]))

    # TODO: Ongoing question of whether these should return generators.

    def _get_given_subject_id(self, subject_id, predicate=None):
        """
        Given record id, return all Relationships with that id as subject.

        Returns None if none found. Wrapped by get(). Optionally filters on
        predicate as well.

        :param subject_id: The subject_id of Relationships to return
        :param predicate: Optionally, the Relationship predicate to filter on.

        :returns: A list of Relationships fitting the criteria or None.
        """
        LOGGER.debug('Getting relationships related to subject_id={} and '
                     'predicate={}.'.format(subject_id, predicate))
        query = (schema.ObjectFromSubject.objects
                 .filter(subject_id=subject_id))
        if predicate:
            query = query.filter(predicate=predicate)
        return self._build_relationships(query.all())

    def _get_given_object_id(self, object_id, predicate=None):
        """
        Given record id, return all Relationships with that id as object.

        Returns None if none found. Wrapped by get(). Optionally filters on
        predicate as well.

        :param object_id: The object_id of Relationships to return
        :param predicate: Optionally, the Relationship predicate to filter on.

        :returns: A list of Relationships fitting the criteria or None.
        """
        LOGGER.debug('Getting relationships related to object_id={} and '
                     'predicate={}.'.format(object_id, predicate))
        query = schema.SubjectFromObject.objects.filter(object_id=object_id)
        if predicate:
            # TODO: If third query table (for predicates) implemented, change
            query = query.filter(predicate=predicate)
        return self._build_relationships(query.allow_filtering().all())

    def _get_given_predicate(self, predicate):
        """
        Given predicate, return all Relationships with that predicate.

        :param predicate: The predicate describing Relationships to return

        :returns: A list of Relationships fitting the criteria
        """
        LOGGER.debug('Getting relationships related to predicate={}.'
                     .format(predicate))
        # TODO: If third query table (for predicates) implemented, change
        query = schema.ObjectFromSubject.objects.filter(predicate=predicate)
        return self._build_relationships(query.allow_filtering().all())

    def _build_relationships(self, query):
        """
        Given query results, built a list of Relationships.

        :param query: The query results to build from.
        """
        LOGGER.debug('Building relationships from query={}'.format(query))
        relationships = []
        for relationship in query:
            rel_obj = model.Relationship(subject_id=relationship.subject_id,
                                         object_id=relationship.object_id,
                                         predicate=relationship.predicate)
            relationships.append(rel_obj)
        return relationships


class RunDAO(dao.RunDAO):
    """DAO responsible for handling Runs, (Record subtype), in Cassandra."""

    def insert(self, run, force_overwrite=False):
        """
        Given a Run, import it into the current Cassandra database.

        :param run: A Run to import
        :param force_overwrite: Whether to forcibly overwrite a preexisting
                                run that shares this run's id.
        """
        LOGGER.debug('Inserting {} into Cassandra with force_overwrite={}'
                     .format(run, force_overwrite))
        create = (schema.Run.create if force_overwrite
                  else schema.Run.if_not_exists().create)
        create(record_id=run.record_id,
               application=run.application,
               user=run.user,
               version=run.version)
        self.record_DAO.insert(record=run, force_overwrite=force_overwrite)

    def _insert_sans_rec(self, run, force_overwrite=False):
        """
        Given a Run, import it into the Run table only.

        Skips the call to record_DAO's insert--this is intended to be called
        from within insert_many()s, which implement special logic that Run
        metadata doesn't benefit from.

        :param run: A Run to import
        :param force_overwrite: Whether to forcibly overwrite a preexisting
                                run that shares this run's id.
        """
        LOGGER.debug('Inserting {} into Cassandra with force_overwrite={}. '
                     'Run table only.'
                     .format(run, force_overwrite))
        create = (schema.Run.create if force_overwrite
                  else schema.Run.if_not_exists().create)
        create(record_id=run.record_id,
               application=run.application,
               user=run.user,
               version=run.version)

    def insert_many(self, list_to_insert, force_overwrite=False):
        """
        Given a list of Runs, insert each into Cassandra.

        Uses Record's special insert_many() for efficiency, then re-inserts
        the metadata on its own (as the metadata doesn't benefit from batching
        and is comparitively lightweight).

        :param list_to_insert: A list of Records to insert

        :param force_overwrite: Whether to forcibly overwrite a preexisting run
                                that shares this run's id.
        """
        LOGGER.debug('Inserting {} runs into Cassandra with '
                     'force_overwrite={}.'
                     .format(len(list_to_insert), force_overwrite))
        self.record_DAO.insert_many(list_to_insert=list_to_insert,
                                    force_overwrite=force_overwrite,
                                    _type_managed=True)
        for item in list_to_insert:
            self._insert_sans_rec(item, force_overwrite)

    def get(self, run_id):
        """
        Given a run's id, return match (if any) from Cassandra database.

        :param run_id: The id of some run

        :returns: A run matching that identifier or None
        """
        LOGGER.debug('Getting run with id: {}'.format(run_id))
        record = schema.Record.filter(record_id=run_id).get()
        run = schema.Run.filter(record_id=run_id).get()
        return model.Run(record_id=run_id,
                         raw=record.raw,
                         application=run.application,
                         user=run.user,
                         user_defined=record.user_defined,
                         version=run.version)

    # Who should this belong to?
    def _convert_record_to_run(self, record):
        """
        Build a Run using a Record and run metadata.

        A variant of get() for internal use which allows us to recycle some of
        Record's functionality. Given a Record, pulls in its information from
        Run and folds it into a new Run object. Allows us to skip an extra read
        of the record table.

        :param record: A Record object to build the Run from.

        :returns: A Run representing the Record plus metadata.
        """
        LOGGER.debug('Converting {} to run.'.format(record))
        run_portion = (schema.Run.filter(record_id=record.record_id).get())
        return model.Run(record_id=record.record_id,
                         raw=record.raw,
                         application=run_portion.application,
                         user=run_portion.user,
                         user_defined=record.user_defined,
                         version=run_portion.version)


class DAOFactory(dao.DAOFactory):
    """
    Build Cassandra-backed DAOs for interacting with Mnoda-based objects.

    Includes Records, Relationships, etc.
    """

    supports_parallel_ingestion = True

    def __init__(self, keyspace, node_ip_list=None):
        """
        Initialize a Factory with a path to its backend.

        :param keyspace: The keyspace to connect to.
        :param node_ip_list: A list of ips belonging to nodes on the target
                            Cassandra instance. If None, connects to localhost.
        """
        self.keyspace = keyspace
        self.node_ip_list = node_ip_list
        schema.form_connection(keyspace, node_ip_list=None)

    def createRecordDAO(self):
        """
        Create a DAO for interacting with records.

        :returns: a RecordDAO
        """
        return RecordDAO()

    def createRelationshipDAO(self):
        """
        Create a DAO for interacting with relationships.

        :returns: a RelationshipDAO
        """
        return RelationshipDAO()

    def createRunDAO(self):
        """
        Create a DAO for interacting with runs.

        :returns: a RunDAO
        """
        return RunDAO(record_DAO=self.createRecordDAO())

    def __repr__(self):
        """Return a string representation of a Cassandra DAOFactory."""
        return ('Cassandra DAOFactory <keyspace={}, node_ip_list={}>'
                .format(self.keyspace, self.node_ip_list))
