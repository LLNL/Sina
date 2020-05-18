"""Contains SQL-specific implementations of our DAOs."""
import os
import numbers
import logging
import json
import warnings
from collections import defaultdict

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

# Identify the tables that store Record.data entries.
DATA_TABLES = [schema.ScalarData, schema.StringData,
               schema.ListScalarData, schema.ListStringDataEntry]


class DataHandler(dao.DataHandler):
    """
    Sets up connection and mediates interaction with Sina-based objects.

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

    def __repr__(self):
        """Return a string representation of a SQL DAOFactory."""
        return 'SQL DAOFactory <db_path={}>'.format(self.db_path)

    def close(self):
        """Close the session for this factory and all created DAOs."""
        self.session.close()

    def insert_record(self, records):
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
            DataHandler._attach_data(sql_record, sina_record.data)
        if sina_record.files:
            DataHandler._attach_files(sql_record, sina_record.files)

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
         scalar_list_criteria,
         string_list_criteria,
         universal_criteria) = sort_and_standardize_criteria(kwargs)
        result_ids = []

        # First handle scalar and string criteria
        for criteria, table in ((scalar_criteria, schema.ScalarData),
                                (string_criteria, schema.StringData)):
            if criteria:
                query = self._generate_data_table_query(criteria, table)
                result_ids.append(str(x[0]) for x in query.all())

        # Move on to any list criteria
        result_ids += [self._string_list_query(datum_name=datum_name,
                                               string_list=list_criteria.value,
                                               operation=list_criteria.operation)
                       for datum_name, list_criteria in string_list_criteria]
        result_ids += [self._scalar_list_query(datum_name=datum_name,
                                               data_range=list_criteria.value,
                                               operation=list_criteria.operation)
                       for datum_name, list_criteria in scalar_list_criteria]

        # Now any universal criteria.
        if universal_criteria:
            result_ids.append(self._universal_query(universal_criteria))

        # If we have more than one set of data, we need to find the intersection.
        for rec_id in utils.intersect_lists(result_ids):
            yield rec_id

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
        query = self.session.query(table.id).filter(table.name == datum_name)
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

    def _string_list_query(self, datum_name, string_list, operation):
        """
        Return all Records where [datum_name] fulfills [operation] for [string_list].

        Helper method for data_query.

        :param datum_name: The name of the datum
        :param string_list: A list of strings datum_name must contain.
        :param operation: What kind of ListQueryOperation to do.
        :returns: A generator of ids of matching Records or the Records
                  themselves (see ids_only).

        :raises ValueError: if given an invalid operation for a string list
        """
        LOGGER.info('Finding Records where datum %s contains %s: %s', datum_name,
                    operation.value.split('_')[1], string_list)
        criteria_tuples = [(datum_name, x) for x in string_list]
        if operation == utils.ListQueryOperation.HAS_ALL:
            query = self._generate_data_table_query(table=schema.ListStringDataEntry,
                                                    criteria_pairs=criteria_tuples)
        elif operation == utils.ListQueryOperation.HAS_ANY:
            query = self._generate_data_table_query(table=schema.ListStringDataEntry,
                                                    criteria_pairs=criteria_tuples,
                                                    fulfill_all=False)
        else:
            # This can only happen if there's an operation that accepts a list
            # of strings but is not supported by string_list_query.
            raise ValueError("Given an invalid operation for a string list query: {}"
                             .format(operation.value))
        for query_result in query:
            yield query_result[0]  # yield the id

    @staticmethod
    def _generate_criterion_filters(criterion_pair, table):
        """
        Generate the AND expression fulfilling a single criterion pair.

        :param criterion_pair: A tuple of (datum_name, criterion). Criterion must be a DataRange
                               or single value, ex: 6, "low_frequency"
        :param table: The table the datum is expected to exist in
        :return: A SQLAlchemy AND expression fulfilling the criterion pair
        """
        datum_name, criterion = criterion_pair
        range_criteria = [table.name == datum_name]
        if isinstance(criterion, utils.DataRange):
            if not criterion.is_single_value():
                if criterion.min:
                    min_op = table.value.__ge__ if criterion.min_inclusive else table.value.__gt__
                    range_criteria.append(min_op(criterion.min))
                if criterion.max:
                    max_op = table.value.__le__ if criterion.max_inclusive else table.value.__lt__
                    range_criteria.append(max_op(criterion.max))
            else:
                range_criteria.append(table.value.__eq__(criterion.min))
        else:
            range_criteria.append(table.value.__eq__(criterion))
        return sqlalchemy.and_(*range_criteria)

    def _generate_data_table_query(self, criteria_pairs, table, fulfill_all=True):
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

        :return: A query object representing <criterion> applied to <datum_name> in <table>.
        """
        query = self.session.query(table.id)
        criteria_queries = [self._generate_criterion_filters(pair, table)
                            for pair in criteria_pairs]

        if not fulfill_all:
            return query.filter(sqlalchemy.or_(*criteria_queries))

        # Since we don't know the possible data names a priori, we have a row per datum
        # and have to "or" them together and then group by record ID, selecting the records
        # that have a matching row for each queried criterion (# rows == # criteria).
        query = query.filter(sqlalchemy.or_(*criteria_queries))

        # For performance reasons, we skip the "group by" stage when not needed
        if len(criteria_pairs) > 1:
            query = (query.group_by(table.id)
                     .having(sqlalchemy.func.count(table.id) == len(criteria_pairs)))
        return query

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

    def _universal_query(self, universal_criteria):
        """
        Pull back all record ids fulfilling universal criteria.

        We do all criteria in a single query per table, as there's only one
        possible universal query right now.

        :param universal_criteria: List of tuples: (datum_name, UniversalCriteria)
        :return: generator of ids of Records fulfilling all criteria.
        """
        result_counts = defaultdict(lambda: 0)
        desired_names = [x[0] for x in universal_criteria]
        LOGGER.info('Finding Records where data in %s exist', desired_names)
        expected_result_count = len(universal_criteria)
        for query_table in DATA_TABLES:
            # We know that a single Record can never have more than one datum with
            # a given name, so all we need to get is count.
            query = (self.session.query(query_table.id, sqlalchemy.func.count(query_table.name))
                     .filter(query_table.name.in_(desired_names))
                     .group_by(query_table.id))
            for result in query:
                result_counts[result[0]] += result[1]  # Add the number of found names
        for entry, val in six.iteritems(result_counts):
            if val == expected_result_count:
                yield entry

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
            tags = json.loads(entry[3]) if entry[3] else None
            scalars[entry[0]] = {'value': entry[1],
                                 'units': entry[2],
                                 'tags': tags}
        return scalars

    def get_with_mime_type(self, mimetype, ids_only=False):
        """
        Return all records or IDs with documents of a given mimetype.

        :param mimetype: The mimetype to use as a search term
        :param ids_only: Whether to only return the ids

        :returns: Record object or IDs fitting the criteria.
        """
        query_set = (self.session.query(schema.Document.id)
                     .filter(schema.Document.mimetype == mimetype))
        ids = (x[0] for x in query_set)
        return ids if ids_only else self.get(ids)

    def insert_relationship(self, relationships=None, subject_id=None,
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
    def get_relationship(self, subject_id=None, object_id=None, predicate=None):
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


class DAOFactory(dao.DAOFactory):
    """
    A fake DAOFactory for backwards compatibility.

    Most implementation is provided by sina.dao.
    """

    def __init__(self, db_path=None):
        """Create the actual workhorse, the DataHandler."""
        warnings.warn("DAOFactories are deprecated; use DataHandler.",
                      DeprecationWarning)
        self.db_path = db_path
        self.datahandler = DataHandler(db_path)
        self.session = self.datahandler.session
