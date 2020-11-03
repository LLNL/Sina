# pylint: disable=too-many-lines
"""Contains Cassandra-specific implementations of our DAOs."""
import numbers
import logging
# Used for temporary implementation of LIKE-ish functionality
import fnmatch
from collections import defaultdict
import json

import six

# Disable pylint check due to its issue with virtual environments
from cassandra.cqlengine.query import DoesNotExist, BatchQuery  # pylint: disable=import-error
# This is used to patch the default limit issue that will be fixed in cassandra-driver 4.0.0
# The behavior of queries is changed in that the default limit (10,000) is disabled
# This affects the object itself; if you inherit this module, you will see the effect.
from cassandra.cqlengine.query import AbstractQuerySet  # pylint: disable=import-error

import sina.dao as dao
import sina.model as model
import sina.datastores.cass_schema as schema
import sina.utils as utils

# Disable pylint checks due to ubiquitous use of id
# pylint: disable=invalid-name,redefined-builtin

LOGGER = logging.getLogger(__name__)

# Used to support data types with both "XFromRecord" and "RecordFromX" tables
TABLE_LOOKUP = {
    "scalar": {"record_table": schema.RecordFromScalarData,
               "data_table": schema.ScalarDataFromRecord},
    "string": {"record_table": schema.RecordFromStringData,
               "data_table": schema.StringDataFromRecord}
}


def _disable_cqlengine_implicit_query_limit():
    """
    Hack around QuerySets having an implicit limit of 10,000 results.

    Note that this behavior will affect *all* QuerySets once this is loaded.
    This is just an expansion on AbstractQuerySet's original init. See DAOFactory
    for use.
    """
    orig_init = AbstractQuerySet.__init__

    def queryset_init_sans_default_limit(abstractqueryset, aqs_model):
        """
        Initialize an abstractqueryset as usual, except with the limit disabled.

        :param <all>: inherited from the "real" init with meanings unchanged.
        """
        orig_init(abstractqueryset, aqs_model)
        # Currently the only way to tweak this.
        # pylint: disable=protected-access
        abstractqueryset._limit = 0

    # Replace the old init with the patched one.
    AbstractQuerySet.__init__ = queryset_init_sans_default_limit


_disable_cqlengine_implicit_query_limit()


class RecordDAO(dao.RecordDAO):
    """The DAO specifically responsible for handling Records in Cassandra."""

    # pylint: disable=arguments-differ
    # Args differ because SQL doesn't support force_overwrite yet, SIBO-307
    def insert(self, records, force_overwrite=False):
        """
        Given a(n iterable of) Record(s), insert it into the current Cassandra database.

        :param records: A Record or iterable of Records to insert
        :param force_overwrite: Whether to forcibly overwrite a preexisting
                                record that shares this record's id.
        :raises LWTException: If force_overwrite is False and an entry with the
                              id exists.
        """
        LOGGER.debug('Inserting %s into Cassandra with force_overwrite=%s.',
                     records, force_overwrite)

        if isinstance(records, model.Record):
            self._insert_one(records)
        else:
            self._insert_many(records, _type_managed=False)

    def _insert_one(self, record, force_overwrite=False):
        """
        Given a single Record, insert it into the current Cassandra database.

        :param records: A Record to insert
        :param force_overwrite: Whether to forcibly overwrite a preexisting
                                record that shares this record's id.
        :raises LWTException: If force_overwrite is False and an entry with the
                              id exists.
        """
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
        if record.curve_sets:
            self._insert_curve_sets(id=record.id,
                                    curve_sets=record.curve_sets,
                                    data=record.data,
                                    force_overwrite=force_overwrite)
        if record.files:
            self._insert_files(id=record.id,
                               files=record.files,
                               force_overwrite=force_overwrite)

    # Disabled until rework, possibly splitting into the first and second batch types
    # pylint: disable=too-many-locals, too-many-branches, too-many-statements
    @staticmethod
    def _insert_many(list_to_insert, _type_managed, force_overwrite=False):
        """
        Given an iterable of Records, insert each into Cassandra.

        This method relies heavily on batching--if you're only inserting a few
        records, you may not see performance gains, and may even see some
        slowdowns due to batch logic overhead.

        :param list_to_insert: A list of Records to insert
        :param _type_managed: Whether all records inserted are the same type
                              AND _insert_many is called from a method that has
                              special handling for this type. See Run's
                              insert()
        :param force_overwrite: Whether to forcibly overwrite a preexisting run
                                that shares this run's id.
        """
        LOGGER.debug('Inserting records %s to Cassandra with'
                     'force_overwrite=%s and _type_managed=%s.',
                     list_to_insert, force_overwrite, _type_managed)
        # Because batch is done by partition key, we'll need to store info for
        # tables whose full per-partition info isn't supplied by one Record.
        # Thus, these rec_from_x dicts last for the full insert.
        from_scalar_batch = defaultdict(list)
        from_string_batch = defaultdict(list)
        from_scalar_list_batch = defaultdict(list)
        from_string_list_batch = defaultdict(list)

        # Different setup from the others, no units or value.
        from_curve_set_meta_batch = defaultdict(list)

        def _cross_populate_batch(batch_dict, batch_list=None):
            """
            Insert data into a batch dict (rec_from_x) and list (x_from_rec).

            Not all data types make sense for an x_from_rec table (ex: lists),
            so in those cases, simply skip the list population.
            """
            batch_dict[datum_name].append((value, id, units, tags))
            if batch_list is not None:
                batch_list.append((datum_name, value, units, tags))

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

            if record.curve_sets:
                # Curve set names are meta, everything else is per-record.
                for curveset_name, curveset_obj in record.curve_sets.items():
                    from_curve_set_meta_batch[curveset_name].append([record.id,
                                                                     curveset_obj.get("tags")])
                resolved_curves = utils.resolve_curve_sets(record.curve_sets, record.data)
                # Curve data is stored as a scalar list
                scalar_list_from_rec_batch = []
                tags, units, value, datum_name, id = [None]*5
                for entry_name, entry in six.iteritems(resolved_curves):
                    # The values set here are used by _cross_populate_batch
                    datum_name = entry_name
                    tags = [str(x) for x in entry['tags']] if 'tags' in entry else None
                    units = entry.get('units')
                    value = entry['value']
                    id = record.id
                    _cross_populate_batch(from_scalar_list_batch,
                                          scalar_list_from_rec_batch)

            if record.data:
                # Unlike the rec_from_x dictionaries, these have the scope of a
                # single Record, since the record id acts as their partition key.
                string_from_rec_batch = []
                scalar_from_rec_batch = []
                tags, units, value, datum_name, id = [None]*5

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
                            _cross_populate_batch(from_scalar_list_batch)
                        else:
                            _cross_populate_batch(from_string_list_batch)
                    else:
                        # It's a string (or it's something else and Cassandra will yell)
                        _cross_populate_batch(from_string_batch, string_from_rec_batch)

                # We've finished this record's data--do the x_from_rec batch inserts
                for table, data_list in ((schema.ScalarDataFromRecord, scalar_from_rec_batch),
                                         (schema.StringDataFromRecord, string_from_rec_batch)):
                    with BatchQuery() as batch_query:
                        create = (table.batch(batch_query).create if force_overwrite
                                  else table.batch(batch_query).if_not_exists().create)
                        for entry in data_list:
                            create(id=record.id,
                                   name=entry[0],
                                   value=entry[1],
                                   units=entry[2],
                                   tags=entry[3])
            if record.files:
                document_batch = []
                for uri, file_info in six.iteritems(record.files):
                    # Mimetype and tags can be None, use get() for safety
                    document_batch.append((uri,
                                           file_info.get('mimetype'),
                                           file_info.get('tags')))
                table = schema.DocumentFromRecord
                with BatchQuery() as batch_query:
                    create = (table.batch(batch_query).create if force_overwrite
                              else table.batch(batch_query).if_not_exists().create)
                    for doc in document_batch:
                        create(id=record.id,
                               uri=doc[0],
                               mimetype=doc[1],
                               tags=doc[2])

        # We've gone through every record we were given. The rec_from_x batch
        # dictionaries are ready for inserting.
        for table, partition_data in ((schema.RecordFromScalarData, from_scalar_batch),
                                      (schema.RecordFromStringData, from_string_batch)):
            for partition, data_list in six.iteritems(partition_data):
                with BatchQuery() as batch_query:
                    create = (table.batch(batch_query).create if force_overwrite
                              else table.batch(batch_query).if_not_exists().create)
                    for entry in data_list:
                        create(name=partition,
                               value=entry[0],
                               id=entry[1],
                               units=entry[2],
                               tags=entry[3])
        # The RecordFromList-type tables differ form their partners slightly more
        # to support their associated queries. They also differ from one another.
        table = schema.RecordFromScalarListDataMin
        support_table = schema.RecordFromScalarListDataMax
        for partition, data_list in six.iteritems(from_scalar_list_batch):
            with BatchQuery() as batch_query:
                for entry in data_list:
                    # We track only the min and max, that's all we need for queries
                    table.batch(batch_query).create(name=partition,
                                                    min=min(entry[0]),
                                                    id=entry[1])
                    support_table.batch(batch_query).create(name=partition,
                                                            max=max(entry[0]),
                                                            id=entry[1])
        table = schema.RecordFromStringListData
        for partition, data_list in six.iteritems(from_string_list_batch):
            with BatchQuery() as batch_query:
                # We no longer worry about overriding, trusting the partner
                # table to catch it if necessary.
                for entry in data_list:
                    for value in entry[0]:
                        table.batch(batch_query).create(name=partition,
                                                        value=value,
                                                        id=entry[1])
        # The RecordFromCurveSetMeta table is pretty simple.
        table = schema.RecordFromCurveSetMeta
        for partition, data_list in six.iteritems(from_curve_set_meta_batch):
            with BatchQuery() as batch_query:
                for entry in data_list:
                    table.batch(batch_query).create(name=partition,
                                                    id=entry[0],
                                                    tags=entry[1])

    @staticmethod
    def _insert_data(data, id, force_overwrite=False):
        """
        Insert data into two of the Cassandra query tables depending on value.

        Data entries that are numbers (12.0) go in the ScalarData tables. Any that
        aren't ("Tuesday","12.0") go in the StringData tables. Helper method to
        simplify insertion.

        :param data: The dictionary of data to insert.
        :param id: The Record ID to associate the data to.
        :param force_overwrite: Whether to forcibly overwrite preexisting data.
                                Currently only used by Cassandra DAOs.
        """
        LOGGER.debug('Inserting %i data entries to Record ID %s and force_overwrite=%s.',
                     len(data), id, force_overwrite)
        for datum_name, datum in data.items():
            schema.cross_populate_query_tables(id=id,
                                               name=datum_name,
                                               value=datum['value'],
                                               units=datum.get('units'),
                                               tags=datum.get('tags'),
                                               force_overwrite=force_overwrite)

    @staticmethod
    def _insert_curve_sets(curve_sets, id, data, force_overwrite=False):
        """
        Insert curves into two of the Cassandra query tables depending on value.

        Data is loaded into the scalar list data and curve meta tables. Helper
        method to simplify insertion.

        :param curve_sets: The dictionary of curve sets to insert.
        :param data: The data associated with the record
        :param id: The Record ID to associate the curve sets to.
        :param force_overwrite: Whether to forcibly overwrite preexisting curves.
                                Currently only used by Cassandra DAOs.
        """
        LOGGER.debug('Inserting %i curve sets into Record ID %s with force_overwrite=%s.',
                     len(curve_sets), id, force_overwrite)
        create_meta = (schema.RecordFromCurveSetMeta.create if force_overwrite
                       else schema.RecordFromCurveSetMeta.if_not_exists().create)
        resolved_curves = utils.resolve_curve_sets(curve_sets, data)

        for curveset_name, curveset_obj in curve_sets.items():
            create_meta(name=curveset_name, id=id, tags=curveset_obj.get("tags"))
        for entry_name, entry_obj in six.iteritems(resolved_curves):
            print(entry_name, entry_obj)
            schema.cross_populate_query_tables(id=id,
                                               name=entry_name,
                                               value=entry_obj['value'],
                                               units=entry_obj.get('units'),
                                               tags=entry_obj.get('tags'),
                                               force_overwrite=force_overwrite)

    @staticmethod
    def _insert_files(id, files, force_overwrite=False):
        """
        Insert files into the DocumentFromRecord table.

        Helper method to simplify insertion, bound to Cassandra.

        :param id: The Record ID to associate the files to.
        :param files: The list of files to insert.
        :param force_overwrite: Whether to forcibly overwrite preexisting files.
                                Currently only used by Cassandra DAOs.
        """
        LOGGER.debug('Inserting %i files to record id=%s and force_overwrite=%s.',
                     len(files), id, force_overwrite)
        create = (schema.DocumentFromRecord.create if force_overwrite
                  else schema.DocumentFromRecord.if_not_exists().create)
        for uri, file_info in six.iteritems(files):
            create(id=id,
                   uri=uri,
                   mimetype=file_info.get('mimetype'),
                   tags=file_info.get('tags'))

    def delete(self, ids):
        """
        Given a(n iterable of) Record id(s), delete the Record(s) from the current database.

        Removes everything: data, related relationships, files. Relies on
        Cassandra batching, one batch per Record if there's only one Record to
        delete, else one batch overall.

        :param ids: The id or list of ids of the Record(s) to delete
        """
        if isinstance(ids, six.string_types):
            with BatchQuery() as batch:
                self._setup_batch_delete(batch, ids)
        else:
            with BatchQuery() as batch:
                for id in ids:
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
        LOGGER.debug("Generating batch deletion commands for %s", record_id)
        record = self.get(record_id)
        # Delete from the record table itself
        schema.Record.objects(id=record_id).batch(batch).delete()
        # Delete every file
        schema.DocumentFromRecord.objects(id=record_id).batch(batch).delete()
        # Delete every piece of data
        # Done a bit differently because record_id isn't always the partition key
        for name, datum in six.iteritems(record['data']):
            schema.cross_batch_delete_query_tables(id=record_id,
                                                   name=name,
                                                   value=datum['value'],
                                                   batch=batch)

        # Because Relationships are created separately from Records, we have to
        # manually discover all relationships. Because they are mirrored, we
        # can do this efficiently and without allow_filtering.
        obj_when_rec_is_subj = (schema.ObjectFromSubject.objects(subject_id=record_id)
                                .values_list('object_id', 'predicate'))
        for obj, pred in obj_when_rec_is_subj:
            (schema.SubjectFromObject.objects(object_id=obj,
                                              predicate=pred,
                                              subject_id=record_id)
             .batch(batch).delete())
        schema.ObjectFromSubject.objects(subject_id=record_id).batch(batch).delete()

        # Now again with the other table.
        subj_when_rec_is_obj = (schema.SubjectFromObject.objects(object_id=record_id)
                                .values_list('subject_id', 'predicate'))
        for subj, pred in subj_when_rec_is_obj:
            (schema.ObjectFromSubject.objects(subject_id=subj,
                                              predicate=pred,
                                              object_id=record_id)
             .batch(batch).delete())
        schema.SubjectFromObject.objects(object_id=record_id).batch(batch).delete()

    def get_raw(self, id_):
        try:
            query = schema.Record.objects.filter(id=id_).get()
            return query.raw
        except DoesNotExist:  # Raise a more familiar, descriptive error.
            raise ValueError("No Record found with id {}".format(id_))

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
        :returns: A generator of Record ids that fulfill all criteria.

        :raises ValueError: if not supplied at least one criterion or given
                            a criterion it does not support.
        """
        LOGGER.debug('Finding all records fulfilling criteria: %s', kwargs.items())
        # No kwargs is bad usage. Bad kwargs are caught in sort_and_standardize_criteria().
        # We will always have at least one entry in one of scalar, string, scalarlist, etc.
        if not kwargs.items():
            raise ValueError("You must supply at least one criterion.")
        (scalar, string, scalarlist,
         stringlist, universal) = utils.sort_and_standardize_criteria(kwargs)
        result_ids = []

        # String and scalar values can be passed directly to _apply_ranges_to_query
        for criteria, table_type in ((scalar, "scalar"),
                                     (string, "string")):
            if criteria:
                result_ids.append(self._apply_ranges_to_query(criteria,
                                                              table_type))

        # List values have special logic per type
        result_ids += [self._string_list_query(datum_name=name,
                                               string_list=list_criteria.value,
                                               operation=list_criteria.operation)
                       for name, list_criteria in stringlist]
        result_ids += [self._scalar_list_query(datum_name=name,
                                               data_range=range_criteria.value,
                                               operation=range_criteria.operation)
                       for name, range_criteria in scalarlist]

        # Universal values come in only one type for now.
        if universal:
            result_ids.append(self._universal_query(universal))

        # If we have more than one set of data, we need to find the intersect.
        for id in utils.intersect_lists(result_ids):
            yield id

    def _apply_ranges_to_query(self, data, table):
        """
        Return the ids of all Records whose data fulfill table-specific AND criteria.

        Done per table, unlike data_query. This is only meant to be used in
        conjunction with data_query() and related. Criteria can be DataRanges
        or single values (12, "dog", etc). As such, it is not used for the list
        data tables.

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
        :param table: The name of the table, to look up in TABLE_LOOKUP (module-level var)

        :returns: a generator of ids fitting the criteria
        """
        rec_table = TABLE_LOOKUP[table]["record_table"]
        data_table = TABLE_LOOKUP[table]["data_table"]
        query = rec_table.objects
        # Cassandra requires a list for the in-predicate
        filtered_ids = list(self._configure_query_for_criteria(query,
                                                               name=data[0][0],
                                                               criteria=data[0][1])
                            .values_list('id', flat=True))

        # Only do the next part if there's more criteria and at least one id
        for counter, (name, criteria) in enumerate(data[1:]):
            if filtered_ids:
                query = (self._configure_query_for_criteria(data_table.objects, name, criteria)
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

    @staticmethod
    def _configure_query_for_criteria(query, name, criteria):
        """
        Use criteria to build a query.

        Note that this returns a query object, not a completed query. It's
        a helper for data query methods to build the queries they execute.

        :param query: The query object to consider
        :param name: The name of the data being queries
        :param criteria: The criteria we're filtering the query on.

        :returns: The query object with criteria-appropriate filters
                  applied.
        """
        LOGGER.debug('Configuring <query=%s> with <criteria=%s>.', query, criteria)
        query = query.filter(name=name)
        if not isinstance(criteria, utils.DataRange):
            query = query.filter(value=criteria)
        elif criteria.is_single_value():
            query = query.filter(value=criteria.min)
        else:
            if criteria.min_is_finite():
                if criteria.min_inclusive:
                    query = query.filter(value__gte=criteria.min)
                else:
                    query = query.filter(value__gt=criteria.min)
            if criteria.max_is_finite():
                if criteria.max_inclusive:
                    query = query.filter(value__lte=criteria.max)
                else:
                    query = query.filter(value__lt=criteria.max)
        return query

    @staticmethod
    def _string_list_query(datum_name, string_list, operation):
        """
        Return all Records where [datum_name] fulfills [operation] for [string_list].

        Helper method for data_query.

        :param datum_name: The name of the datum
        :param string_list: A list of strings datum_name must contain.
        :pram operation: What kind of ListQueryOperation to do.
        :returns: A generator of ids of matching Records or the Records
                  themselves (see ids_only).

        :raises ValueError: if given an invalid operation for a string list
        """
        def get_list_rows_with_val(value):
            """Return StringList ids with matching value for datum_name."""
            query = schema.RecordFromStringListData.filter(name=datum_name, value=value)
            return query.values_list('id', flat=True)

        # Pre-populate. Necessary for ALL, harmless for ANY
        distinct_ids = set(get_list_rows_with_val(string_list[0]))

        if operation == utils.ListQueryOperation.HAS_ALL:
            set_func = distinct_ids.intersection_update
        elif operation == utils.ListQueryOperation.HAS_ANY:
            set_func = distinct_ids.update
        else:
            # This can only happen if there's an operation that accepts a list
            # of strings but is not supported by string_list_query.
            raise ValueError("Given an invalid operation for a string list query: {}"
                             .format(operation.value))

        for string in string_list[1:]:
            set_func(get_list_rows_with_val(string))

        return distinct_ids

    @staticmethod
    def _scalar_list_query(datum_name, data_range, operation):
        """
        Return all Records where [datum_name] fulfills [operation] for [data_range].

        Helper method for data_query.

        :param datum_name: The name of the datum
        :param data_range: A datarange to be used with <operation>
        :pram operation: What kind of ListQueryOperation to do.
        :returns: A generator of ids of matching Records.

        :raises ValueError: if given an invalid operation for a datarange
        """
        LOGGER.info('Finding Records where datum %s has %s in %s', datum_name,
                    operation.value.split('_')[0], data_range)

        # Because Cassandra won't let us filter sequential keys, we need to use 2 tables.
        query_tables = {"min": schema.RecordFromScalarListDataMin,
                        "max": schema.RecordFromScalarListDataMax}

        # Cassandra's filters use kwargs. We'll have to build names then unpack.
        if operation == utils.ListQueryOperation.ALL_IN:
            # (What must be [>,>=] the criterion's min, [<,<=] the criterion's max)
            op_cols = ("min", "max")
        elif operation == utils.ListQueryOperation.ANY_IN:
            op_cols = ("max", "min")
        else:
            raise ValueError("Given an invalid operation for a scalar range query: {}"
                             .format(operation.value))

        # Set whether it's > or >=, < or <=
        record_ids = []
        if data_range.min is not None:
            op_desc = op_cols[0]+"__gte" if data_range.min_inclusive else op_cols[0]+"__gt"
            record_ids.append(set(query_tables[op_cols[0]].objects
                                  .filter(name=datum_name)
                                  .filter(**{op_desc: data_range.min})
                                  .values_list('id', flat=True)))
        if data_range.max is not None:
            op_desc = op_cols[1]+"__lte" if data_range.max_inclusive else op_cols[1]+"__lt"
            record_ids.append(set(query_tables[op_cols[1]].objects
                                  .filter(name=datum_name)
                                  .filter(**{op_desc: data_range.max})
                                  .values_list('id', flat=True)))
        for record_id in set.intersection(*record_ids):
            yield record_id

    @staticmethod
    def _universal_query(universal_criteria):
        """
        Pull back all record ids fulfilling universal criteria.

        We currently need #criteria * #tables queries to do this due to the inability
        to query across partitions ("for every Record" doesn't work as one query).

        :param universal_criteria: List of tuples: (datum_name, UniversalCriteria)
        :return: generator of ids of Records fulfilling all criteria.
        """
        query_tables = [schema.RecordFromScalarData, schema.RecordFromStringData,
                        schema.RecordFromStringListData, schema.RecordFromScalarListDataMin]
        desired_names = [x[0] for x in universal_criteria]
        LOGGER.info('Finding Records where data in %s exist', desired_names)
        result_counts = defaultdict(lambda: 0)
        expected_result_count = len(universal_criteria)
        for query_table in query_tables:
            for name in desired_names:
                query = query_table.objects.filter(name=name).values_list('id', flat=True)
                for rec_id in query:
                    result_counts[rec_id] += 1
        for entry, val in six.iteritems(result_counts):
            if val == expected_result_count:
                yield entry

    def _get_many(self, ids, _record_builder, chunk_size):
        """
        Apply some "get" function to an iterable of Record ids.

        Used by the parent get(), this is the Cassandra-specific implementation of
        getting multiple Records.

        :param ids: An iterable of Record ids to return
        :param chunk_size: Currently unused for Cassandra
        :param _record_builder: The function used to create a Record object
                                (or one of its children) from the raw.

        :returns: A generator of Records if found.

        :raises ValueError: if a Record with the id can't be found.
        """

        results = schema.Record.objects.filter(schema.Record.id.in_(ids))
        ids_found = 0
        for result in results:
            yield _record_builder(json_input=json.loads(result.raw))
            ids_found += 1

        if ids_found != len(ids):
            raise ValueError("No Record found with id in %s" % ids)

    def _one_exists(self, test_id):
        """
        Given an id, return boolean of if it exists or not.
        This is the Cassandra specific implementation.

        :param id: The id of the Record to test.

        :returns: A single boolean value pertaining to the id's existence.
        """
        try:
            _ = schema.Record.objects.filter(id=test_id).get()
            return True
        except DoesNotExist:
            return False

    def _many_exist(self, test_ids):
        """
        Given an iterable of ids, return boolean list of whether those
        records exist or not.
        This is the Cassandra specific implementation

        :param ids: The ids of the Records to test.

        :returns: A generator of bools pertaining to the ids' existence.
        """
        test_ids = list(test_ids)
        actual_ids = set(schema.Record.objects
                         .filter(schema.Record.id.in_(test_ids))
                         .values_list('id', flat=True))
        for test_id in test_ids:
            yield test_id in actual_ids

    def get_all(self, ids_only=False):
        """
        Return all Records.

        :param ids_only: whether to return only the ids of matching Records

        :returns: A generator of all Records.
        """
        LOGGER.debug('Getting all records')
        if ids_only:
            query = (schema.Record.objects.values_list('id', flat=True))
            for id in query:
                yield str(id)
        else:
            results = schema.Record.objects
            for result in results:
                yield model.generate_record_from_json(json_input=json.loads(result.raw))

    def get_all_of_type(self, type, ids_only=False):
        """
        Given a type of Record, return all Records of that type.

        :param type: The type of Record to return, ex: run
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of Records of that type or (if ids_only) a
                  generator of their ids
        """
        LOGGER.debug('Getting all records of type %s.', type)
        # There's an index on type, which should be alright as type is expected
        # to have low cardinality. If speed becomes an issue, a dedicated query table might help.
        query = (schema.Record.objects.filter(type=type).values_list('id', flat=True))
        if ids_only:
            for id in query:
                yield str(id)
        else:
            for record in self.get(query):
                yield record

    def get_with_curve_set(self, curve_set_name, ids_only=False):
        """
        Given the name of a curve set, return Records containing it.

        :param curve_set_name: The name of the group of curves
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of Records of that type or (if ids_only) a
                  generator of their ids
        """
        LOGGER.debug('Getting all records with curve sets named %s.', curve_set_name)
        query = (schema.RecordFromCurveSetMeta.filter(name=curve_set_name)
                 .values_list('id', flat=True))
        if ids_only:
            for record_id in query.all():
                yield record_id
        else:
            for record in self.get(query.all()):
                yield record

    def get_available_types(self):
        """
        Return a list of all the Record types in the database.

        :returns: A list of types present (ex: ["run", "experiment"])
        """
        # CQL's "distinct" is limited to partition columns (ID) and "static" columns only.
        return list(set(schema.Record.objects.values_list('type', flat=True)))

    def data_names(self, record_type, data_types=None):
        """
        Return a list of all the data labels for data of a given type.
        Defaults to getting all data names for a given record type.

        :param record_type: Type of records to get data names for.
        :param data_types: A single data type or a list of data types
                           to get the data names for.

        :returns: A generator of data names.
        """
        type_name_to_tables = {'scalar': schema.ScalarDataFromRecord,
                               'string': schema.StringDataFromRecord}
        possible_types = list(type_name_to_tables.keys())
        if data_types is None:
            data_types = possible_types
        if not isinstance(data_types, list):
            data_types = [data_types]
        if not set(data_types).issubset(set(possible_types)):
            raise ValueError('Only select data types from: %s' % possible_types)

        query_tables = [type_name_to_tables[type] for type in data_types]

        ids = list(self.get_all_of_type(record_type, ids_only=True))

        for query_table in query_tables:
            results = set(query_table.objects
                          .filter(query_table.id.in_(ids))
                          .values_list('name', flat=True))
            for result in results:
                yield result

    def get_given_document_uri(self, uri, accepted_ids_list=None, ids_only=False):
        """
        Return all records associated with documents whose uris match some arg.

        Temporary implementation. THIS IS A VERY SLOW, BRUTE-FORCE STRATEGY!
        You use it at your own risk! Do not expect it to be performant or
        particularly stable. To avoid duplications, while it does return
        a generator, it actually returns a generator of a set (so there's
        no memory conserved).

        Supports the use of % as a wildcard character.

        :param uri: The uri to use as a search term, such as "foo.png"
        :param accepted_ids_list: A list of ids to restrict the search to.
                                  If not provided, all ids will be used.
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of unique found records or (if ids_only) a
                  generator of their ids.
        """
        LOGGER.debug('Getting all records related to uri=%s.', uri)
        if accepted_ids_list:
            LOGGER.debug('Restricting to %i ids.', len(accepted_ids_list))
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
            for id in set(match_ids):
                yield id
        else:
            for record in self.get(set(match_ids)):
                yield record

    def _get_with_max_min_helper(self, scalar_name, count, id_only, sort_ascending):
        """
        Handle shared logic for the max/min functions.

        :param sort_ascending: Whether the smallest value should be at the top (True)
                               or the bottom (False)
        """
        # Relies on Cassandra data always being stored sorted.
        order_by = 'value' if sort_ascending else '-value'
        ids = (schema.RecordFromScalarData.objects.filter(name=scalar_name)
               .order_by(order_by).limit(count).all().values_list('id', flat=True))
        return ids if id_only else self.get(ids)

    def get_with_max(self, scalar_name, count=1, id_only=False):
        """
        Return the Record object(s) associated with the highest value(s) of scalar_name.

        This and its partner rely on Cassandra data being stored sorted. This is a
        guarantee of the backend.

        Highest first, then second-highest, etc, until <count> records have been listed.
        This will only return records for plain scalars (not lists of scalars, strings, or
        list of strings).

        :param scalar_name: The name of the scalar to find the maximum record(s) for.
        :param count: How many to return.
        :param id_only: Whether to only return the id

        :returns: An iterator of the record objects or ids corresponding to the
                  <count> largest <scalar_name> values, ordered largest first.
        """
        return self._get_with_max_min_helper(scalar_name, count, id_only, sort_ascending=False)

    def get_with_min(self, scalar_name, count=1, id_only=False):
        """
        Return the Record objects or ids associated with the lowest values of <scalar_name>.

        Lowest first, then second-lowest, etc, until <count> records have been listed.
        This will only return records for plain scalars (not lists of scalars, strings, or
        list of strings).

        :param scalar_name: The name of the scalar to find the minumum record(s) for.
        :param count: How many to return.
        :param id_only: Whether to only return the id

        :returns: An iterator of the record objects or ids corresponding to the
                  <count> smallest <scalar_name> values, ordered smallest first.
        """
        return self._get_with_max_min_helper(scalar_name, count, id_only, sort_ascending=True)

    def get_data_for_records(self, data_list, id_list=None, omit_tags=False):
        """
        Retrieve a subset of data for Records (or optionally a subset of Records).

        NOTE: This is not for list-type data! If you have a use case involving
        getting list-type data for large numbers of Records at once, please
        let us know. For now, list-type data is ignored.

        This method might, for example, get "debugger_version" and "volume" for the
        Records with ids "foo_1" and "foo_3". Results are returned in a dictionary of
        dictionaries; the outer key is the record_id, the inner key is the
        name of the data piece (ex: "volume"). So::

            {"foo_1": {"volume": {"value": 12, "units": cm^3},
                       "debugger_version": {"value": "alpha"}}
             "foo_3": {"debugger_version": {"value": "alpha"}}

        As seen in foo_3 above, if a piece of data is missing, it won't be
        included; think of this as a subset of a Record's own data. Similarly,
        if a Record ends up containing none of the requested data, it will be
        omitted.

        :param data_list: A list of the names of data fields to find
        :param id_list: A list of the record ids to find data for, None if
                        all Records should be considered.
        :param omit_tags: Whether to avoid returning tags. A Cassandra
                          limitation results in up to id_list*data_list+1
                          queries to include the tags, rather than the single
                          query we'd do otherwise. If you don't need the tags/
                          are on a machine with a slow network connection
                          to the cluster, consider setting this to True.

        :returns: a dictionary of dictionaries containing the requested data,
                 keyed by record_id and then data field name.
        """
        if id_list is not None:
            # Cassandra-driver doesn't handle a gen for id_list safely. Cast early for nice logs.
            id_list = list(id_list)
        LOGGER.debug('Getting data in %s for %s', data_list,
                     'record ids in {}'.format(id_list) if id_list is not None else "all records")
        data = defaultdict(lambda: defaultdict(dict))
        query_tables = ([schema.ScalarDataFromRecord, schema.StringDataFromRecord]
                        if id_list is not None
                        else [schema.RecordFromScalarData, schema.RecordFromStringData])
        values_list = ['id', 'name', 'value', 'units']
        for query_table in query_tables:
            query = (query_table.objects
                     .filter(query_table.name.in_(data_list)))  # pylint: disable=no-member
            if id_list is not None:
                query = query.filter(query_table.id.in_(id_list))  # pylint: disable=no-member
            query = query.values_list(*values_list)
            for result in query:
                id, name, value, units = result
                datapoint = {"value": value}
                if units:
                    datapoint["units"] = units
                data[id][name] = datapoint

        if not omit_tags:
            for id in data:
                for name in data[id]:
                    tags = self._get_tags_for_datum(id, name)
                    if tags is not None:
                        data[id][name]["tags"] = tags
        return data

    @staticmethod
    def _get_tags_for_datum(id, name):
        """
        Given a specific datum for a specific Record, return its tags.

        Helper method for get_data_for_records.

        We'll go through our data tables until we find the entry, so this
        works for strings and scalars, but not lists or files.

        Cassandra has a limitation wherein any "IN" query stops working
        if one of the columns requested contains collections. 'tags' is a
        collection column. Unfortunately, there's a further limitation
        that a BatchQuery can't select (only create, update, or delete),
        so the best we can do (until they fix one of the above) is to send a
        flurry of tiny queries. If you're using this helper, consider
        adding an optarg to disable returning tags.

        :param id: The id the datum belongs to
        :param name: The name of the datum

        :returns: The corresponding tags, or None if none were found.

        :raises ValueError: if given a name or id not found in the database.
        """
        data_tables = [TABLE_LOOKUP[x]["data_table"] for x in ("scalar", "string")]
        for table in data_tables:
            tags = (table.objects
                    .filter(table.id == id)
                    .filter(table.name == name)
                    .values_list('tags', flat=True)).all()
            if tags:
                return tags[0]
        raise ValueError('No data entry "{}" for record {}'.format(name, id))

    def get_scalars(self, id, scalar_names):
        """
        LEGACY: retrieve scalars for a given record id.

        This is a legacy method. Consider accessing data from Records directly,
        ex scalar_info = my_rec["data"][scalar_name]

        Scalars are returned as a dictionary with the same format as a Record's
        data attribute (it's a subset of it)

        :param id: The record id to find scalars for
        :param scalar_names: A list of the names of scalars to return

        :return: A dict of scalars matching the Sina data specification
        """
        LOGGER.warning("Using deprecated method get_scalars()."
                       "Consider using Record.data instead.")
        LOGGER.debug('Getting scalars=%s for record id=%s', scalar_names, id)
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

    def get_with_mime_type(self, mimetype, ids_only=False):
        """
        Return all records or IDs with documents of a given mimetype.

        :param mimetype: The mimetype to use as a search term
        :param ids_only: Whether to only return the ids

        :returns: Record object or IDs fitting the criteria.
        """
        ids = (schema.DocumentFromRecord.objects.filter(mimetype=mimetype)
               .values_list('id', flat=True))
        return ids if ids_only else self.get(ids)


class RelationshipDAO(dao.RelationshipDAO):
    """The DAO responsible for handling Relationships in Cassandra."""

    def insert(self, relationships=None, subject_id=None,
               object_id=None, predicate=None):
        """
        Given some Relationship(s), import into a Cassandra database.

        This can create an entry from either an existing relationship object
        or from its components (subject id, object id, predicate). If all four
        are provided, the Relationship will be used. If inserting many
        Relationships, a list of Relationships MUST be provided (and no
        other fields).

        :param relationships: A Relationship object to build entry from or iterable of them.
        :param subject_id: The id of the subject.
        :param object_id: The id of the object.
        :param predicate: A string describing the relationship between subject and oject.
        """
        if (isinstance(relationships, model.Relationship)
                or any(x is not None for x in (subject_id, object_id, predicate))):
            subj, obj, pred = self._validate_insert(relationship=relationships,
                                                    subject_id=subject_id,
                                                    object_id=object_id,
                                                    predicate=predicate)
            schema.cross_populate_object_and_subject(subject_id=subj,
                                                     object_id=obj,
                                                     predicate=pred)
        else:
            LOGGER.debug('Inserting %i relationships.', len(relationships))
            # Batching is done per partition key--we won't know per-partition
            # contents until we've gone through the full list of Relationships.
            from_subject_batch = defaultdict(list)
            from_object_batch = defaultdict(list)

            for rel in relationships:
                from_subject_batch[rel.subject_id].append((rel.predicate,
                                                           rel.object_id))
                from_object_batch[rel.object_id].append((rel.predicate,
                                                         rel.subject_id))
            # Our dictionaries are populated and ready for batch insertion
            for obj, insert_info in six.iteritems(from_object_batch):
                # Only having one entry is a common use case. Skip the overhead!
                if len(insert_info) == 1:
                    schema.cross_populate_object_and_subject(subject_id=insert_info[0][1],
                                                             object_id=obj,
                                                             predicate=insert_info[0][0])
                else:
                    with BatchQuery() as batch_query:
                        for entry in insert_info:
                            (schema.SubjectFromObject
                             .batch(batch_query).create(obj=obj,
                                                        predicate=entry[0],
                                                        subject_id=entry[1]))
            for subj, insert_info in six.iteritems(from_subject_batch):
                # We already handled this use case with the cross_populate above
                if len(insert_info) == 1:
                    pass
                else:
                    with BatchQuery() as batch_query:
                        for entry in insert_info:
                            (schema.ObjectFromSubject
                             .batch(batch_query).create(subject_id=subj,
                                                        predicate=entry[0],
                                                        object_id=entry[1]))

    def get(self, subject_id=None, object_id=None, predicate=None):
        """Retrieve relationships fitting some criteria."""
        LOGGER.debug('Getting relationships with subject_id=%s, '
                     'predicate=%s, object_id=%s.',
                     subject_id, predicate, object_id)

        if subject_id:
            query = schema.ObjectFromSubject.objects.filter(subject_id=subject_id)
            if predicate:
                query = query.filter(predicate=predicate)
            if object_id:
                query = query.filter(object_id=object_id)
        else:
            query = schema.SubjectFromObject.objects
            if object_id:
                query = query.filter(object_id=object_id)

            if predicate:
                query = query.filter(predicate=predicate)

            if subject_id:
                query = query.filter(subject_id=subject_id)

        # Both tables have the predicate in the middle, and the subject
        # and object IDs on either end.
        if predicate:
            # Only need to filter here if we only have the middle column
            need_filtering = not (subject_id or object_id)
        else:
            # Only need to filter here if we skip the middle column -- we don't
            # need to filter when we don't specify any column
            need_filtering = subject_id and object_id

        if need_filtering:
            query = query.allow_filtering()

        return self._build_relationships(query.all())


class DAOFactory(dao.DAOFactory):
    """
    Build Cassandra-backed DAOs for interacting with Sina-based objects.

    Includes Records, Relationships, etc.
    """

    supports_parallel_ingestion = True

    def __init__(self, keyspace, node_ip_list=None, sonar_cqlshrc_path=None):
        """
        Initialize a Factory with a path to its backend.

        :param keyspace: The keyspace to connect to.
        :param node_ip_list: A list of ips belonging to nodes on the target
                            Cassandra instance. If None, connects to localhost.
        :param sonar_cqlshrc_path: Only used when connecting to LC Sonar machines.
                                   The path to the desired cqlshrc file.
        """
        self.keyspace = keyspace
        self.node_ip_list = node_ip_list
        self.sonar_cqlshrc_path = sonar_cqlshrc_path
        schema.form_connection(keyspace, node_ip_list=self.node_ip_list,
                               sonar_cqlshrc_path=self.sonar_cqlshrc_path)

    def create_record_dao(self):
        """
        Create a DAO for interacting with records.

        :returns: a RecordDAO
        """
        return RecordDAO()

    def create_relationship_dao(self):
        """
        Create a DAO for interacting with relationships.

        :returns: a RelationshipDAO
        """
        return RelationshipDAO()

    def close(self):
        """Close resources being used by this factory."""
        # For now, we are using a single shared connection. If we change this in the future,
        # we need to close the Cassandra connection here.
        pass

    def __repr__(self):
        """Return a string representation of a Cassandra DAOFactory."""
        return ('Cassandra DAOFactory <keyspace={}, node_ip_list={}>'
                .format(self.keyspace, self.node_ip_list))
