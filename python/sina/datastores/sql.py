"""Contains SQL-specific implementations of our DAOs."""
import os
import numbers
import logging
import sqlalchemy
import json
from collections import defaultdict
import six
from functools import reduce

import sina.dao as dao
import sina.model as model
import sina.datastores.sql_schema as schema
from sina.utils import sort_and_standardize_criteria
from sina import utils

LOGGER = logging.getLogger(__name__)

# String used to identify a sqlite database for SQLALchemy
SQLITE = "sqlite:///"

# Parameter offsets used when combining queries across tables
# see _apply_ranges_to_query() for usage
param_offsets = {schema.ScalarData: "",
                 schema.StringData: "_1",
                 schema.ListScalarDataEntry: "_2",
                 schema.ListStringDataEntry: "_3"}


class RecordDAO(dao.RecordDAO):
    """The DAO specifically responsible for handling Records in SQL."""

    def __init__(self, session):
        """Initialize RecordDAO with session for its SQL database."""
        self.session = session

    def insert(self, record, called_from_child=False):
        """
        Given a Record, insert it into the current SQL database.

        :param record: A Record to insert
        :param called_from_child: Whether a child of Record (such as Run) is
                                  calling this. Used to skip committing in
                                  order to preserve atomicity.
        """
        LOGGER.debug('Inserting {} into SQL.'.format(record))
        is_valid, warnings = record.is_valid()
        if not is_valid:
            raise ValueError(warnings)
        self.session.add(schema.Record(id=record.id,
                                       type=record.type,
                                       raw=json.dumps(record.raw)))
        if record.data:
            self._insert_data(record.id, record.data)
        if record.files:
            self._insert_files(record.id, record.files)

        # If called from child, child is responsible for committing.
        if not called_from_child:
            self.session.commit()

    def _insert_data(self, id, data):
        """
        Insert data entries into the ScalarData and StringData tables.

        Does not commit(), caller needs to do that.

        :param id: The Record ID to associate the data to.
        :param data: The dictionary of data to insert.
        """
        LOGGER.debug('Inserting {} data entries to Record ID {}.'
                     .format(len(data), id))
        for datum_name, datum in data.items():
            if isinstance(datum['value'], list):
                # Store info such as units and tags in master table
                # Note: SQL doesn't support maps, so we have to convert the
                # tags to a string (if they exist).
                # Using json.dumps() instead of str() (or join()) gives
                # valid JSON
                tags = (json.dumps(datum['tags']) if 'tags' in datum

                                                     else None)
                # Check if empty list
                if datum:
                    kind_master = (schema.ListScalarDataMaster
                                   if isinstance(datum['value'][0],
                                                 numbers.Real)
                                   else schema.ListStringDataMaster)
                else:
                    # Default to Scalar table
                    kind_master = schema.ListScalarDataMaster
                self.session.add(kind_master(id=id,
                                             name=datum_name,
                                             # units might be None, always use
                                             # get()
                                             units=datum.get('units'),
                                             tags=tags))

                # Store list entries in entry table
                for index, entry in enumerate(datum['value']):
                    # Check if it's a scalar
                    kind = (schema.ListScalarDataEntry
                            if isinstance(entry, numbers.Real)
                            else schema.ListStringDataEntry)
                    self.session.add(kind(id=id,
                                          name=datum_name,
                                          index=index,
                                          value=entry))
            elif (isinstance(datum['value'], six.string_types) or
                  isinstance(datum['value'], numbers.Number)):
                tags = (json.dumps(datum['tags']) if 'tags' in datum
                                                     else None)
                # Check if it's a scalar
                kind = (schema.ScalarData if isinstance(datum['value'],
                                                        numbers.Real)
                        else schema.StringData)
                self.session.add(kind(id=id,
                                      name=datum_name,
                                      value=datum['value'],
                                      # units might be None, always use get()
                                      units=datum.get('units'),
                                      tags=tags))

    def _insert_files(self, id, files):
        """
        Insert files into the Document table.

        Does not commit(), caller needs to do that.

        :param id: The Record ID to associate the files to.
        :param files: The list of files to insert.
        """
        LOGGER.debug('Inserting {} files to record id={}.'
                     .format(len(files), id))
        for entry in files:
            tags = (json.dumps(entry['tags']) if 'tags' in entry else None)
            self.session.add(schema.Document(id=id,
                                             uri=entry['uri'],
                                             mimetype=entry.get('mimetype'),
                                             tags=tags))

    def delete(self, id):
        """
        Given the id of a Record, delete all mention of it from the SQL database.

        This includes removing all its data, its raw, any relationships
        involving it, etc. Because the id is a foreign key in every table
        (besides Record itself but including Run, etc), we can rely on
        cascading to propogate the deletion.

        :param id: The id of the Record to delete.
        """
        LOGGER.debug('Deleting record with id: {}'.format(id))
        self.session.query(schema.Record).filter(schema.Record.id == id).delete()
        self.session.commit()

    def delete_many(self, ids_to_delete):
        """
        Given a list of Record ids, delete all mentions of them from the SQL database.

        :param ids_to_delete: A list of the ids of Records to delete.
        """
        LOGGER.debug('Deleting records with ids in: {}'.format(ids_to_delete))
        (self.session.query(schema.Record).filter(schema.Record.id.in_(ids_to_delete))
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
        LOGGER.debug('Finding all records fulfilling criteria: {}'
                     .format(kwargs.items()))
        # No kwargs is bad usage. Bad kwargs are caught in sort_criteria().
        if not kwargs.items():
            raise ValueError("You must supply at least one criterion.")
        (scalar_criteria,
         string_criteria,
         scalarlist,
         stringlist) = sort_and_standardize_criteria(kwargs)
        result_ids = []

        if scalar_criteria:
            scalar_query = self.session.query(schema.ScalarData.id)
            scalar_query = self._apply_ranges_to_query(scalar_query,
                                                       scalar_criteria,
                                                       schema.ScalarData)
        if string_criteria:
            string_query = self.session.query(schema.StringData.id)
            string_query = self._apply_ranges_to_query(string_query,
                                                       string_criteria,
                                                       schema.StringData)
        #  If we have more than one set of data, we need to perform a union
        if scalar_criteria and string_criteria:
            and_query = scalar_query.intersect(string_query)
            result_ids.append(str(x[0]) for x in and_query.all())
        # Otherwise, just find which one has something to return
        elif scalar_criteria:
            result_ids.append(str(x[0]) for x in scalar_query.all())
        elif string_criteria:
            result_ids.append(str(x[0]) for x in string_query.all())
        for criteria, table_type in ((scalarlist, "scalarlist"),
                                     (stringlist, "stringlist")):
            for criterion in criteria:
                # Unpack the criterion
                datum_name, list_criteria = criterion
                # has_all queries are broken up and treated like a scalar or string
                if (list_criteria.operation in
                    [utils.ListQueryOperation.ALL,
                     utils.ListQueryOperation.ANY,
                     utils.ListQueryOperation.ONLY]):
                    ids = self.get_list(datum_name=datum_name,
                                        list_of_contents=list_criteria.entries,
                                        ids_only=True,
                                        operation=list_criteria.operation)
                    result_ids.append(ids)
                else:
                    raise ValueError("Currently, only [{}, {}, {}] list "
                                     "operations are supported. Given {}"
                                     .format(utils.ListQueryOperation.ALL,
                                             utils.ListQueryOperation.ANY,
                                             utils.ListQueryOperation.ONLY,
                                             list_criteria.operation))
        # If we have more than one set of data, we need to find the intersect.
        if len(result_ids) > 1:
            valid_ids = set(result_ids[0])
            for entry in result_ids[1:]:
                valid_ids = valid_ids.intersection(entry)
            for id in valid_ids:
                yield id
        else:
            for id in result_ids[0]:
                yield id

    def get(self, id):
        """
        Given a id, return match (if any) from SQL database.

        :param id: The id of the Record to return

        :returns: A Record matching id or None
        """
        LOGGER.debug('Getting record with id={}'.format(id))
        query = (self.session.query(schema.Record)
                 .filter(schema.Record.id == id).one())
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
        query = (self.session.query(schema.Record.id)
                             .filter(schema.Record.type == type))
        if ids_only:
            for x in query.all():
                yield str(x[0])
        else:
            filtered_ids = (str(x[0]) for x in query.all())
            for record in self.get_many(filtered_ids):
                yield record

    def get_list(self,
                 datum_name,
                 list_of_contents,
                 operation,
                 ids_only=False):
        """
        Given a list datum's name and values, return Records where the datum contains those values.

        As an example, given "pizza_toppings", ["pineapple", "cheese"], and the
        operation of ListQueryOperation.ALL, this method would return Records
        where "pizza_toppings" is ["pineapple", "cheese"] or
        ["pineapple", "cheese", "pepperoni"], but not just ["cheese"].

        Note that if datum_name isn't found, no record_ids will be found, so be
        sure datum_name is the name of a list-type datum (timeseries, etc).

        :param datum_name: The name of the datum
        :param list_of_contents: All the values datum_name must contain. Can be
                                 single values ("egg", 12) or DataRanges.
        :pram operation: What kind of ListQueryOperation to do.
        :param ids_only: Whether to only return ids rather than full Records.
        :returns: A generator of ids of matching Records or the Records
                  themselves (see ids_only).
        :raises ValueError: if given an empty list_of_contents
        :raises TypeError: if given a list that isn't all strings xor scalars.
        """
        LOGGER.info('Finding Records where datum {} contains {}: {}'
                    .format(datum_name,
                            operation.value.split('.')[0],
                            list_of_contents))
        if not list_of_contents:
            raise ValueError("Must supply at least one entry in "
                             "list_of_contents for {}".format(datum_name))

        list_of_record_ids_sets = []

        if all(isinstance(x, numbers.Real) or
               (isinstance(x, utils.DataRange) and x.is_numeric_range())
               for x in list_of_contents):
            numeric = True
            list_of_record_ids_sets.extend(
                self._list_query(table=schema.ListScalarDataEntry,
                                 datum_name=datum_name,
                                 list_of_contents=list_of_contents))
        elif all(isinstance(x, six.string_types) or
                 (isinstance(x, utils.DataRange) and x.is_lexographic_range())
                 for x in list_of_contents):
            numeric = False
            list_of_record_ids_sets.extend(
                self._list_query(table=schema.ListStringDataEntry,
                                 datum_name=datum_name,
                                 list_of_contents=list_of_contents))
        else:
            raise TypeError("list_of_contents must be only strings or only scalars")
        # This reduce "ands" together all the sets (one per criterion),
        # creating one set that adheres to all our individual criterion sets.
        if operation == utils.ListQueryOperation.ALL:
            record_ids = reduce((lambda x, y: x & y), list_of_record_ids_sets)
        elif operation == utils.ListQueryOperation.ANY:
            record_ids = set.union(*list_of_record_ids_sets)
        elif operation == utils.ListQueryOperation.ONLY:
            record_ids = reduce((lambda x, y: x & y), list_of_record_ids_sets)
            ranges = [x if isinstance(x, utils.DataRange)
                      else utils.DataRange(x, x, max_inclusive=True)
                      for x in list_of_contents]
            if numeric:
                excluded_ids = self._list_query(table=schema.ListScalarDataEntry,
                                                datum_name=datum_name,
                                                list_of_contents=utils.invert_ranges(ranges))
            else:
                excluded_ids = self._list_query(table=schema.ListStringDataEntry,
                                                datum_name=datum_name,
                                                list_of_contents=utils.invert_ranges(ranges))
            for set_ids in excluded_ids:
                for id_ in set_ids:
                    if id_ in record_ids:
                        record_ids.remove(id_)
        if ids_only:
            for record_id in record_ids:
                yield record_id
        else:
            for record in self.get_many(record_ids):
                yield record

    def _list_query(self, table, datum_name, list_of_contents):
        """
        For each criterion, execute a query and add the set result to a list.

        :param table: Which table to query on: ListScalarDataEntry or
                      ListStringDataEntry.
        :param datum_name: The name of the datum
        :param list_of_contents: All the values datum_name must contain. Can be
                                 single values ("egg", 12) or DataRanges.
        :returns: A list of sets of record ids, where each set is the result
                  set of one query with one criterion.
        """
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
        LOGGER.debug('Getting all records related to uri={}.'.format(uri))
        if accepted_ids_list:
            LOGGER.debug('Restricting to {} ids.'.format(len(accepted_ids_list)))
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
            for x in query.all():
                yield x[0]
        else:
            filtered_ids = (x[0] for x in query.all())
            for record in self.get_many(filtered_ids):
                yield record

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
            StringData, ListScalarDataEntry, or ListStringDataEntry.

        :returns: <query>, now filtering on <data>
        :raises ValueError: If given an invalid table.
        """
        LOGGER.debug('Filtering <query={}> with <data={}>.'.format(query, data))
        if (table not in [schema.ScalarData,
                          schema.StringData,
                          schema.ListScalarDataEntry,
                          schema.ListStringDataEntry]):
            msg = 'Given invalid table to query: {}'.format(table)
            LOGGER.error(msg)
            raise ValueError(msg)

        search_args = {}
        range_components = []
        # Performing an intersection on two SQLAlchemy queries, as in data_query(),
        # causes their parameters to merge and overwrite any shared names.
        # Here, we guarantee our params will have unique names per table.
        offset = param_offsets[table]
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
                table == schema.ListScalarDataEntry):
            query = _count_checker(is_list=True)
        else:
            query = _count_checker(is_list=False)
        query = query.params(search_args)
        return query

    def _build_range_filter(self, name, criteria, table, index=0):
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
        LOGGER.debug('Building TextClause filter for data "{}" with criteria'
                     '<{}> and index={}.'
                     .format(name, criteria, index))
        offset = param_offsets[table]
        # SQLAlchemy's methods for substituting in table names are convoluted.
        # A much simpler, clearer method:
        if table == schema.ScalarData:
            tablename = "ScalarData"
        elif table == schema.StringData:
            tablename = "StringData"
        elif table == schema.ListScalarDataEntry:
            tablename = "ListScalarDataEntry"
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

    def get_data_for_records(self, id_list, data_list):
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

        :returns: a dictionary of dictionaries containing the requested data,
                 keyed by record_id and then data field name.
        """
        LOGGER.debug('Getting data in {} for record ids in {}'
                     .format(data_list, id_list))
        data = defaultdict(lambda: defaultdict(dict))
        query_tables = [schema.ScalarData, schema.StringData]
        for query_table in query_tables:
            query = (self.session.query(query_table.id,
                                        query_table.name,
                                        query_table.value,
                                        query_table.units,
                                        query_table.tags)
                     .filter(query_table.id.in_(id_list))
                     .filter(query_table.name.in_(data_list)))
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
        # Not a strict subset of get_data_for_records() in that this will
        # never return stringdata
        LOGGER.debug('Getting scalars={} for record id={}'
                     .format(scalar_names, id))
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

    def get_files(self, id):
        """
        Retrieve files for a given record id.

        Files are returned in the alphabetical order of their URIs

        :param id: The record id to find files for
        :return: A list of file JSON objects matching the Mnoda specification
        """
        LOGGER.debug('Getting files for record id={}'.format(id))
        query = (self.session.query(schema.Document.uri, schema.Document.mimetype,
                                    schema.Document.tags)
                             .filter(schema.Document.id == id)
                             .order_by(schema.Document.uri.asc()).all())
        files = []
        for entry in query:
            tags = json.loads(entry[2]) if entry[2] else None
            files.append({'uri': entry[0], 'mimetype': entry[1], 'tags': tags})
        return files


class RelationshipDAO(dao.RelationshipDAO):
    """The DAO responsible for handling Relationships in SQL."""

    def __init__(self, session):
        """Initialize RelationshipDAO with session for its SQL database."""
        self.session = session

    def insert(self, relationship=None, subject_id=None,
               object_id=None, predicate=None):
        """
        Given some Relationship, import it into the SQL database.

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
        self.session.add(schema.Relationship(subject_id=subject_id,
                                             object_id=object_id,
                                             predicate=predicate))
        self.session.commit()

    # Note that get() is implemented by its parent.

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
        query = (self.session.query(schema.Relationship)
                 .filter(schema.Relationship.subject_id == subject_id))
        if predicate:
            query.filter(schema.Relationship.predicate == predicate)

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
        query = (self.session.query(schema.Relationship)
                 .filter(schema.Relationship.object_id == object_id))
        if predicate:
            query.filter(schema.Relationship.predicate == predicate)

        return self._build_relationships(query.all())

    def _get_given_predicate(self, predicate):
        """
        Given predicate, return all Relationships with that predicate.

        :param predicate: The predicate describing Relationships to return

        :returns: A list of Relationships fitting the criteria
        """
        LOGGER.debug('Getting relationships related to predicate={}.'
                     .format(predicate))
        query = (self.session.query(schema.Relationship)
                 .filter(schema.Relationship.predicate == predicate))

        return self._build_relationships(query.all())

    def _build_relationships(self, query):
        """
        Given query results, build a list of Relationships.

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
    """DAO responsible for handling Runs, (Record subtype), in SQL."""

    def __init__(self, session, recordDAO):
        """Initialize RunDAO and assign a contained RecordDAO."""
        super(RunDAO, self).__init__(recordDAO)
        self.session = session
        self.record_DAO = recordDAO

    def insert(self, run):
        """
        Given a Run, import it into the current SQL database.

        :param run: A Run to import
        """
        self.record_DAO.insert(run, called_from_child=True)
        self.session.add(schema.Run(id=run.id,
                                    application=run.application,
                                    user=run.user,
                                    version=run.version))
        self.session.commit()

    def get(self, id):
        """
        Given a run's id, return match (if any) from the SQL database.

        :param id: The id of some run

        :returns: A run matching that identifier or None
        """
        LOGGER.debug('Getting run with id: {}'.format(id))
        record = (self.session.query(schema.Record)
                  .filter(schema.Record.id == id).one())
        return model.generate_run_from_json(json.loads(record.raw))

    def delete(self, id):
        """
        Given the id of a Run, delete all mention of it from the SQL database.

        This includes removing all its data, its raw, any relationships
        involving it, etc.

        :param id: The id of the Run to delete.
        """
        self.record_DAO.delete(id)

    def delete_many(self, ids_to_delete):
        """
        Given a list of Run ids, delete all mentions of them from the SQL database.

        :param ids_to_delete: A list of the ids of Runs to delete.
        """
        self.record_DAO.delete_many(ids_to_delete)

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
            return model.generate_run_from_json(json_input=record.raw)
        else:
            msg = ('Record must be of subtype Run to convert to Run. Given '
                   '{}.'.format(record.id))
            LOGGER.warn(msg)
            raise ValueError(msg)


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
                        use an in-memory database.
        """
        self.db_path = db_path
        if db_path:
            engine = sqlalchemy.create_engine(SQLITE + db_path)
            if not os.path.exists(db_path):
                schema.Base.metadata.create_all(engine)
        else:
            engine = sqlalchemy.create_engine('sqlite:///')
            schema.Base.metadata.create_all(engine)

        def configure_on_connect(connection, _):
            """Activate foreign key support on connection creation."""
            connection.execute('pragma foreign_keys=ON')

        sqlalchemy.event.listen(engine, 'connect', configure_on_connect)
        session = sqlalchemy.orm.sessionmaker(bind=engine)
        self.session = session()

    def createRecordDAO(self):
        """
        Create a DAO for interacting with records.

        :returns: a RecordDAO
        """
        return RecordDAO(session=self.session)

    def createRelationshipDAO(self):
        """
        Create a DAO for interacting with relationships.

        :returns: a RelationshipDAO
        """
        return RelationshipDAO(session=self.session)

    def createRunDAO(self):
        """
        Create a DAO for interacting with runs.

        :returns: a RunDAO
        """
        return RunDAO(session=self.session,
                      recordDAO=self.createRecordDAO())

    def __repr__(self):
        """Return a string representation of a SQL DAOFactory."""
        return 'SQL DAOFactory <db_path={}>'.format(self.db_path)
