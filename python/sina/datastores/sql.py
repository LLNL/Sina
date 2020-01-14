"""Contains SQL-specific implementations of our DAOs."""
import os
import numbers
import logging
import json
from collections import defaultdict
from functools import reduce   # pylint: disable=redefined-builtin

import six

# Disable pylint check due to its issue with virtual environments
import sqlalchemy  # pylint: disable=import-error

import sina.dao as dao
import sina.model as model
import sina.datastores.sql_schema as schema
from sina.utils import sort_and_standardize_criteria
from sina import utils

# Disable redefined-builtin, invalid-name due to ubiquitous use of id
# pylint: disable=invalid-name,redefined-builtin

LOGGER = logging.getLogger(__name__)

# String used to identify a sqlite database for SQLALchemy
SQLITE_PREFIX = "sqlite:///"

# Parameter offsets used when combining queries across tables
# see _apply_ranges_to_query() for usage
PARAM_OFFSETS = {schema.ScalarData: "",
                 schema.StringData: "_1",
                 schema.ListScalarData: "_2",
                 schema.ListStringDataEntry: "_3"}


class RecordDAO(dao.RecordDAO):
    """The DAO specifically responsible for handling Records in SQL."""

    def __init__(self, session):
        """Initialize RecordDAO with session for its SQL database."""
        self.session = session

    def insert(self, records):
        """
        Given a(n iterable of) Record(s), insert into the current SQL database.

        :param records: Record or iterable of Records to insert
        """
        if isinstance(records, model.Record):
            records = [records]
        for record in records:
            LOGGER.debug('Inserting record %s into SQL.', record.id or record.local_id)
            sql_record = self.create_sql_record(record)
            self.session.add(sql_record)
        self.session.commit()

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
                # If we've been given an empty list or a list of numbers:
                if not datum or isinstance(datum['value'][0], numbers.Real):
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

    def delete(self, ids):
        """
        Given a(n iterable of) Record id(s), delete all mention from the SQL database.

        This includes removing all data, raw(s), relationships, etc.
        Because the id is a foreign key in every table
        (besides Record itself but including Run, etc), we can rely on
        cascading to propogate the deletion.

        :param ids: The id or iterable of ids of the Record(s) to delete.
        """
        if isinstance(ids, six.string_types):
            ids = [ids]
        LOGGER.debug('Deleting records with ids in: %s', ids)
        (self.session.query(schema.Record)
         .filter(schema.Record.id.in_(ids))
         .delete(synchronize_session='fetch'))
        self.session.commit()

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
                            a criterion it does not support
        """
        LOGGER.debug('Finding all records fulfilling criteria: %s', kwargs.items())
        # No kwargs is bad usage. Bad kwargs are caught in sort_criteria().
        if not kwargs.items():
            raise ValueError("You must supply at least one criterion.")
        (scalar_criteria,
         string_criteria,
         scalarlist_criteria,
         stringlist_criteria) = sort_and_standardize_criteria(kwargs)
        result_ids = []

        # First handle scalar and string criteria
        for criteria, table in ((scalar_criteria, schema.ScalarData),
                                (string_criteria, schema.StringData)):
            if criteria:
                query = self.session.query(table.id)
                query = self._apply_ranges_to_query(query,
                                                    criteria,
                                                    table)
                result_ids.append(str(x[0]) for x in query.all())

        # Move on to any list criteria
        result_ids += [self._string_list_query(datum_name=datum_name,
                                               string_list=list_criteria.value,
                                               operation=list_criteria.operation)
                       for datum_name, list_criteria in stringlist_criteria]
        result_ids += [self._scalar_list_query(datum_name=datum_name,
                                               data_range=list_criteria.value,
                                               operation=list_criteria.operation)
                       for datum_name, list_criteria in scalarlist_criteria]

        # If we have more than one set of data, we need to find the intersection.
        for id in utils.intersect_lists(result_ids):
            yield id

    def _get_one(self, id, _record_builder):
        """
        Apply some "get" function to a single Record id.

        Used by the parent get(), this is the SQL-specific implementation of
        getting a single Record.

        :param id: A Record id to return
        :param _record_builder: The function used to create a Record object
                                (or one of its children) from the raw.

        :returns: A Record object
        """
        result = (self.session.query(schema.Record)
                  .filter(schema.Record.id == id).one_or_none())
        if result is None:
            raise ValueError("No Record found with id {}".format(id))
        return _record_builder(json_input=json.loads(result.raw))

    def get_all_of_type(self, type, ids_only=False):
        """
        Given a type of record, return all Records of that type.

        :param type: The type of record to return, ex: run
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of Records of that type or (if ids_only) a
                  generator of their ids
        """
        LOGGER.debug('Getting all records of type %s.', type)
        query = (self.session.query(schema.Record.id)
                 .filter(schema.Record.type == type))
        if ids_only:
            for record_id in query.all():
                yield str(record_id[0])
        else:
            filtered_ids = (str(x[0]) for x in query.all())
            for record in self.get(filtered_ids):
                yield record

    def _scalar_list_query(self,
                           datum_name,
                           data_range,
                           operation):
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
        table = schema.ListScalarData
        query = self.session.query(table.id)
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

        record_ids = query.filter(*filters)
        for record_id in record_ids:
            yield record_id[0]

    # Disable the pylint check to if and until the team decides to refactor the method
    def _string_list_query(self,  # pylint: disable=too-many-branches
                           datum_name,
                           string_list,
                           operation):
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
        LOGGER.info('Finding Records where datum %s contains %s: %s', datum_name,
                    operation.value.split('_')[1], string_list)
        list_of_record_ids_sets = []
        list_of_record_ids_sets.extend(
            self._execute_string_list_query(datum_name=datum_name,
                                            list_of_contents=string_list))

        # This reduce "ands" together all the sets (one per criterion),
        # creating one set that adheres to all our individual criterion sets.
        if operation == utils.ListQueryOperation.HAS_ALL:
            record_ids = reduce((lambda x, y: x & y), list_of_record_ids_sets)
        elif operation == utils.ListQueryOperation.HAS_ANY:
            record_ids = set.union(*list_of_record_ids_sets)
        else:
            # This can only happen if there's an operation that accepts a list
            # of strings but is not supported by string_list_query.
            raise ValueError("Given an invalid operation for a string list query: {}"
                             .format(operation.value))
        for record_id in record_ids:
            yield record_id

    def _execute_string_list_query(self, datum_name, list_of_contents):
        """
        For each string list criterion, execute a query and add the set result to a list.

        :param datum_name: The name of the datum
        :param list_of_contents: All the values datum_name must contain. Can be
                                 single values ("egg", 12) or DataRanges.
        :returns: A list of sets of record ids, where each set is the result
                  set of one query with one criterion.
        """
        table = schema.ListStringDataEntry
        criteria_tuples = [(datum_name, x) for x in list_of_contents]
        list_of_record_ids_sets = []
        for criterion in criteria_tuples:
            scalar_list_query = self.session.query(table.id)
            records_list = self._apply_ranges_to_query(query=scalar_list_query,
                                                       table=table,
                                                       data=[criterion]).all()
            list_of_record_ids_sets.append(set(str(record_id[0])
                                               for record_id in records_list))
        return list_of_record_ids_sets

    def get_available_types(self):
        """
        Return a list of all the Record types in the database.

        :returns: A list of types present (ex: ["run", "experiment"])
        """
        results = self.session.query(schema.Record.type).distinct().all()
        return [entry[0] for entry in results]

    def get_given_document_uri(self, uri, accepted_ids_list=None, ids_only=False):
        """
        Return all records associated with documents whose uris match some arg.

        Supports the use of % as a wildcard character.

        :param uri: The uri to use as a search term, such as "foo.png"
        :param accepted_ids_list: A list of ids to restrict the search to.
                                  If not provided, all ids will be used.
        :param ids_only: whether to return only the ids of matching Records
                         (used for further filtering)

        :returns: A generator of matching records or (if ids_only) a
                  generator of their ids. Returns distinct items.
        """
        LOGGER.debug('Getting all records related to uri=%s.', uri)
        if accepted_ids_list:
            LOGGER.debug('Restricting to %i ids.', len(accepted_ids_list))
        # Note: Mixed results on whether SQLAlchemy's optimizer is smart enough
        # to have %-less LIKE operate on par with ==, hence this:
        if '%' in uri:
            query = (self.session.query(schema.Document.id)
                     .filter(schema.Document.uri.like(uri)).distinct())
        else:
            query = (self.session.query(schema.Document.id)
                     .filter(schema.Document.uri == uri).distinct())
        if accepted_ids_list is not None:
            query = query.filter(schema.Document
                                 .id.in_(accepted_ids_list))
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
        if count == 1:
            sort_by = sqlalchemy.func.min if get_min else sqlalchemy.func.max
            query_set = (self.session.query(schema.ScalarData.id, sort_by(schema.ScalarData.value))
                         .filter(schema.ScalarData.name == scalar_name)
                         .one())
            ids = [query_set[0]]
        else:
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

    def _apply_ranges_to_query(self, query, data, table):
        """
        Filter query object based on list of (name, criteria).

        This is only meant to be used in conjunction with data_query() and
        related. Criteria must be DataRanges.

        Uses parameter substitution to get around limitations of SQLAlchemy OR
        construct. Note that we still use AND logic; the "or" is used in
        conjunction with a count statement because each data entry is its own
        row, and we need to use AND across rows (and with respect to the record
        id).

        :param query: A SQLAlchemy query object
        :param data: A list of (name, criteria) pairs to apply to the query object
        :param table: The table to query against, either ScalarData,
            StringData, ListScalarData, or ListStringDataEntry.

        :returns: <query>, now filtering on <data>
        :raises ValueError: If given an invalid table.
        """
        LOGGER.debug('Filtering <query=%s> with <data=%s>.', query, data)
        if (table not in [schema.ScalarData,
                          schema.StringData,
                          schema.ListScalarData,
                          schema.ListStringDataEntry]):
            msg = 'Given invalid table to query: {}'.format(table)
            LOGGER.error(msg)
            raise ValueError(msg)

        search_args = {}
        range_components = []
        # Performing an intersection on two SQLAlchemy queries, as in data_query(),
        # causes their parameters to merge and overwrite any shared names.
        # Here, we guarantee our params will have unique names per table.
        offset = PARAM_OFFSETS[table]
        for index, (name, criteria) in enumerate(data):
            range_components.append((name, criteria, index))
            search_args["name{}{}".format(index, offset)] = name
            if not isinstance(criteria, utils.DataRange):
                search_args["eq{}{}".format(index, offset)] = criteria
            elif criteria.is_single_value():
                search_args["eq{}{}".format(index, offset)] = criteria.min
            else:
                search_args["min{}{}".format(index, offset)] = criteria.min
                search_args["max{}{}".format(index, offset)] = criteria.max
        query = query.filter(sqlalchemy
                             .or_(self._build_range_filter(name, criteria, table, index)
                                  for (name, criteria, index) in range_components))

        def _count_checker(is_list=False):
            """
            Check which count to use depending if we are checking a list.

            If we are checking the count of a list of values, then we know the
            list of criteria passed in is a list of one criterion. We check
            that one or more rows came back satisfying said criterion. If we
            are not a list, we must have equality between the length of the
            list of criteria and the number of rows returned. This is because
            only one row can come back if a criterion is satisified, so it is
            one to one.

            :param is_list: Whether or not we are checking a list of values.
            :returns: Query that correctly checks count(s) of criteria.
            """
            if is_list:
                text = "{} >= {}"
                components_length = 1
            else:
                text = "{} = {}"
                components_length = len(range_components)
            return (query.group_by(table.id)
                    .having(sqlalchemy.text(text
                                            .format(sqlalchemy.func.count(table.id),
                                                    components_length))))
        if (table == schema.ListStringDataEntry or
                table == schema.ListScalarData):
            query = _count_checker(is_list=True)
        else:
            query = _count_checker(is_list=False)
        query = query.params(search_args)
        return query

    @staticmethod
    def _build_range_filter(name, criteria, table, index=0):
        """
        Build a TextClause to filter a SQL query using range parameters.

        Helper method to _apply_scalar_ranges_to_query. Needed in order to use
        parameter substitution and circumvent some filter limitations.

        Example clause as raw SQL:

        WHERE ScalarData.name=:scalar_name0 AND ScalarData.value<right_num0

        :param name: The name of the value we apply the criteria to
        :param criteria: The criteria used to build the query.
        :param table: The table to query against, either ScalarData or
                      StringData
        :param index: optional offset of this criteria if using multiple
                      criteria. Used for building var names for
                      parameterization.

        :returns: a TextClause object for use in a SQLAlchemy statement

        :raises ValueError: if given a bad table to query against.
        """
        LOGGER.debug('Building TextClause filter for data "%s" with criteria'
                     '<%s> and index=%s.', name, criteria, index)
        offset = PARAM_OFFSETS[table]
        # SQLAlchemy's methods for substituting in table names are convoluted.
        # A much simpler, clearer method:
        if table == schema.ScalarData:
            tablename = "ScalarData"
        elif table == schema.StringData:
            tablename = "StringData"
        elif table == schema.ListScalarData:
            tablename = "ListScalarData"
        elif table == schema.ListStringDataEntry:
            tablename = "ListStringDataEntry"
        else:
            raise ValueError("Given a bad table for data query: {}".format(table))

        conditions = ["({table}.name IS :name{index}{offset} AND {table}.value"
                      .format(table=tablename, index=index, offset=offset)]
        if not isinstance(criteria, utils.DataRange):
            conditions.append(" = :eq{}{}".format(index, offset))
        elif criteria.is_single_value():
            conditions.append(" = :eq{}{}".format(index, offset))
        else:
            if criteria.min_is_finite():
                conditions.append(" >= " if criteria.min_inclusive else " > ")
                conditions.append(":min{}{}".format(index, offset))
            # If two-sided range, begin preparing new condition
            if (criteria.min_is_finite()) and (criteria.max_is_finite()):
                conditions.append(" AND {}.value ".format(tablename))
            if criteria.max_is_finite():
                conditions.append(" <= " if criteria.max_inclusive else " < ")
                conditions.append(":max{}{}".format(index, offset))
        # This helper method should NEVER see a (None, None) range due to the
        # special way they need handled (figuring out what table they belong to)
        conditions.append(")")
        return sqlalchemy.text(''.join(conditions))

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
                    datapoint["tags"] = json.loads(result.tags)
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

        :return: A dict of scalars matching the Mnoda data specification
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
            tags = json.loads(entry[3]) if entry[3] else None
            scalars[entry[0]] = {'value': entry[1],
                                 'units': entry[2],
                                 'tags': tags}
        return scalars


class RelationshipDAO(dao.RelationshipDAO):
    """The DAO responsible for handling Relationships in SQL."""

    def __init__(self, session):
        """Initialize RelationshipDAO with session for its SQL database."""
        self.session = session

    def insert(self, relationships=None, subject_id=None,
               object_id=None, predicate=None):
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
        self.session.commit()

    # Note that get() is implemented by its parent.
    def get(self, subject_id=None, object_id=None, predicate=None):
        """Retrieve relationships fitting some criteria."""
        LOGGER.debug('Getting relationships with subject_id=%s, '
                     'predicate=%s, object_id=%s.',
                     subject_id, predicate, object_id)
        query = self.session.query(schema.Relationship)
        if subject_id:
            query = query.filter(schema.Relationship.subject_id == subject_id)
        if object_id:
            query = query.filter(schema.Relationship.object_id == object_id)
        if predicate:
            query = query.filter(schema.Relationship.predicate == predicate)

        return self._build_relationships(query.all())


class RunDAO(dao.RunDAO):
    """DAO responsible for handling Runs (Record subtype) in SQL."""

    def __init__(self, session, record_dao):
        """Initialize RunDAO and assign a contained RecordDAO."""
        super(RunDAO, self).__init__(record_dao)
        self.session = session
        self.record_dao = record_dao

    def _return_only_run_ids(self, ids):
        """
        Given a(n iterable) of id(s) which might be any type of Record, clear out non-Runs.

        :param ids: An id or iterable of ids to sort through

        :returns: For each id, the id if it belongs to a Run, else None. Returns an iterable
                  if "ids" is an iterable, else returns a single value.
        """
        if isinstance(ids, six.string_types):
            val = self.session.query(schema.Run.id).filter(schema.Run.id == ids).one_or_none()
            return val[0] if val is not None else None
        ids = list(ids)
        query = self.session.query(schema.Run.id).filter(schema.Run.id.in_(ids)).all()
        run_ids = set(str(x[0]) for x in query)
        # We do this in order to fulfill the "id or None" requirement
        results = [x if x in run_ids else None for x in ids]
        return results

    def insert(self, runs):
        """
        Given a(n iterable of) Run(s), import into the SQL database.

        :param runs: A Run or iterator of Runs to import
        """
        if isinstance(runs, model.Run):
            runs = [runs]
        for run in runs:
            record = RecordDAO.create_sql_record(run)
            run = schema.Run(application=run.application, user=run.user,
                             version=run.version)
            run.record = record
            self.session.add(record)
            self.session.add(run)
        self.session.commit()

    def delete(self, ids):
        """
        Given (a) Run id(s), delete all mention from the SQL database.

        This includes removing all related data, raw(s), any relationships
        involving it/them, etc.

        :param ids: The id or iterator of ids of the Run to delete.
        """
        run_ids = self._return_only_run_ids(ids)
        if run_ids is None:  # We have nothing to do here
            return
        elif isinstance(run_ids, six.string_types):
            run_ids = [run_ids]
        else:
            run_ids = [id for id in run_ids if id is not None]
        self.record_dao.delete(ids)


class DAOFactory(dao.DAOFactory):
    """
    Build SQL-backed DAOs for interacting with Mnoda-based objects.

    Includes Records, Relationships, etc.
    """

    def __init__(self, db_path=None):
        """
        Initialize a Factory with a path to its backend.

        Currently supports only SQLite.

        :param db_path: Path to the database to use as a backend. If None, will
                        use an in-memory database. If it contains a '://', it is assumed that
                        this is a URL which can be used to connect to the database. Otherwise,
                        this is treated as a path for a SQLite database.
        """
        self.db_path = db_path
        use_sqlite = False
        if db_path:
            if '://' not in db_path:
                engine = sqlalchemy.create_engine(SQLITE_PREFIX + db_path)
                create_db = not os.path.exists(db_path)
                use_sqlite = True
            else:
                engine = sqlalchemy.create_engine(db_path)
                create_db = True
        else:
            engine = sqlalchemy.create_engine(SQLITE_PREFIX)
            use_sqlite = True
            create_db = True

        if use_sqlite:
            def configure_on_connect(connection, _):
                """Activate foreign key support on connection creation."""
                connection.execute('pragma foreign_keys=ON')

            sqlalchemy.event.listen(engine, 'connect', configure_on_connect)

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

    def create_run_dao(self):
        """
        Create a DAO for interacting with runs.

        :returns: a RunDAO
        """
        return RunDAO(session=self.session,
                      record_dao=self.create_record_dao())

    def __repr__(self):
        """Return a string representation of a SQL DAOFactory."""
        return 'SQL DAOFactory <db_path={}>'.format(self.db_path)
