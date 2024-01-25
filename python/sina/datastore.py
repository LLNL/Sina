"""Defines the DataStore, Sina's toplevel data interaction object."""
from __future__ import print_function
import warnings

import six

import sina.datastores.sql as sina_sql
try:
    import sina.datastores.cass as sina_cass
    HAS_CASSANDRA = True

except ImportError:
    # Not having Cassandra is a possibility. If someone tries to use Cassandra
    # without the dependencies, we raise a descriptive error.
    HAS_CASSANDRA = False


def connect(database=None, keyspace=None, database_type=None,
            allow_connection_pooling=False, read_only=False):
    """
    Connect to a database.

    Given a uri/path (and, if required, the name of a keyspace),
    figures out which backend is required.

    :param database: The URI of the database to connect to. If empty, an
     in-memory sqlite3 database will be used.
    :param keyspace: The keyspace to connect to (Cassandra only).
    :param database_type: Type of backend to connect to. If not provided, Sina
                          will infer this from <database>. One of "sql" or
                          "cassandra".
    :param allow_connection_pooling: Allow "pooling" behavior that recycles connections,
                                     which may prevent them from closing fully on .close().
                                     Only used for the sql backend.
    :param read_only: whether to create a read-only store
    :return: a DataStore object connected to the specified database
    """
    # Determine a backend
    if database_type is None:
        database_type = "sql" if keyspace is None else "cassandra"
    if database_type == "sql":
        connection = sina_sql.DAOFactory(database, allow_connection_pooling)
    elif database_type == "cassandra":
        if HAS_CASSANDRA:
            if keyspace:
                connection = sina_cass.DAOFactory(node_ip_list=database,
                                                  keyspace=keyspace)
            else:
                raise ValueError("A keyspace must be provided to use Cassandra")
        else:
            raise ImportError("A Cassandra backend cannot be accessed until "
                              "Cassandra dependencies are loaded into the "
                              "environment. See the README.")
    else:
        raise ValueError("Given unrecognized database type: {}".format(database_type))
    if read_only:
        return ReadOnlyDataStore(connection)
    return DataStore(connection)


def create_datastore(database=None, keyspace=None, database_type=None,
                     allow_connection_pooling=False):
    """
    Create a DataStore for handling some type of backend.

    Given a uri/path (and, if required, the name of a keyspace),
    figures out which backend is required.

    .. deprecated:: 1.10
        Use :func:`connect` instead.

    :param database: The URI of the database to connect to.
    :param keyspace: The keyspace to connect to (Cassandra only).
    :param database_type: Type of backend to connect to. If not provided, Sina
                          will infer this from <database>. One of "sql" or
                          "cassandra".
    :param allow_connection_pooling: Allow "pooling" behavior that recycles connections,
                                     which may prevent them from closing fully on .close().
                                     Only used for the sql backend.
    :return: a DataStore object connected to the specified database
    """
    warnings.warn('This function is deprecated. Use connect() instead.',
                  DeprecationWarning)
    return connect(database=database, keyspace=keyspace,
                   database_type=database_type,
                   allow_connection_pooling=allow_connection_pooling)


class ReadOnlyDataStore(object):
    """
    Mediates interactions between users and data, providing read-only
    capabilities.

    DataStore and ReadOnlyDataStore grant access to a selection of operations
    for both Records and Relationships. They're used like this:

        ds = connect(path_to_my_database)
        my_runs = ds.records.find_with_type("runs")
        submission_rels = ds.relationships.get(predicate="submitted")

    Note the use of connect() in place of manually creating a DataStore
    object. For information on all the operations available, see
    RecordOperations and RelationshipOperations below.
    """

    def __init__(self, dao_factory):
        """
        Define attributes needed by a datastore.

        Generally connect() is preferred.

        :param dao_factory: The DAOFactory that will provide the backend
                            connection.
        """
        self._dao_factory = dao_factory
        # DAOs are created at this level to support DataStore operations that
        # affect both records AND relationships.
        self._record_dao = dao_factory.create_record_dao()
        self._relationship_dao = dao_factory.create_relationship_dao()
        self.records = self.RecordOperations(self._record_dao)
        self.relationships = self.RelationshipOperations(self._relationship_dao)

    @property
    def read_only(self):
        """Whether this is a read-only datastore."""
        return True

    def close(self):
        """Close any resources held by this datastore."""
        self._dao_factory.close()

    def __enter__(self):
        """Use the datastore as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close the datastore's resources.

        Be careful! This will close the connection for anyone sharing it.
        Any Datastores created from the same DAOFactory share the same
        connection.
        """
        return self.close()

    class RecordOperations(object):
        """
        Defines the queries users can perform on Records.

        This should be considered the "source of truth" in terms of what Record
        operations are available to users and what each does.

        This doesn't handle implementation, helper methods, etc; it's for
        defining the user interface.
        """

        def __init__(self, record_dao):
            """
            Create or assign object(s) we'll need for performing queries.

            :param record_dao: the owning DataStore's RecordDAO
            """
            self._record_dao = record_dao

        # -------------------- Basic operations ---------------------
        def get(self, ids_to_get, chunk_size=999):
            """
            Given one or more Record ids, return matching Record(s).

            :param ids_to_get: The id(s) of the Record(s) to return.
            :param chunk_size: Size of chunks to pull records in.

            :returns: If provided an iterable, a generator of Record objects,
                      else a single Record object.

            :raises ValueError: if no Record is found for some id.
            """
            return self._record_dao.get(ids_to_get, chunk_size=chunk_size)

        # Sphinx has an issue with trailing-underscore params, we need to escape it for the doc
        # pylint: disable=anomalous-backslash-in-string
        def get_raw(self, id_):
            """
            Get the raw content of the record identified by the given ID.

            This can be used in cases where the json is somehow corrupted
            and cannot be used to create a via the get() call. This is not
            intended to be used for other purposes.

            :param id\_: the ID of the record
            :return: the raw JSON for the specified record
            :raises: ValueError if the record does not exist
            """
            return self._record_dao.get_raw(id_)

        def exist(self, ids_to_check):
            """
            Given an (iterable of) id(s), return boolean list of whether those
            records exist or not.

            :param ids_to_check: The id(s) of the Record(s) to test.

            :returns: If provided an iterable, a generator of bools pertaining to
                      the ids existence, else a single boolean value.
            """
            return self._record_dao.exist(ids_to_check)

        def get_all(self, ids_only=False):
            """
            Return all Records.

            :param ids_only: whether to return only the ids of matching Records

            :returns: A generator of all Records.
            """
            return self._record_dao.get_all(ids_only)

        # High arg count is inherent to the functionality.
        # pylint: disable=too-many-arguments
        def find(self, types=None, data=None, file_uri=None, mimetype=None,
                 id_pool=None, ids_only=False,
                 query_order=("data", "file_uri", "mimetype", "types")):
            """
            Return Records that match multiple different types of criteria.

            A convenience method, this allows you to combine Sina's different types
            of queries into a single call. Using the method with only one of the criteria
            args is equivalent to using that dedicated query method. Using more performs
            an "AND" operation: returned Records must fulfill ALL criteria.

            :param types: Functionality of find_with_type, an iterable of types of Records
                          (e.g. "msub", "test", "run") to return.
            :param data: Functionality of find_with_data, dictionary of {<name>:<criteria>} entries
                         a Record's data must fulfill
            :param file_uri: Functionality of find_with_file_uri, a uri criterion (optionally with
                             wildcards) a Record's files must fulfill, ex: having at least one .png
            :param mimetype: Functionality of find_with_file_mimetype, a mimetype criterion at
                             least one of a Record's files must fulfill, ex: having a mimetype
                             of mimetype "image/png"
            :param id_pool: A pool of IDs to restrict the query to. Only a Record whose id is in
                            this pool can be returned
            :param ids_only: Whether to return only the ids of the matching Records
            :param query_order: The order in which to perform the queries. Advanced usage,
                                the default should be fine for many cases. To optimize
                                performance, order queries in ascending order of expected
                                number of matches (ex: if your database has very few Records
                                with the desired type(s), you may wish to put "type" first).
                                Query names are "types", "file_uri", "mimetype", and "data".
                                Note that if any query name is absent from the passed tuple,
                                that query will not be executed.
            """
            # We protect _find to disincentize users using the DAO directly.
            # pylint: disable=protected-access
            return self._record_dao._find(types, data, file_uri, mimetype, id_pool,
                                          ids_only, query_order)

        # ------------------ Operations tied to Record type -------------------
        def find_with_type(self, types, ids_only=False, id_pool=None):
            """
            Given a(n iterable of) type(s) of Record, return all Records of that type(s).

            :param types: A(n iterable of) types of Records to filter on. Can be negated with
                          not_() to return Records not of those types.
            :param ids_only: whether to return only the ids of matching Records
            :param id_pool: Used when combining queries: a pool of ids to restrict
                            the query to. Only records with ids in this pool can be
                            returned.

            :returns: A generator of matching Records.
            """
            return self._record_dao.get_all_of_type(types, ids_only, id_pool)

        find_with_types = find_with_type

        def get_types(self):
            """
            Return all types of Records available in the backend.

            :returns: A generator of types of Record.
            """
            return self._record_dao.get_available_types()

        def get_curve_set_names(self):
            """
            Return the names of all curve sets available in the backend.

            :returns: An iterable of curve set names.
            """
            return self._record_dao.get_curve_set_names()

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
            return self._record_dao.data_names(record_type, data_types, filter_constants)

        # ------------------ Operations tied to Record data -------------------
        def find_with_data(self, **kwargs):
            """
            Return the ids of Records whose data fulfill some criteria.

            Criteria are expressed as keyword arguments. Each keyword
            is the name of an entry in a Record's data field, and it's set
            equal to a single value, a DataRange (see utils.DataRanges), or a
            special criteria (ex: has_all(), see utils) that expresses the
            desired value/range of values. All criteria must be satisfied for
            an ID to be returned:

                # Return ids of all Records with a volume of 12, a quadrant of
                # "NW", AND a height >=30 and <40.
                data_query(volume=12, quadrant="NW", height=DataRange(30,40))

            :param kwargs: Pairs of the names of data and the criteria that data
                             must fulfill.
            :returns: A generator of Record ids that fulfill all criteria.

            :raises ValueError: if not supplied at least one criterion or given
                                a criterion it does not support
            """
            return self._record_dao.data_query(**kwargs)

        def get_data(self, data_list, id_list=None):
            """
            Retrieve a subset of non-list data for some or all Records.

            For example, it might get "debugger_version" and "volume" for the
            Records with ids "foo_1" and "foo_3". Requested data is returned as
            a dictionary of dictionaries; the outer key is the record_id, the
            inner key is the name of the datum (ex: "volume"). So::

                {"foo_1": {"volume": {"value": 12, "units": cm^3},
                           "debugger_version": {"value": "alpha"}}
                 "foo_3": {"debugger_version": {"value": "alpha"}}

            As seen in foo_3 above, if a piece of data is missing, it won't be
            included; think of this as a subset of a Record's own data.
            Similarly, if a Record ends up containing none of the requested
            data, or if the data exists but it's a list of strings or scalars,
            it will be omitted.

            The absence of list data may be addressed in the future if there's
            demand for it.

            :param data_list: A list of the names of data fields to find
            :param id_list: A list of the record ids to find data for, None if
                            all Records should be considered.

            :returns: a dictionary of dictionaries containing the requested
                      data, keyed by record_id and then data field name.
            """
            return self._record_dao.get_data_for_records(data_list, id_list)

        def find_with_max(self, scalar_name, count=1, ids_only=False):
            """
            Return the Records/id(s) with the highest value(s) for <scalar_name>.

            The first Record or id returned has the highest value, then
            second-highest, etc, until <count> records have been listed.
            This will only return records for plain scalars (not lists of
            scalars, strings, or list of strings).

            :param scalar_name: The scalar to find the maximum record(s) for.
            :param count: How many to return.
            :param ids_only: Whether to only return the id

            :returns: An iterator of the Records or ids corresponding to the
                      <count> highest <scalar_name> values in descending order.
            """
            return self._record_dao.get_with_max(scalar_name, count, ids_only)

        def find_with_min(self, scalar_name, count=1, ids_only=False):
            """
            Return the Records/id(s) with the lowest value(s) for <scalar_name>.

            The first Record or id returned has the lowest value, then
            second-lowest, etc, until <count> records have been listed.
            This will only return records for plain scalars (not lists of
            scalars, strings, or list of strings).

            :param scalar_name: The scalar to find the minimum record(s) for.
            :param count: How many to return.
            :param ids_only: Whether to only return the id

            :returns: An iterator of the Records or ids corresponding to the
                      <count> lowest <scalar_name> values in ascending order.
            """
            return self._record_dao.get_with_min(scalar_name, count, ids_only)

        # ------------------ Operations tied to Record files -------------------
        def find_with_file_uri(self, uri, ids_only=False, id_pool=None):
            """
            Given a uri criterion, return Records with files whose uris match.

            The simplest case for <criterion> is to provide a string (possibly including
            one or more wildcards, see below). You may also use Sina's has_any
            or has_all constructs, ex find_with_file_uris(uri=has_any("%.png", "%.jpg"))

            Supports the use of % as a wildcard character. Note that you may or
            may not get duplicates depending on the backend; call set() to
            collapse the returned generator if required.

            :param uri: A uri or criterion describing what to match. Either a string,
                        a has_all, or a has_any.
            :param ids_only: whether to return only the ids of matching Records
            :param id_pool: Used when combining queries: a pool of ids to restrict
                            the query to. Only records with ids in this pool can be
                            returned.

            :returns: A generator of matching Records.
            """
            return self._record_dao.get_given_document_uri(uri=uri,
                                                           accepted_ids_list=id_pool,
                                                           ids_only=ids_only)

        def find_with_file_mimetype(self, mimetype, ids_only=False):
            """
            Return all records or IDs with documents of a given mimetype.

            :param mimetype: The mimetype to use as a search term
            :param ids_only: Whether to only return the ids

            :returns: Record object or IDs fitting the criteria.
            """
            # It's "mimetype" in the schema, but the method is named
            # mime_type. We follow the schema above for consistency.
            return self._record_dao.get_with_mime_type(mimetype, ids_only)

    class RelationshipOperations(object):  # pylint: disable=too-few-public-methods
        """
        Defines the queries users can perform on Relationships.

        This should be considered the "source of truth" in terms of what
        Relationship operations are available to users and what each does.

        This doesn't handle implementation, helper methods, etc; it's for
        defining the user interface.
        """

        def __init__(self, relationship_dao):
            """
            Create or assign object(s) we'll need for performing queries.

            :param relationship_dao: the owning DataStore's RelationshipDAO
            """
            self._relationship_dao = relationship_dao

        def find(self, subject_id=None, predicate=None, object_id=None):
            """
            Return all relationships that fulfill one or more criteria.

            Note that the arg order here was "naturalized" to be in the order that people
            would read this in an English sentence ("Carmen helps Danny"); this differs
            from the older dao equivalent (get()).
            """
            return self._relationship_dao.get(subject_id=subject_id,
                                              predicate=predicate,
                                              object_id=object_id)


class DataStore(ReadOnlyDataStore):  # pylint: disable=too-few-public-methods
    """
    Mediates interactions between users and data.

    Adds operations that modify the data store to ReadOnlyDataStore.

    DataStore and ReadOnlyDataStore grant access to a selection of operations
    for both Records and Relationships. They're used like this:

        ds = connect(path_to_my_database)
        my_runs = ds.records.find_with_type("runs")
        submission_rels = ds.relationships.get(predicate="submitted")

    Note the use of connect() in place of manually creating a DataStore
    object. For information on all the operations available, see
    RecordOperations and RelationshipOperations below.
    """

    @property
    def read_only(self):
        """Whether this is a read-only datastore."""
        return False

    # The DAO version is protected to disincentivize using it from the DAOs.
    # pylint: disable=protected-access
    def delete_all_contents(self, force=""):
        """
        Delete EVERYTHING in a datastore; this cannot be undone.

        :param force: This function is meant to raise a confirmation prompt. If you
                      want to use it in an automated script (and you're sure of
                      what you're doing), set this to "SKIP PROMPT".
        :returns: whether the deletion happened.
        """
        confirm_phrase = "DELETE ALL DATA"
        if force == "SKIP PROMPT":
            # Record deletes propagate to Relationships. That currently covers all info
            # in a datastore.
            self._record_dao._do_delete_all_records()
            return True
        warning = ("WARNING: You're about to delete all data in your current "
                   "datastore. This cannot be undone! If you're sure you want to "
                   "delete all data, enter the phrase {}: ").format(confirm_phrase)
        response = six.moves.input(warning)
        if response == confirm_phrase:
            self._record_dao._do_delete_all_records()
            print('The database has been purged of all contents.')
            return True
        print('Response was "{}", not "{}". Deletion aborted.'.format(response, confirm_phrase))
        return False

    class RecordOperations(ReadOnlyDataStore.RecordOperations):
        """
        Defines the queries users can perform on Records.

        This should be considered the "source of truth" in terms of what Record
        operations are available to users and what each does.

        This doesn't handle implementation, helper methods, etc; it's for
        defining the user interface.
        """

        # -------------------- Basic operations ---------------------
        def insert(self, records_to_insert, ingest_funcs=None,
                   ingest_funcs_preserve_raw=None):
            """
            Given one or more Records, insert them into the DAO's backend.

            :param records_to_insert: A Record or iter of Records to insert
            :param ingest_funcs: A function or list of functions to
                                 run against each record before insertion.
                                 See the postprocessing module for a few
                                 you can use! They will be run in list order.
            :param ingest_funcs_preserve_raw: Whether the postprocessing is allowed
                                              to touch the underlying json on ingest.
                                              This may break parity with files on the
                                              filesystem, but is needed if you want
                                              to use filter_keep/etc. to make smaller
                                              records. MUST BE SPECIFIED if you want
                                              to use the ingest_funcs.
            """
            self._record_dao.insert(records_to_insert, ingest_funcs,
                                    ingest_funcs_preserve_raw)

        def update(self, records_to_update):
            """
            Given one or more Records, update them in the DAO's backend.

            :param records_to_update: A Record or iter of Records to update
            """
            self._record_dao.update(records_to_update)

        def delete(self, ids_to_delete):
            """
            Given one or more Record ids, delete all mention from the DAO's backend.

            This includes removing all data, raw(s), any relationships
            involving it/them, etc.

            :param ids_to_delete: A Record id or iterable of Record ids to delete.
            """
            return self._record_dao.delete(ids_to_delete)

    class RelationshipOperations(ReadOnlyDataStore.RelationshipOperations):
        """
        Defines the queries users can perform on Relationships.

        This should be considered the "source of truth" in terms of what
        Relationship operations are available to users and what each does.

        This doesn't handle implementation, helper methods, etc; it's for
        defining the user interface.
        """

        def insert(self, relationships_to_insert):
            """
            Given one or more Relationships, insert them into a backend.

            :param relationships_to_insert: Relationships to insert
            """
            self._relationship_dao.insert(relationships_to_insert)

        def delete(self, subject_id=None, predicate=None, object_id=None):
            """
            Given one or more criteria, delete all matching Relationships from the DAO's backend.

            This does not affect records, data, etc. Only Relationships.

            Note that the arg order here was "naturalized" to be in the order that people
            would read this in an English sentence ("Carmen helps Danny"), same as
            find(); this differs from the dao delete()'s order, which matches the
            older dao.get().

            :raise ValueError: if no criteria are specified.
            """
            self._relationship_dao.delete(subject_id=subject_id,
                                          predicate=predicate,
                                          object_id=object_id)
