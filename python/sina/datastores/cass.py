"""Contains Cassandra-specific implementations of our DAOs."""
import numbers
import logging
# Used for temporary implementation of LIKE-ish functionality
import fnmatch
import six
from collections import defaultdict
import json

from cassandra.cqlengine.query import DoesNotExist, BatchQuery

import sina.dao as dao
import sina.model as model
import sina.datastores.cass_schema as schema
import sina.utils as utils

LOGGER = logging.getLogger(__name__)

table_lookup = {
                "scalar": {"record_table": schema.RecordFromScalarData,
                           "data_table": schema.ScalarDataFromRecord},
                "string": {"record_table": schema.RecordFromStringData,
                           "data_table": schema.StringDataFromRecord},
                "stringlist": {"record_table": schema.RecordFromStringListData,
                               "data_table": schema.StringListDataFromRecord},
                "scalarlist": {"record_table": schema.RecordFromScalarListData,
                               "data_table": schema.ScalarListDataFromRecord}
}


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
        is_valid, warnings = record.is_valid()
        if not is_valid:
            raise ValueError(warnings)
        create = (schema.Record.create if force_overwrite
                  else schema.Record.if_not_exists().create)
        create(id=record.id,
               type=record.type,
               raw=json.dumps(record.raw))
        if record.data:
            self._insert_data(id=record.id,
                              data=record.data,
                              force_overwrite=force_overwrite)
        if record.files:
            self._insert_files(id=record.id,
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
                                that shares this run's id.
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
        from_scalar_batch = defaultdict(list)
        from_string_batch = defaultdict(list)
        from_scalar_list_batch = defaultdict(list)
        from_string_list_batch = defaultdict(list)

        for record in list_to_insert:
            # Insert the Record itself
            is_valid, warnings = record.is_valid()
            if not is_valid:
                raise ValueError(warnings)
            create = (schema.Record.create if force_overwrite
                      else schema.Record.if_not_exists().create)
            create(id=record.id,
                   type=record.type,
                   raw=json.dumps(record.raw))
            if record.data:
                string_from_rec_batch = []
                scalar_from_rec_batch = []
                string_list_from_rec_batch = []
                scalar_list_from_rec_batch = []
                tags, units, value, datum_name, id = [None]*5

                def _cross_populate_batch(batch_dict, batch_list):
                    """Insert data into a batch dict and list."""
                    batch_dict[datum_name].append((value, id, units, tags))
                    batch_list.append((datum_name, value, units, tags))

                for datum_name, datum in record.data.items():
                    tags = [str(x) for x in datum['tags']] if 'tags' in datum else None
                    units = datum.get('units')
                    value = datum['value']
                    id = record.id
                    if isinstance(value, numbers.Real):
                        _cross_populate_batch(from_scalar_batch, scalar_from_rec_batch)

                    elif isinstance(value, list):
                        # Empty lists are stored as though they contain scalars
                        # This is safe as long as future functionality involving
                        # modifying already-ingested data checks type on re-ingestion
                        if not value or isinstance(value[0], numbers.Real):
                            _cross_populate_batch(from_scalar_list_batch,
                                                  scalar_list_from_rec_batch)
                        else:
                            _cross_populate_batch(from_string_list_batch,
                                                  string_list_from_rec_batch)
                    else:
                        # It's a string (or it's something else and Cassandra will yell)
                        _cross_populate_batch(from_string_batch, string_from_rec_batch)

                # We've finished this record's data--do the batch inserts
                for table, data_list in ((schema.ScalarDataFromRecord, scalar_from_rec_batch),
                                         (schema.StringDataFromRecord, string_from_rec_batch),
                                         (schema.ScalarListDataFromRecord,
                                          scalar_list_from_rec_batch),
                                         (schema.StringListDataFromRecord,
                                          string_list_from_rec_batch)):
                    with BatchQuery() as b:
                        create = (table.batch(b).create if force_overwrite
                                  else table.batch(b).if_not_exists().create)
                        for entry in data_list:
                            create(id=record.id,
                                   name=entry[0],
                                   value=entry[1],
                                   units=entry[2],
                                   tags=entry[3])
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
                        create(id=record.id,
                               uri=doc[0],
                               mimetype=doc[1],
                               tags=doc[2])
            if not _type_managed:
                if record.type == "run":
                    self.RunDAO._insert_sans_rec(record, force_overwrite)

        # We've gone through every record we were given. The from_scalar_batch
        # and from_string_batch dictionaries are ready for batch inserting.
        for table, partition_data in ((schema.RecordFromScalarData, from_scalar_batch),
                                      (schema.RecordFromStringData, from_string_batch)):
            for partition, data_list in six.iteritems(partition_data):
                with BatchQuery() as b:
                    create = (table.batch(b).create if force_overwrite
                              else table.batch(b).if_not_exists().create)
                    for entry in data_list:
                        create(name=partition,
                               value=entry[0],
                               id=entry[1],
                               units=entry[2],
                               tags=entry[3])
        # The RecordFromList-type tables differ form their partners slightly more
        # to support their associated queries
        for table, partition_data in ((schema.RecordFromScalarListData, from_scalar_list_batch),
                                      (schema.RecordFromStringListData, from_string_list_batch)):
            for partition, data_list in six.iteritems(partition_data):
                with BatchQuery() as b:
                    # We no longer worry about overriding, trusting the partner
                    # table to catch it if necessary.
                    for entry in data_list:
                        for value in entry[0]:
                            table.batch(b).create(name=partition,
                                                  value=value,
                                                  id=entry[1])

    def _insert_data(self, data, id, force_overwrite=False):
        """
        Insert data into two of the four query tables depending on value.

        Data entries that are numbers (12.0) go in the ScalarData tables. Any that
        aren't ("Tuesday","12.0") go in the StringData tables.

        :param data: The dictionary of data to insert.
        :param id: The Record ID to associate the data to.
        :param force_overwrite: Whether to forcibly overwrite preexisting data.
                                Currently only used by Cassandra DAOs.
        """
        LOGGER.debug('Inserting {} data entries to Record ID {} and force_overwrite={}.'
                     .format(len(data), id, force_overwrite))
        for datum_name, datum in data.items():
            schema.cross_populate_data_tables(id=id,
                                              name=datum_name,
                                              value=datum['value'],
                                              units=datum.get('units'),
                                              tags=datum.get('tags'),
                                              force_overwrite=force_overwrite)

    def _insert_files(self, id, files, force_overwrite=False):
        """
        Insert files into the DocumentFromRecord table.

        :param id: The Record ID to associate the files to.
        :param files: The list of files to insert.
        :param force_overwrite: Whether to forcibly overwrite preexisting files.
                                Currently only used by Cassandra DAOs.
        """
        LOGGER.debug('Inserting {} files to record id={} and force_overwrite={}.'
                     .format(len(files), id, force_overwrite))
        create = (schema.DocumentFromRecord.create if force_overwrite
                  else schema.DocumentFromRecord.if_not_exists().create)
        for entry in files:
            create(id=id,
                   uri=entry['uri'],
                   mimetype=entry.get('mimetype'),
                   tags=entry.get('tags'))

    def delete(self, id):
        """
        Delete a single Record from the Cassandra backend.

        Removes everything: its data, any relationships it's in, files. Relies on
        Cassandra batching, one batch per Record.

        :param id: The id of the Record to delete
        """
        with BatchQuery() as batch:
            self._setup_batch_delete(batch, id)

    def delete_many(self, ids_to_delete):
        """
        Delete a list of Records from the Cassandra backend.

        Removes everything: their data, relationships, files. Relies on
        Cassandra's batching, one batch encompassing all Records. If you want
        to do one batch per Record, use delete() in a loop.

        :param ids_to_delete: A list of ids of Records to delete
        """
        with BatchQuery() as batch:
            for id in ids_to_delete:
                self._setup_batch_delete(batch, id)

    def _setup_batch_delete(self, batch, record_id):
        """
        Given a batchquery, add the deletion commands for a given record.

        Cassandra has no notion of foreign keys, so we manually define what
        it means to delete a record, including removing all the data entries,
        all the files, etc. We add those deletions to a batchquery for later
        execution.

        :param batch: the batch to add the deletions to
        :param record_id: the id of the record we're deleting
        """
        LOGGER.debug("Generating batch deletion commands for {}".format(record_id))
        record = self.get(record_id)
        # Delete from the record table itself
        schema.Record.objects(id=record_id).batch(batch).delete()
        # Delete every file
        schema.DocumentFromRecord.objects(id=record_id).batch(batch).delete()
        # Delete every piece of data
        # Done a bit differently because record_id isn't always the partition key
        for name, datum in record['data'].iteritems():
            schema.cross_batch_delete_data_tables(id=record_id,
                                                  name=name,
                                                  value=datum['value'],
                                                  batch=batch)

        # Because Relationships are created separately from Records, we have to
        # manually discover all relationships. Because they are mirrored, we
        # can do this efficiently and without allow_filtering.
        obj_when_rec_is_subj = (schema.ObjectFromSubject.objects(subject_id=record_id)
                                                        .values_list('object_id',
                                                                     'predicate'))
        for obj, pred in obj_when_rec_is_subj:
            (schema.SubjectFromObject.objects(object_id=obj,
                                              predicate=pred,
                                              subject_id=record_id)
             .batch(batch).delete())
        schema.ObjectFromSubject.objects(subject_id=record_id).batch(batch).delete()

        # Now again with the other table.
        subj_when_rec_is_obj = (schema.SubjectFromObject.objects(object_id=record_id)
                                                        .values_list('subject_id',
                                                                     'predicate'))
        for subj, pred in subj_when_rec_is_obj:
            (schema.ObjectFromSubject.objects(subject_id=subj,
                                              predicate=pred,
                                              object_id=record_id)
             .batch(batch).delete())
        schema.SubjectFromObject.objects(object_id=record_id).batch(batch).delete()

    def data_query(self, **kwargs):
        """
        Return the ids of all Records whose data fulfill some criteria.

        Criteria are expressed as keyword arguments. Each keyword
        is the name of an entry in a Record's data field, and it's set
        equal to either a single value or a DataRange (see utils.DataRanges
        for more info) that expresses the desired value/range of values.
        All criteria must be satisfied for an ID to be returned:

            # Return ids of all Records with a volume of 12, a quadrant of
            # "NW", AND a max_height >=30 and <40.
            data_query(volume=12, quadrant="NW", max_height=DataRange(30,40))

        :param kwargs: Pairs of the names of data and the criteria that data
                         must fulfill.
        :returns: A generator of Records that fulfill all criteria.

        :raises ValueError: if not supplied at least one criterion.
        """
        LOGGER.debug('Finding all records fulfilling criteria: {}'
                     .format(kwargs.items()))
        # No kwargs is bad usage. Bad kwargs are caught in sort_criteria().
        if not kwargs.items():
            raise ValueError("You must supply at least one criterion.")
        scalar_criteria, string_criteria = utils.sort_and_standardize_criteria(kwargs)

        if scalar_criteria:
            scalar_ids = self._apply_ranges_to_query(scalar_criteria,
                                                     "scalar")
        if string_criteria:
            string_ids = self._apply_ranges_to_query(string_criteria,
                                                     "string")

        # If we have more than one set of data, we need to perform a union.
        # Cassandra doesn't support join-like operations, though, so we
        # handle it. Note that we'll be storing a full list of ids in memory,
        # but because Cassandra already required that to perform the query,
        # we're not in danger of running out of memory if we've reached here.
        if scalar_criteria and string_criteria:
            string_ids = set(string_ids)
            for id in scalar_ids:
                if id in string_ids:
                    yield id
        # Otherwise, just find which one has something to return
        elif scalar_criteria:
            for id in scalar_ids:
                yield id
        else:
            for id in string_ids:
                yield id

    def _apply_ranges_to_query(self, data, table):
        """
        Return the ids of all Records whose data fulfill table-specific criteria.

        Done per table, unlike data_query. This is only meant to be used in
        conjunction with data_query() and related. Criteria can be DataRanges
        or single values (12, "dog", etc)

        Because each piece of data is its own row and we need to compare between
        rows, we can't use a simple AND. In SQL, we get around this with
        GROUP BY, in order to avoid reading the entire table multiple times.
        Cassandra is organized differently; thanks to its partitioning, it is
        *in theory* efficient to start by narrowing it down to a set of partitions
        (by finding which Records fit the first criteria) and then applying each
        successive criteria as a filter on that set, ultimately doing len(data)
        queries (but handling less data overall). If this acts slow, it's
        probably network/query overhead.

        :param data: A list of (name, criteria) pairs to apply to the query object
        :param table: The name of the table, to look up in table_lookup (module-level var)

        :returns: a generator of ids fitting the criteria
        """
        rec_table = table_lookup[table]["record_table"]
        query = rec_table.objects
        # Cassandra requires a list for the in-predicate
        filtered_ids = list(self._configure_query_for_criteria(query,
                                                               name=data[0][0],
                                                               criteria=data[0][1])
                            .values_list('id', flat=True))

        # Only do the next part if there's more criteria and at least one id
        for counter, (name, criteria) in enumerate(data[1:]):
            if filtered_ids:
                query = (self._configure_query_for_criteria(rec_table.objects, name, criteria)
                         .filter(id__in=filtered_ids))
                if counter < (len(data[1:]) - 1):
                    # Cassandra requires a list for the id__in attribute
                    filtered_ids = list(query.values_list('id', flat=True).all())
                else:
                    # We are on the last iteration, no need for a list, use a generator
                    filtered_ids = query.values_list('id', flat=True)
            else:
                break

        for id in filtered_ids:
            yield id

    def get(self, id):
        """
        Given a id, return match (if any) from Cassandra database.

        :param id: The id of the record to return

        :returns: A record matching that id or None
        """
        LOGGER.debug('Getting record with id={}'.format(id))
        query = schema.Record.objects.filter(id=id).get()
        return model.generate_record_from_json(
            json_input=json.loads(query.raw))

    def get_all_of_type(self, type, ids_only=False):
        """
        Given a type of record, return all Records of that type.

        :param type: The type of record to return, ex: run
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of Records of that type or (if ids_only) a
                  generator of their ids
        """
        LOGGER.debug('Getting all records of type {}.'.format(type))
        # Allow_filtering() is, as a rule, inadvisable; if speed becomes a
        # concern, an id - type query table should be easy to set up.
        query = (schema.Record.objects.filter(type=type)
                                      .allow_filtering()
                                      .values_list('id', flat=True))
        if ids_only:
            for id in query:
                yield str(id)
        else:
            for record in self.get_many(query):
                yield record

    def get_list_has_all(self, datum_name, list_of_contents, ids_only=False):
        """
        Given a list datum's name and values, return Records where the datum contains all values.

        As an example, given "pizza_toppings" and ["pineapple", "cheese"],
        this method would return Records where "pizza_toppings" is ["pineapple", "cheese"]
        or ["pineapple", "cheese", "pepperoni"], but not just ["cheese"].

        Note that if datum_name isn't found, no record_ids will be found, so be sure
        datum_name is the name of a list-type datum (timeseries, etc).

        :param datum_name: The name of the datum
        :param list_of_contents: All the values datum_name must contain. Can be single
                                 values (like "egg" or 12) or DataRanges. All values must
                                 describe the same type of data, either scalar or string.
        :param ids_only: Whether to only return ids rather than full Records.
        :returns: A generator of ids of matching Records or the Records themselves (see ids_only)
        :raises TypeError: if given a list that isn't all strings xor scalars.
        :raises ValueError: if list_of_contents is empty.
        """
        LOGGER.info('Finding Records where datum {} contains all of: {}'.format(datum_name,
                                                                                list_of_contents))
        # We don't know what someone means when they pass us no contents for datum_name
        if not list_of_contents:
            raise ValueError("Must supply at least one entry in list_of_contents for {}"
                             .format(datum_name))
        criteria_tuples = [(datum_name, x) for x in list_of_contents]
        # If this becomes an internal method, might want caller to do these checks
        if all((isinstance(x, numbers.Real) or
                (isinstance(x, utils.DataRange) and x.is_numeric_range()))
               for x in list_of_contents):
            ids = self._apply_ranges_to_query(table="scalarlist", data=criteria_tuples)
        elif all((isinstance(x, six.string_types) or
                  (isinstance(x, utils.DataRange) and x.is_lexographic_range()))
                 for x in list_of_contents):
            ids = self._apply_ranges_to_query(table="stringlist", data=criteria_tuples)
        else:
            raise TypeError("list_of_contents must be only strings or only scalars")

        if ids_only:
            return ids
        else:
            return self.get_many(list(ids))

    def get_given_document_uri(self, uri, accepted_ids_list=None, ids_only=False):
        """
        Return all records associated with documents whose uris match some arg.

        Temporary implementation. THIS IS A VERY SLOW, BRUTE-FORCE STRATEGY!
        You use it at your own risk! Do not expect it to be performant or
        particularly stable. Due to some cassandra limitations, this returns
        potentially duplicate items. One work around for this is to wrap this
        call in a set() like this:
        get_many(set(get_given_document_uri(<args>, ids_only=True))).

        Supports the use of % as a wildcard character.

        :param uri: The uri to use as a search term, such as "foo.png"
        :param accepted_ids_list: A list of ids to restrict the search to.
                                  If not provided, all ids will be used.
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of found records or (if ids_only) a
                  generator of their ids.
        """
        LOGGER.debug('Getting all records related to uri={}.'.format(uri))
        if accepted_ids_list:
            LOGGER.debug('Restricting to {} ids.'.format(len(accepted_ids_list)))
        LOGGER.warning('Temporary implementation of getting Records based on '
                       'Document URI. This is a very slow, brute-force '
                       'strategy.')
        if accepted_ids_list is not None:
            base_query = schema.DocumentFromRecord.objects.filter(id__in=accepted_ids_list)
        else:
            # If we haven't had an accepted_ids_list passed, any filtering we do
            # will NOT include the partition key, so we need to allow filtering.
            base_query = schema.DocumentFromRecord.objects.allow_filtering()
        # If there's a wildcard
        if '%' in uri:
            # Special case: get all ids with associated docs.
            if len(uri) == 1:
                match_ids = base_query.values_list('id', flat=True)

            # If a wildcard is in any position besides last, we do it in Python
            elif '%' in uri[:-1]:
                # Change searched URI into a fnmatch-friendly version
                search_uri = uri.replace('*', '[*]').replace('%', '*')
                match_ids = (
                    entry.id
                    for entry in base_query
                    if fnmatch.fnmatch(entry.uri, search_uri)
                )
            # As long as the wildcard's in last place, we can do it in CQL
            else:
                # Cassandra orders lexographically by UTF-8
                # Thus, we can search from ex: 'foo' through 'fop' to
                # simulate a 'LIKE foo%' query.
                alphabetical_end = uri[:-2]+chr(ord(uri[-2]) + 1)
                match_ids = (base_query.filter(uri__gte=uri[:-1])
                                       .filter(uri__lt=alphabetical_end)
                                       .values_list('id', flat=True))
        # If there's no wildcard, we're looking for exact matches.
        else:
            match_ids = base_query.filter(uri=uri).values_list('id', flat=True)

        if ids_only:
            for id in match_ids:
                yield id
        else:
            for record in self.get_many(match_ids):
                yield record

    def _configure_query_for_criteria(self, query, name, criteria):
        """
        Use criteria to build a query.

        Note that this returns a query object, not a completed query. It's
        used by the data query methods to build the queries they execute.

        :param query: The query object to consider
        :param name: The name of the data being queries
        :param criteria: The criteria we're filtering the query on.

        :returns: The query object with criteria-appropriate filters
                  applied.
        """
        LOGGER.debug('Configuring <query={}> with <criteria={}>.'
                     .format(query, criteria))
        query = query.filter(name=name)
        if not isinstance(criteria, utils.DataRange):
            query = query.filter(value=criteria)
        elif criteria.is_single_value():
            query = query.filter(value=criteria.min)
        else:
            if criteria.min is not None:
                if criteria.min_inclusive:
                    query = query.filter(value__gte=criteria.min)
                else:
                    query = query.filter(value__gt=criteria.min)
            if criteria.max is not None:
                if criteria.max_inclusive:
                    query = query.filter(value__lte=criteria.max)
                else:
                    query = query.filter(value__lt=criteria.max)
        return query

    def get_data_for_records(self, id_list, data_list, omit_tags=False):
        """
        Retrieve a subset of data for Records in id_list.

        For example, it might get "debugger_version" and "volume" for the
        Records with ids "foo_1" and "foo_3". It's returned in a dictionary of
        dictionaries; the outer key is the record_id, the inner key is the
        name of the data piece (ex: "volume"). So::

            {"foo_1": {"volume": {"value": 12, "units": cm^3},
                       "debugger_version": {"value": "alpha"}}
             "foo_3": {"debugger_version": {"value": "alpha"}}

        As seen in foo_3 above, if a piece of data is missing, it won't be
        included; think of this as a subset of a Record's own data. Similarly,
        if a Record ends up containing none of the requested data, it will be
        omitted.

        :param id_list: A list of the record ids to find data for
        :param data_list: A list of the names of data fields to find
        :param omit_tags: Whether to avoid returning tags. A Cassandra
                          limitation results in up to id_list*data_list+1
                          queries to include the tags, rather than the single
                          query we'd do otherwise. If you don't need the tags/
                          are on a machine with a slow network connection
                          to the cluster, consider setting this to True.

        :returns: a dictionary of dictionaries containing the requested data,
                 keyed by record_id and then data field name.
        """
        LOGGER.debug('Getting data in {} for record ids in {}'
                     .format(data_list, id_list))
        data = defaultdict(lambda: defaultdict(dict))
        query_tables = [schema.ScalarDataFromRecord,
                        schema.StringDataFromRecord]
        for query_table in query_tables:
            query = (query_table.objects
                     .filter(query_table.id.in_(id_list))
                     .filter(query_table.name.in_(data_list))
                     .values_list('id', 'name', 'value', 'units'))
            for result in query:
                id, name, value, units = result
                datapoint = {"value": value}
                if units:
                    datapoint["units"] = units
                data[id][name] = datapoint
            # Cassandra has a limitation wherein any "IN" query stops working
            # if one of the columns requested contains collections. 'tags' is a
            # collection column. Unfortunately, there's a further limitation
            # that a BatchQuery can't select (only create, update, or delete),
            # so the best we can do (until they fix one of the above) is:
            if not omit_tags:
                for id in data:
                    for name in data[id]:
                        if "tags" not in data[id][name]:
                            tags = (query_table.objects
                                    .filter(query_table.id == id)
                                    .filter(query_table.name == name)
                                    .values_list('tags', flat=True)).all()
                            if tags and tags[0] is not None:
                                data[id][name]["tags"] = tags[0]
        return data

    def get_scalars(self, id, scalar_names):
        """
        LEGACY: retrieve scalars for a given record id.

        This is a legacy method. Consider accessing data from Records directly,
        ex scalar_info = my_rec["data"][scalar_name]

        Scalars are returned as a dictionary with the same format as a Record's
        data attribute (it's a subset of it)

        :param id: The record id to find scalars for
        :param scalar_names: A list of the names of scalars to return

        :return: A dict of scalars matching the Mnoda data specification
        """
        LOGGER.debug('Getting scalars={} for record id={}'
                     .format(scalar_names, id))
        scalars = {}
        # Cassandra has special restrictions on list types that prevents us
        # from filtering on IN when they're present in a table. Hence this
        # workaround.
        for name in sorted(scalar_names):
            try:
                entry = (schema.ScalarDataFromRecord.objects
                         .filter(id=id)
                         .filter(name=name)
                         .values_list('name', 'value', 'units', 'tags')).get()
                scalars[entry[0]] = {'value': entry[1],
                                     'units': entry[2],
                                     'tags': entry[3]}
            except DoesNotExist:
                # If scalar doesn't exist, continue
                pass
        return scalars

    def get_files(self, id):
        """
        Retrieve files for a given record id.

        Files are returned in the alphabetical order of their URIs

        :param id: The record id to find files for
        :return: A list of file JSON objects matching the Mnoda specification
        """
        LOGGER.debug('Getting files for record id={}'.format(id))
        files = (schema.DocumentFromRecord.objects
                 .filter(id=id)
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

        :param subject_id: The id of the subject.
        :param object_id: The id of the object.
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
        from_subject_batch = defaultdict(list)
        from_object_batch = defaultdict(list)

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
        create(id=run.id,
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
        create(id=run.id,
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

    def delete(self, id):
        """
        Delete a single Run from the Cassandra backend.

        Removes everything: its data, any relationships it's in, files. Relies on
        Cassandra batching, one batch per Run.

        :param id: The id of the Run to delete
        """
        with BatchQuery() as batch:
            schema.Run.objects(id=id).batch(batch).delete()
            self.record_DAO._setup_batch_delete(batch, id)

    def delete_many(self, ids_to_delete):
        """
        Delete a list of Runs from the Cassandra backend.

        Removes everything: their data, relationships, files. Relies on
        Cassandra's batching, one batch encompassing all Runs. If you want
        to do one batch per Run, use delete() in a loop.

        :param ids_to_delete: A list of ids of Runs to delete
        """
        with BatchQuery() as batch:
            for id in ids_to_delete:
                schema.Run.objects(id=id).batch(batch).delete()
                self.record_DAO._setup_batch_delete(batch, id)

    def get(self, id):
        """
        Given a run's id, return match (if any) from Cassandra database.

        :param id: The id of some run

        :returns: A run matching that identifier or None
        """
        LOGGER.debug('Getting run with id: {}'.format(id))
        record = schema.Record.filter(id=id).get()
        return model.generate_run_from_json(json_input=json.loads(record.raw))
    # Who should this belong to?

    def _convert_record_to_run(self, record):
        """
        Build a Run using a Record and run metadata.

        A variant of get() for internal use which allows us to recycle some of
        Record's functionality. Given a Record, pulls in its information from
        Run and folds it into a new Run object. Allows us to skip an extra read
        of the record table.

        :param record: A Record object to build the Run from.

        :returns: A Run representing the Record plus metadata. None if given
            a record that isn't a run as input.
        """
        LOGGER.debug('Converting {} to run.'.format(record))
        if record.type == 'run':
            return model.generate_run_from_json(record.raw)
        else:
            msg = ('Record must be of subtype Run to convert to Run. Given '
                   '{}.'.format(record.id))
            LOGGER.warn(msg)
            raise ValueError(msg)


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
