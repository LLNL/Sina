"""Contains SQL-specific implementations of our DAOs."""
import os
import numbers
import logging
from collections import defaultdict
import functools

import six

# Disable pylint check due to its issue with virtual environments
import sqlalchemy  # pylint: disable=import-error
from sqlalchemy.pool import NullPool  # pylint: disable=import-error
from sqlalchemy.exc import OperationalError  # pylint: disable=import-error

import sina.dao as dao
import sina.sjson as json
import sina.model as model
import sina.datastores.sql_schema as schema
from sina.utils import sort_and_standardize_criteria
from sina import utils
from sina.postprocessing import underlay

# Disable redefined-builtin, invalid-name due to ubiquitous use of id
# pylint: disable=invalid-name,redefined-builtin
# Disable too-many-lines, as a refactor's currently out of scope
# pylint: disable=too-many-lines

LOGGER = logging.getLogger(__name__)

# String used to identify a sqlite database for SQLALchemy
SQLITE_PREFIX = "sqlite:///"

# Identify the tables that store Record.data entries.
DATA_TABLES = [schema.ScalarData, schema.StringData,
               schema.ListScalarData, schema.ListStringDataEntry]

# Set maximum chunk size for id queries
CHUNK_SIZE = 999


def _commit_or_rollback(func):
    """
    Create a wrapper which calls the given function, committing a session
    if it succeeds, or rolling it back if it (or the commit) fails. The first
    argument to the function must be an object with a "session" field.
    This is intended to be used only on the member functions of DAOs below.
    The return value of the wrapped function will be returned by the wrapper.

    :param func: the function to wrap
    :return: the wrapped function
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Wrapper function for the passed-in function."""
        session = args[0].session
        try:
            result = func(*args, **kwargs)
            session.commit()
            return result
        # need to roll back on anything, so use bare except
        except:  # noqa: E722
            session.rollback()
            raise

    return wrapper


class RecordDAO(dao.RecordDAO):
    """The DAO specifically responsible for handling Records in SQL."""

    def __init__(self, session):
        """Initialize RecordDAO with session for its SQL database."""
        self.session = session

    def _insert_no_commit(self, records):
        """Insert without committing; for shared functionality."""
        if isinstance(records, model.Record):
            records = [records]
        for record in records:
            LOGGER.debug('Inserting record %s into SQL.', record.id or record.local_id)
            sql_record = self.create_sql_record(record)
            self.session.add(sql_record)

    @_commit_or_rollback
    def _do_insert(self, records):
        """
        Given a(n iterable of) Record(s), insert into the current SQL database.

        :param records: Record or iterable of Records to insert
        """
        self._insert_no_commit(records)

    @staticmethod
    def create_sql_record(sina_record):
        """
        Create a SQL record object for the given Sina Record.

        :param sina_record: A Record to insert
        :return: the created record
        """
        is_valid, warnings = sina_record.is_valid()
        if not is_valid:
            raise ValueError(warnings)
        sql_record = schema.Record(id=sina_record.id, type=sina_record.type,
                                   raw=json.dumps(sina_record.raw))
        if sina_record.data:
            RecordDAO._attach_data(sql_record, sina_record.data)
        if sina_record.curve_sets:
            RecordDAO._attach_curves(sql_record, sina_record.curve_sets, sina_record.data)
        if sina_record.files:
            RecordDAO._attach_files(sql_record, sina_record.files)

        return sql_record

    @staticmethod
    def _attach_data(record, data):
        """
        Attach the data entries to the given SQL record.

        :param record: The SQL schema record to associate the data to.
        :param data: The dictionary of data to insert.
        """
        LOGGER.debug('Inserting %i data entries to Record ID %s.', len(data), record.id)
        for datum_name, datum in data.items():
            if isinstance(datum['value'], list):
                # Store info such as units and tags in master table
                # Note: SQL doesn't support maps, so we have to convert the
                # tags to a string (if they exist).
                # Using json.dumps() instead of str() (or join()) gives
                # valid JSON
                tags = (json.dumps(datum['tags']) if 'tags' in datum else None)
                if not datum['value']:  # empty list
                    continue  # An empty list can't be queried
                # If we've been given a list of numbers:
                elif isinstance(datum['value'][0], numbers.Real):
                    record.scalar_lists.append(schema.ListScalarData(
                        name=datum_name,
                        min=min(datum['value']),
                        max=max(datum['value']),
                        units=datum.get('units'),  # units might be None, always use get()
                        tags=tags))
                else:
                    # it's a list of strings
                    record.string_lists_master.append(schema.ListStringDataMaster(
                        name=datum_name, units=datum.get('units'), tags=tags))

                    # Each entry in a list of strings requires its own row
                    for index, entry in enumerate(datum['value']):
                        record.string_lists_entry.append(schema.ListStringDataEntry(
                            name=datum_name, index=index, value=entry))
            elif isinstance(datum['value'], (numbers.Number, six.string_types)):
                tags = (json.dumps(datum['tags']) if 'tags' in datum else None)
                if isinstance(datum['value'], numbers.Real):
                    data_type = schema.ScalarData
                    list_in_record = record.scalars
                else:
                    data_type = schema.StringData
                    list_in_record = record.strings
                list_in_record.append(data_type(name=datum_name,
                                                value=datum['value'],
                                                # units might be None, always use get()
                                                units=datum.get('units'),
                                                tags=tags))

    @staticmethod
    def _attach_curves(record, curve_sets, data):
        """
        Attach the curve entries to the given SQL record.

        :param record: The SQL schema record to associate the data to.
        :param curve_sets: The dictionary of curve sets to insert.
        :param data: The dictionary containing data items
        """
        LOGGER.debug('Inserting %i curve set entries to Record ID %s.',
                     len(curve_sets), record.id)

        for curveset_name, curveset_obj in curve_sets.items():
            tags = (json.dumps(curveset_obj['tags']) if 'tags' in curveset_obj else None)
            record.curve_set_meta.append(schema.CurveSetMeta(name=curveset_name,
                                                             tags=tags))
        resolved_sets = utils.resolve_curve_sets(curve_sets, data)
        for entry_name, entry_obj in resolved_sets.items():
            tags = (json.dumps(entry_obj['tags']) if 'tags' in entry_obj else None)
            record.scalar_lists.append(schema.ListScalarData(
                name=entry_name,
                min=min(entry_obj['value']),
                max=max(entry_obj['value']),
                units=entry_obj.get('units'),  # units might be None, always use get()
                tags=tags))

    @staticmethod
    def _attach_files(record, files):
        """
        Attach the file entries to the given SQL record.

        :param record: The Record to associate the files to.
        :param files: The dictionary of files to insert.
        """
        LOGGER.debug('Inserting %i files to record id=%s.', len(files), id)
        for uri, file_info in six.iteritems(files):
            tags = (json.dumps(file_info['tags']) if 'tags' in file_info else None)
            record.documents.append(schema.Document(uri=uri,
                                                    mimetype=file_info.get('mimetype'),
                                                    tags=tags))

    def _delete_no_commit(self, ids):
        """Delete without committing; for shared functionality."""
        if isinstance(ids, six.string_types):
            ids = [ids]
        LOGGER.debug('Deleting records with ids in: %s', ids)
        (self.session.query(schema.Record)
         .filter(schema.Record.id.in_(ids))
         .delete(synchronize_session='fetch'))

    @_commit_or_rollback
    def delete(self, ids):
        """
        Given a(n iterable of) Record id(s), delete all mention from the SQL database.

        This includes removing all data, raw(s), relationships, etc.
        Because the id is a foreign key in every table
        (besides Record itself but including Run, etc), we can rely on
        cascading to propogate the deletion.

        :param ids: The id or iterable of ids of the Record(s) to delete.
        """
        self._delete_no_commit(ids)

    def get_raw(self, id_):
        result = (self.session.query(schema.Record)
                  .filter(schema.Record.id == id_).one_or_none())

        if result is None:
            raise ValueError("No Record found with id %s" % id_)

        return _to_json_string(result.raw)

    @_commit_or_rollback
    def _do_update(self, records):
        """
        Given a list of Records, update them in the backend in a single transaction.

        :param records: A list of Records to update.
        """
        # Note that session.merge() does not delete removed attributes, hence the
        # manual delete-reinsert. We also need to be sure we preserve relationships,
        # since they would otherwise cascade delete.
        temp_rel_dao = RelationshipDAO(self.session)
        for record in records:
            old_subject_relationships = temp_rel_dao.get(subject_id=record.id)
            old_object_relationships = temp_rel_dao.get(object_id=record.id)
            self._delete_no_commit(record.id)
            self._insert_no_commit(record)
            self.session.flush()  # Ensure the record exists before re-adding relationships
            temp_rel_dao.insert(old_object_relationships)
            temp_rel_dao.insert(old_subject_relationships)

    @_commit_or_rollback
    def _do_update_appendonly(self, records):
        """
        Given a list of Records, update them in the backend in a single transaction.

        :param records: A list of Records to update.
        """
        new_records = []
        for record in records:
            # Replaces values from old record into new record
            # that way only appends are new
            old_record = list(super(RecordDAO, self)._find(id_pool=[record.id]))[0]
            underlay_func = underlay(record)
            new_records.append(underlay_func(old_record))

        self._do_update(new_records)

    # pylint: disable=too-many-locals, too-many-branches
    def _do_data_query(self, criteria, id_pool=None, alias_dict=None):
        """
        Handle the backend-specific logic for the dao data_query.

        :param criteria: Dict of {data_name: criteria_to_fulfill}
        :param id_pool: List of ids to restrict results to.
        :param alias_dict: An alias dictionary to find differently named data across records
        :returns: A generator of Record ids that fulfill all criteria.

        :raises ValueError: if not supplied at least one criterion or given
                            a criterion it does not support
        """
        # For data_query() method since everything gets passed in as criteria
        if alias_dict is None and 'alias_dict' in criteria:
            alias_dict = criteria.get('alias_dict')
            criteria.pop('alias_dict')

        # Finding relevant keys and values
        if alias_dict:
            # Flattening the alias dict
            alias_flattened = [[]] * len(alias_dict)
            for i, (key, val) in enumerate(alias_dict.items()):
                alias_flattened[i] = [key]
                if isinstance(val, list):
                    alias_flattened[i].extend(val)
                elif isinstance(val, str):
                    alias_flattened[i].extend([val])

            # Creating dictionary based on original arg values
            alias = {}
            for a in criteria:
                for alias_list in alias_flattened:
                    if a in alias_list:
                        if alias.get(a) is None:
                            alias[a] = alias_list
                        else:
                            raise KeyError(f'Alias {a} already in multiple locations!')

            alias_dict = alias

        (scalar_criteria,
         string_criteria,
         scalar_list_criteria,
         string_list_criteria,
         universal_criteria) = sort_and_standardize_criteria(criteria)
        sub_queries = []

        # First handle scalar and string criteria
        if scalar_criteria:
            sub_queries.append(self._generate_data_table_query(scalar_criteria, schema.ScalarData,
                                                               alias_dict=alias_dict))
        if string_criteria:
            sub_queries.append(self._generate_data_table_query(string_criteria, schema.StringData,
                                                               alias_dict=alias_dict))

        # Move on to any list criteria
        sub_queries += [self._string_list_query(datum_name=datum_name,
                                                string_list=list_criteria.value,
                                                operation=list_criteria.operation,
                                                alias_dict=alias_dict)
                        for datum_name, list_criteria in string_list_criteria]
        sub_queries += [self._scalar_list_query(datum_name=datum_name,
                                                data_range=list_criteria.value,
                                                operation=list_criteria.operation,
                                                alias_dict=alias_dict)
                        for datum_name, list_criteria in scalar_list_criteria]

        joined_query = self.session.query(schema.Record.id)
        if id_pool is not None:
            joined_query = joined_query.filter(schema.Record.id.in_(id_pool))
        for sub_query in sub_queries:
            sub_query = sub_query.subquery()
            joined_query = joined_query.join(sub_query, schema.Record.id == sub_query.c.id)

        # Universal criteria currently go cross-table and have to be handled
        # with Python logic
        if universal_criteria:
            universal_pool = self._universal_query(universal_criteria, alias_dict=alias_dict)
            if not sub_queries and id_pool is None:
                return universal_pool
            universal_pool = set(universal_pool)
            return (x[0] for x in joined_query.all() if x[0] in universal_pool)

        return (x[0] for x in joined_query.all())

    def _scalar_list_query(self, datum_name, data_range, operation, alias_dict=None):
        """
        Return all Records where [datum_name] fulfills [operation] for [data_range].

        Helper method for data_query.

        :param datum_name: The name of the datum
        :param data_range: A datarange to be used with <operation>
        :pram operation: What kind of ListQueryOperation to do.
        :param alias_dict: An alias dictionary to find differently named data across records
        :returns: A query object returning ids of matching Records.

        :raises ValueError: if given an invalid operation for a datarange
        """
        LOGGER.info('Finding Records where datum %s has %s in %s', datum_name,
                    operation.value.split('_')[0], data_range)
        table = schema.ListScalarData

        if alias_dict:
            temp = alias_dict.get(datum_name, [datum_name])
            datum_name = temp
        else:
            datum_name = [datum_name]

        if len(datum_name) == 1:
            range_criteria = [table.name == datum_name[0]]
        else:
            range_criteria = [table.name.in_(datum_name)]

        query = self.session.query(table.id).filter(*range_criteria)

        filters = []
        if operation == utils.ListQueryOperation.ALL_IN:
            # What must be [>,>=] the criterion's min
            # Note that "min" and "max" are columns (the min and max vals found in some list datum)
            gt_crit_min = table.min
            # What must be [<,<=] the criterion's max
            lt_crit_max = table.max
        elif operation == utils.ListQueryOperation.ANY_IN:
            gt_crit_min = table.max
            lt_crit_max = table.min
        else:
            raise ValueError("Given an invalid operation for a scalar range query: {}"
                             .format(operation.value))
        # Set whether it's > or >=, < or <=
        if data_range.min is not None:
            col_op = gt_crit_min.__ge__ if data_range.min_inclusive else gt_crit_min.__gt__
            filters.append(col_op(data_range.min))
        if data_range.max is not None:
            col_op = lt_crit_max.__le__ if data_range.max_inclusive else lt_crit_max.__lt__
            filters.append(col_op(data_range.max))

        return query.filter(*filters)

    def _string_list_query(self, datum_name, string_list, operation, alias_dict=None):
        """
        Return all Records where [datum_name] fulfills [operation] for [string_list].

        Helper method for data_query.

        :param datum_name: The name of the datum
        :param string_list: A list of strings datum_name must contain.
        :param operation: What kind of ListQueryOperation to do.
        :param alias_dict: An alias dictionary to find differently named data across records
        :returns: A query object returning matching Records or the Records
                  themselves (see ids_only).

        :raises ValueError: if given an invalid operation for a string list
        """
        LOGGER.info('Finding Records where datum %s contains %s: %s', datum_name,
                    operation.value.split('_')[1], string_list)
        criteria_tuples = [(datum_name, x) for x in string_list]
        if operation == utils.ListQueryOperation.HAS_ALL:
            query = self._generate_data_table_query(table=schema.ListStringDataEntry,
                                                    criteria_pairs=criteria_tuples,
                                                    alias_dict=alias_dict)
        elif operation == utils.ListQueryOperation.HAS_ANY:
            query = self._generate_data_table_query(table=schema.ListStringDataEntry,
                                                    criteria_pairs=criteria_tuples,
                                                    fulfill_all=False,
                                                    alias_dict=alias_dict)
        else:
            # This can only happen if there's an operation that accepts a list
            # of strings but is not supported by string_list_query.
            raise ValueError("Given an invalid operation for a string list query: {}"
                             .format(operation.value))
        return query

    @staticmethod
    def _generate_criterion_filters(criterion_pair, table, alias_dict=None):
        """
        Generate the AND expression fulfilling a single criterion pair.

        :param criterion_pair: A tuple of (datum_name, criterion). Criterion must be a DataRange
                               or single value, ex: 6, "low_frequency"
        :param table: The table the datum is expected to exist in
        :param alias_dict: An alias dictionary to find differently named data across records
        :return: A SQLAlchemy AND expression fulfilling the criterion pair
        """
        datum_name, criterion = criterion_pair

        if alias_dict:
            temp = alias_dict.get(datum_name, [datum_name])
            datum_name = temp
        else:
            datum_name = [datum_name]

        if len(datum_name) == 1:
            range_criteria = [table.name == datum_name[0]]
        else:
            range_criteria = [table.name.in_(datum_name)]

        if isinstance(criterion, utils.DataRange):
            if not criterion.is_single_value():
                if criterion.min is not None:
                    min_op = table.value.__ge__ if criterion.min_inclusive else table.value.__gt__
                    range_criteria.append(min_op(criterion.min))
                if criterion.max is not None:
                    max_op = table.value.__le__ if criterion.max_inclusive else table.value.__lt__
                    range_criteria.append(max_op(criterion.max))
            else:
                range_criteria.append(table.value.__eq__(criterion.min))
        else:
            range_criteria.append(table.value.__eq__(criterion))
        return sqlalchemy.and_(*range_criteria)

    def _generate_data_table_query(self, criteria_pairs, table, fulfill_all=True, alias_dict=None):
        """
        Generate a query that determines whether a Record fulfills a set of criteria.

        All criteria must belong to a single table. This is used to generate a single
        query rather than chaining together multiple queries--see "criteria"

        :param criteria_pairs: A list of (datum_name, criterion) tuples. All datum_names are
                               expected to correspond to entries in the same table.
        :param table: The table the data are expected to exist in.
        :param fulfill_all: Whether we should ensure every criteria_pair is fulfilled. If
                            false, only one or more pairs need to be fulfilled
                            (ex: has_any() list query)
        :param alias_dict: An alias dictionary to find differently named data across records

        :return: A query object representing <criterion> applied to <datum_name> in <table>.
        """
        query = self.session.query(table.id)
        criteria_queries = [self._generate_criterion_filters(pair, table, alias_dict=alias_dict)
                            for pair in criteria_pairs]

        query = query.filter(sqlalchemy.or_(*criteria_queries))

        # Since we don't know the possible data names a priori, we have a row per datum
        # and have to "or" them together and then group by record ID, selecting the records
        # that have a matching row for each queried criterion (# rows == # criteria).
        # This is why the OR and AND queries use the same basic query; the AND
        # query just takes it a step further.
        if len(criteria_pairs) > 1:
            query = query.group_by(table.id)

            if fulfill_all and alias_dict is None:
                query = query.having(sqlalchemy.func.count(table.id) == len(criteria_pairs))
            elif fulfill_all and alias_dict is not None:
                # Alias dict will have more criteria_pairs
                query = query.having(sqlalchemy.func.count(table.id) >= len(criteria_pairs))

        return query

    def _get_many(self, ids, _record_builder, chunk_size):
        """
        Apply some "get" function to an iterable of Record ids.
        Used by the parent get(), this is the SQL-specific implementation of
        getting multiple Records.
        ...

        :param ids: An iterable of Record ids to return
        :param chunk_size: Size of chunks to pull records in.
        :param _record_builder: The function used to create a Record object
                                (or one of its children) from the raw.
        :returns: A generator of Record objects
        """
        chunks = [ids[x:x+chunk_size] for x in range(0, len(ids), chunk_size)]
        for chunk in chunks:
            ids_found = 0
            results = (self.session.query(schema.Record)
                       .filter(schema.Record.id.in_(chunk)))

            for result in results:
                ids_found += 1
                yield _record_builder(json_input=_json_loads(result.raw))

            if ids_found != len(chunk):
                raise ValueError("No Record found with id in chunk %s" % chunk)

    def get_all(self, ids_only=False):
        """
        Return all Records.

        :param ids_only: whether to return only the ids of matching Records

        :returns: A generator of all Records.
        """
        LOGGER.debug('Getting all records')
        if ids_only:
            query = self.session.query(schema.Record.id)
            for record_id in query:
                yield str(record_id[0])
        else:
            results = self.session.query(schema.Record)
            for result in results:
                yield model.generate_record_from_json(
                    json_input=_json_loads(result.raw))

    def _do_get_all_of_type(self, types, ids_only=False, id_pool=None):
        """SQL-specific implementation of DAO's _do_get_all_of_type."""
        if isinstance(types, utils.Negation):
            filter_func = schema.Record.type.notin_
            types = types.arg
        else:
            filter_func = schema.Record.type.in_

        query = (self.session.query(schema.Record.id)
                 .filter(filter_func(types)))
        if id_pool is not None:
            query = query.filter(schema.Record.id.in_(id_pool))

        if ids_only:
            for record_id in query.all():
                yield str(record_id[0])
        else:
            filtered_ids = (str(x[0]) for x in query.all())
            for record in self.get(filtered_ids):
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
        query = (self.session.query(schema.CurveSetMeta.id)
                 .filter(schema.CurveSetMeta.name == curve_set_name))
        if ids_only:
            for record_id in query.all():
                yield str(record_id[0])
        else:
            filtered_ids = (str(x[0]) for x in query.all())
            for record in self.get(filtered_ids):
                yield record

    def _one_exists(self, test_id):
        """
        Given an id, return boolean
        This is the SQL specific implementation.

        :param id: The id of the Record to test.

        :returns: A single boolean value pertaining to the id's existence.
        """
        query = (self.session.query(schema.Record.id)
                 .filter(schema.Record.id == test_id).one_or_none())
        return bool(query)

    def _many_exist(self, test_ids):
        """
        Given an iterable of ids, return boolean list of whether those
        records exist or not.
        This is the SQL specific implementation

        :param ids: The ids of the Records to test.

        :returns: A generator of bools pertaining to the ids' existence.
        """
        test_ids = list(test_ids)
        chunks = [test_ids[x:x+CHUNK_SIZE] for x in range(0, len(test_ids), CHUNK_SIZE)]
        for chunk in chunks:
            query = (self.session.query(schema.Record.id)
                     .filter(schema.Record.id.in_(chunk)))
            actual_ids = set((str(x[0]) for x in query.all()))
            for test_id in chunk:
                yield test_id in actual_ids

    # pylint: disable=too-many-locals
    def _universal_query(self, universal_criteria, alias_dict=None):
        """
        Pull back all record ids fulfilling universal criteria.

        We do all criteria in a single query per table, as there's only one
        possible universal query right now.

        :param universal_criteria: List of tuples: (datum_name, UniversalCriteria)
        :param alias_dict: An alias dictionary to find differently named data across records
        :return: generator of ids of Records fulfilling all criteria.
        """
        result_counts = defaultdict(set)
        desired_names = [x[0] for x in universal_criteria]

        if alias_dict:
            temp = []
            for name in desired_names:
                temp += alias_dict.get(name, name)
            desired_names = temp

        LOGGER.info('Finding Records where data in %s exist', desired_names)
        expected_result_count = len(universal_criteria)
        for query_table in DATA_TABLES:
            # OLD:
            # We know that a single Record can never have more than one datum with
            # a given name, so all we need to get is count.
            # NOW (fixed bug):
            # They can if curve set and data "collide"! We need to allow those.
            query = (self.session.query(query_table.id, query_table.name)
                     .filter(query_table.name.in_(desired_names)))
            for id, found in query:
                result_counts[id].add(found)
        for entry, val in six.iteritems(result_counts):
            if len(val) == expected_result_count and alias_dict is None:
                yield entry

            # alias dict can cause multiple data from same record to show up
            # which gives a false positive. Statement below checks if data
            # is from the same alias. E.g. id = 'shared_curve_set_and_matching_scalar_data'
            # contains both "shared_scalar" and "test_data_5" from
            # alias_dict = {"shared_scalar": ["test_data_1", "test_data_5"]}
            elif len(val) == expected_result_count and alias_dict:
                for _, aval in alias_dict.items():
                    same_alias = 0
                    for v in val:
                        if v in aval:
                            same_alias += 1
                    if same_alias == 1:
                        yield entry

    # High arg count is inherent to the functionality.
    # pylint: disable=too-many-arguments
    def _find(self, types=None, data=None, file_uri=None,
              mimetype=None, id_pool=None, ids_only=False,
              query_order=("data", "file_uri", "mimetype", "types"), alias_dict=None):
        """Implement cross-backend logic for the DataStore method of the same name."""
        try:
            return super(RecordDAO, self)._find(types=types, data=data, file_uri=file_uri,
                                                mimetype=mimetype, id_pool=id_pool,
                                                ids_only=ids_only, query_order=query_order,
                                                alias_dict=alias_dict)
        # We may have issues when too many ids are returned due to the (compile time)
        # limit on variables, as IN counts every id as a variable. If so, use an
        # alternate form of query.
        except OperationalError:
            return self._find_with_manual_intersection(types=types, data=data, file_uri=file_uri,
                                                       mimetype=mimetype, id_pool=id_pool,
                                                       ids_only=ids_only,
                                                       query_order=query_order)

    # pylint: disable=too-many-arguments
    def _find_with_manual_intersection(self, types=None, data=None, file_uri=None,
                                       mimetype=None, id_pool=None, ids_only=False,
                                       query_order=("data", "file_uri", "mimetype", "types"),
                                       alias_dict=None):
        """
        Perform a _find() that uses id_pool intersection.

        Provided as a workaround for large id_pools potentially tripping the compile
        time SQL limit on maximum variables in a query.
        """
        if id_pool is not None:
            id_pool = set(id_pool)
        # Note, same map as in dao.py's _find().
        query_map = {"data": (self._do_data_query, data),
                     "file_uri": (self._do_get_given_document_uri, file_uri),
                     "mimetype": (self.get_with_mime_type, mimetype),
                     "types": (self.get_all_of_type, types)}

        def get_id_set_from_query_type(query_type):
            """Get ids for a single query."""
            query_func, arg = query_map[query_type]
            if arg is not None:
                if query_type == "data":
                    return query_func(arg, id_pool=id_pool, alias_dict=alias_dict)
                return query_func(arg,  # pylint: disable=unexpected-keyword-arg
                                  id_pool=id_pool,
                                  ids_only=True)
            return None

        individual_pools = [get_id_set_from_query_type(x) for x in query_order]
        for individual_pool in individual_pools:
            if individual_pool is None:  # the query wasn't invoked
                continue
            if id_pool is None:  # first invoked query, no id_pool arg
                id_pool = set(individual_pool)
            else:
                id_pool = id_pool.intersection(individual_pool)
        # Let the DAO handle the logic of returning in the proper format.
        return super(RecordDAO, self)._find(id_pool=id_pool, ids_only=ids_only)

    def get_available_types(self):
        """
        Return a list of all the Record types in the database.

        :returns: A list of types present (ex: ["run", "experiment"])
        """
        results = self.session.query(schema.Record.type).distinct().all()
        return [entry[0] for entry in results]

    def get_curve_set_names(self):
        """
        Return the names of all curve sets available in the backend.

        :returns: An iterable of curve set names.
        """
        return list(x[0] for x in self.session.query(schema.CurveSetMeta.name)
                    .distinct().all())

    def data_names(self, record_type, data_types=None, filter_constants=False):
        """
        Return a list of all the data labels for data of a given type.

        Defaults to getting all data names for a given record type.

        :param record_type: Type of records to get data names for.
        :param data_types: A single data type or a list of data types
                           to get the data names for.
        :param filter_constants: If True, will filter out any string or scalar data
                                 whose value is identical between all records in the
                                 database (such as the density of some material). No
                                 effect on list data.

        :returns: A generator of data names.
        """
        type_name_to_tables = {'scalar': schema.ScalarData,
                               'string': schema.StringData,
                               'scalar_list': schema.ListScalarData,
                               'string_list': schema.ListStringDataEntry}
        possible_data_types = list(type_name_to_tables.keys())
        if data_types is None:
            data_types = possible_data_types
        if not isinstance(data_types, list):
            data_types = [data_types]
        if not set(data_types).issubset(set(possible_data_types)):
            raise ValueError('Only select data types from: %s' % possible_data_types)

        query_tables = [type_name_to_tables[type] for type in data_types]

        for query_table in query_tables:
            if filter_constants and query_table in (schema.ScalarData, schema.StringData):
                results = (self.session.query(query_table.name).join(schema.Record)
                           .filter(schema.Record.type == record_type).group_by(query_table.name)
                           .having(sqlalchemy.func.count(query_table.value.distinct()).__gt__(1)))
            else:
                results = (self.session.query(query_table.name).join(schema.Record)
                           .filter(schema.Record.type == record_type)
                           .distinct())
            for result in results:
                yield result[0]

    def _build_query_given_uri_has_any(self, uri_list):
        """Perform get_given_document_uri when we have a has_any criterion."""
        query = self.session.query(schema.Document.id)
        filters = []
        for uri in uri_list:
            # Note: Mixed results on whether SQLAlchemy's optimizer is smart enough
            # to have %-less LIKE operate on par with ==, hence this:
            if '%' in uri:
                filters.append(schema.Document.uri.like(uri))
            else:
                filters.append(schema.Document.uri.__eq__(uri))
        return query.filter(sqlalchemy.or_(*filters)).group_by(schema.Document.id)

    def _build_query_given_uri_has_all(self, uri_list):
        """Perform get_given_document_uri when we have a has_all criterion."""
        def do_filter(query, uri):
            """Apply the correct filter for a uri."""
            if '%' in uri:
                return query.filter(schema.Document.uri.like(uri))
            return query.filter(schema.Document.uri.__eq__(uri))

        query = do_filter(self.session.query(schema.Document.id, schema.Document.uri), uri_list[0])
        for uri in uri_list[1:]:
            sub_query = do_filter(self.session.query(schema.Document.id), uri).subquery()
            query = query.join(sub_query, schema.Document.id == sub_query.c.id)
        return query

    def _do_get_given_document_uri(self, uri, id_pool=None, ids_only=False):
        """
        Return all records associated with documents whose uris match some arg.

        Supports the use of % as a wildcard character.

        :param uri: The uri or uri criterion to use as a search term, such as
                    "foo.png" or has_any("%success.jpg", "%success.png")
        :param id_pool: A list of ids to restrict the search to.
                        If not provided, all ids will be used.
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of matching records or (if ids_only) a
                  generator of their ids. Returns distinct items.
        """
        query = self.session.query(schema.Document.id,
                                   sqlalchemy.func.count(schema.Document.id))

        if isinstance(uri, utils.StringListCriteria):
            if uri.operation == utils.ListQueryOperation.HAS_ANY:
                query = self._build_query_given_uri_has_any(uri.value)
            else:
                query = self._build_query_given_uri_has_all(uri.value)
        else:
            # Logic is identical for the case of just one uri
            query = self._build_query_given_uri_has_any([uri])
        if id_pool is not None:
            query = query.filter(schema.Document
                                 .id.in_(id_pool))
        if ids_only:
            for record_id in query.all():
                yield record_id[0]
        else:
            filtered_ids = (x[0] for x in query.all())
            for record in self.get(filtered_ids):
                yield record

    def _get_with_max_min_helper(self, scalar_name, count, id_only, get_min):
        """
        Handle shared logic for the max/min functions.

        :param get_min: Whether we should be looking for the smallest val (True)
                        or largest (False).
        :returns: Either an id or Record object fitting the criteria.
        """
        sort_by = schema.ScalarData.value.asc() if get_min else schema.ScalarData.value.desc()
        query_set = (self.session.query(schema.ScalarData.id)
                     .filter(schema.ScalarData.name == scalar_name)
                     .order_by(sort_by).limit(count).all())
        ids = (x[0] for x in query_set)
        return ids if id_only else self.get(ids)

    def get_with_max(self, scalar_name, count=1, id_only=False):
        """
        Return the Record objects or ids associated with the highest values of <scalar_name>.

        Highest first, then second-highest, etc, until <count> records have been listed.
        This will only return records for plain scalars (not lists of scalars, strings, or
        list of strings).

        :param scalar_name: The name of the scalar to find the maximum record(s) for.
        :param count: How many to return.
        :param id_only: Whether to only return the id

        :returns: An iterator of the record objects or ids corresponding to the
                  <count> largest <scalar_name> values, ordered largest first.
        """
        return self._get_with_max_min_helper(scalar_name, count, id_only, get_min=False)

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
        return self._get_with_max_min_helper(scalar_name, count, id_only, get_min=True)

    def get_data_for_records(self, data_list, id_list=None):
        """
        Retrieve a subset of data for Records (or optionally a subset of Records).

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

        :param data_list: A list of the names of data fields to find
        :param id_list: A list of the record ids to find data for, None if
                        all Records should be considered.

        :returns: a dictionary of dictionaries containing the requested data,
                 keyed by record_id and then data field name.
        """
        if id_list is not None:
            id_list = list(id_list)  # Generator safety
        LOGGER.debug('Getting data in %s for %s',
                     data_list,
                     'record ids in {}'.format(id_list) if id_list is not None else "all records")
        data = defaultdict(lambda: defaultdict(dict))
        query_tables = [schema.ScalarData, schema.StringData]
        for query_table in query_tables:
            query = (self.session.query(query_table.id,
                                        query_table.name,
                                        query_table.value,
                                        query_table.units,
                                        query_table.tags)
                     .filter(query_table.name.in_(data_list)))
            if id_list is not None:
                query = query.filter(query_table.id.in_(id_list))
            for result in query:
                datapoint = {"value": result.value}
                if result.units:
                    datapoint["units"] = result.units
                if result.tags:
                    # Convert from string to ks
                    datapoint["tags"] = _json_loads(result.tags)
                data[result.id][result.name] = datapoint
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

        :return: A dict of scalars matching the Sina data specification
        """
        LOGGER.warning("Using deprecated method get_scalars()."
                       "Consider using Record.data instead.")
        # Not a strict subset of get_data_for_records() in that this will
        # never return stringdata
        LOGGER.debug('Getting scalars=%s for record id=%s', scalar_names, id)
        scalars = {}
        query = (self.session.query(schema.ScalarData.name, schema.ScalarData.value,
                                    schema.ScalarData.units, schema.ScalarData.tags)
                 .filter(schema.ScalarData.id == id)
                 .filter(schema.ScalarData.name.in_(scalar_names))
                 .order_by(schema.ScalarData.name.asc()).all())
        for entry in query:
            # SQL doesn't handle maps. so tags are stored as JSON lists.
            # This converts them to Python.
            tags = _json_loads(entry[3]) if entry[3] else None
            scalars[entry[0]] = {'value': entry[1],
                                 'units': entry[2],
                                 'tags': tags}
        return scalars

    def get_with_mime_type(self, mimetype, ids_only=False, id_pool=None):
        """
        Return all records or IDs with documents of a given mimetype.

        :param mimetype: The mimetype to use as a search term
        :param ids_only: Whether to only return the ids
        :param id_pool: Used when combining queries: a pool of ids to restrict
                        the query to. Only records with ids in this pool can be
                        returned.

        :returns: Record object or IDs fitting the criteria.
        """
        query_set = (self.session.query(schema.Document.id)
                     .filter(schema.Document.mimetype == mimetype))
        if id_pool is not None:
            query_set = query_set.filter(schema.Document.id.in_(id_pool))
        ids = (x[0] for x in query_set)
        return ids if ids_only else self.get(ids)


class RelationshipDAO(dao.RelationshipDAO):
    """The DAO responsible for handling Relationships in SQL."""

    def __init__(self, session):
        """Initialize RelationshipDAO with session for its SQL database."""
        self.session = session

    @_commit_or_rollback
    def insert(self, relationships=None, subject_id=None, object_id=None,
               predicate=None):
        """
        Given some Relationship(s), import it/them into a SQL database.

        This can create an entry from either an existing relationship object
        or from its components (subject id, object id, predicate). If all
        are provided, the Relationship will be used. If inserting many
        Relationships, a list of Relationships MUST be provided (no
        other fields). If any field besides Relationships is provided, it's
        assumed that only one Relationship is being inserted.

        :param relationships: A Relationship object to build entry from or an iterable of them.
        :param subject_id: The id of the subject.
        :param object_id: The id of the object.
        :param predicate: A string describing the relationship between subject and object.
        """
        self._insert_no_commit(relationships, subject_id, object_id, predicate)

    def _insert_no_commit(self, relationships=None, subject_id=None, object_id=None,
                          predicate=None):
        """Insert without committing; for shared functionality."""
        if (isinstance(relationships, model.Relationship)
                or any(x is not None for x in (subject_id, object_id, predicate))):
            subj, obj, pred = self._validate_insert(relationship=relationships,
                                                    subject_id=subject_id, object_id=object_id,
                                                    predicate=predicate)
            self.session.add(schema.Relationship(subject_id=subj,
                                                 object_id=obj,
                                                 predicate=pred))
        else:
            for rel in relationships:
                self.session.add(schema.Relationship(subject_id=rel.subject_id,
                                                     object_id=rel.object_id,
                                                     predicate=rel.predicate))

    # Note that get() is implemented by its parent.
    def get(self, subject_id=None, object_id=None, predicate=None):
        """Retrieve relationships fitting some criteria."""
        LOGGER.debug('Getting relationships with subject_id=%s, '
                     'predicate=%s, object_id=%s.',
                     subject_id, predicate, object_id)

        query = self._get_matching_relationships(subject_id, object_id, predicate)
        return self._build_relationships(query.all())

    def _get_matching_relationships(self, subject_id=None, object_id=None, predicate=None):
        """
        Do the actual retrieval of relationships fitting some criteria.

        Helper method for get() and _do_delete().
        """
        query = self.session.query(schema.Relationship)
        if subject_id:
            query = query.filter(schema.Relationship.subject_id == subject_id)
        if object_id:
            query = query.filter(schema.Relationship.object_id == object_id)
        if predicate:
            query = query.filter(schema.Relationship.predicate == predicate)
        return query

    @_commit_or_rollback
    def _do_delete(self, subject_id=None, object_id=None, predicate=None):
        """
        Given one or more criteria, delete all matching Relationships from the DAO's backend.

        This does not affect records, data, etc. Only Relationships.

        :raise ValueError: if no criteria are specified.
        """
        query = self._get_matching_relationships(subject_id, object_id, predicate)
        query.delete(synchronize_session='fetch')


class DAOFactory(dao.DAOFactory):
    """
    Build SQL-backed DAOs for interacting with Sina-based objects.

    Includes Records, Relationships, etc.
    """

    def __init__(self, db_path=None, allow_connection_pooling=False):
        """
        Initialize a Factory with a path to its backend.

        :param db_path: Path to the database to use as a backend. If None, will
                        use an in-memory database. If it contains a '://', it is assumed that
                        this is a URL which can be used to connect to the database. Otherwise,
                        this is treated as a path for a SQLite database.
        :param allow_connection_pooling: Allow pooling behavior for connections. Not
                                         recommended when using large numbers of DAOs (as from
                                         many nodes accessing one database) to prevent
                                         "zombie" connections that don't close when .close()d.
                                         Ignored for in-memory dbs (db_path=None).
        """
        self.db_path = db_path
        if db_path and db_path != ":memory:":
            if '://' not in db_path:
                connection_string = SQLITE_PREFIX + db_path
                create_db = not os.path.exists(db_path)
                use_sqlite = True
            else:
                connection_string = db_path
                create_db = True
                use_sqlite = False
            if allow_connection_pooling:
                engine = sqlalchemy.create_engine(connection_string)
            else:
                engine = sqlalchemy.create_engine(connection_string,
                                                  poolclass=NullPool)
        else:
            engine = sqlalchemy.create_engine(SQLITE_PREFIX)
            use_sqlite = True
            create_db = True

        if use_sqlite:
            def configure_on_connect(connection, _):
                """Activate foreign key support on connection creation."""
                connection.execute('pragma foreign_keys=ON')

            sqlalchemy.event.listen(engine, 'connect',
                                    configure_on_connect)

        if create_db:
            schema.Base.metadata.create_all(engine)

        session = sqlalchemy.orm.sessionmaker(bind=engine)
        self.session = session()

    def create_record_dao(self):
        """
        Create a DAO for interacting with records.

        :returns: a RecordDAO
        """
        return RecordDAO(session=self.session)

    def create_relationship_dao(self):
        """
        Create a DAO for interacting with relationships.

        :returns: a RelationshipDAO
        """
        return RelationshipDAO(session=self.session)

    def __repr__(self):
        """Return a string representation of a SQL DAOFactory."""
        return 'SQL DAOFactory <db_path={}>'.format(self.db_path)

    def close(self):
        """Close the session for this factory and all created DAOs."""
        self.session.close()


def _json_loads(data_from_db):
    """
    Load json from the given data.

    Because of all the different types that can be returned as, a series
    of checks is done to ensure we pass is to the json library in the
    right format.

    :param data_from_db: the data as a string. Could be a buffer object.
    :returns: the data as json
    """
    return json.loads(_to_json_string(data_from_db))


def _to_json_string(data_from_db):
    """
    Convert the given data from the database to a string. This is needed to
    handle all the different types that can be returned as from the database
    where we would expect a string.

    :param data_from_db: the data from the database
    :returns: the data as a string
    """
    # NOTE: When we stop supporting python2 and ujson, we may be able
    # to get rid of all this
    if isinstance(data_from_db, bytes):
        return data_from_db.decode()
    elif not isinstance(data_from_db, six.string_types):
        return six.text_type(data_from_db)
    return data_from_db
