"""Defines the DataStore, Sina's toplevel data interaction object."""
import sina.datastores.sql as sina_sql
try:
    import sina.datastores.cass as sina_cass
    HAS_CASSANDRA = True

except ImportError:
    # Not having Cassandra is a possibility. If someone tries to use Cassandra
    # without the dependencies, we raise a descriptive error.
    HAS_CASSANDRA = False


# TODO: Initial plan was to allow them to create from a DAOFactory. But maybe
# we hide the DAOFactory entirely and allow them to create from a Datastore.
# Same functionality, but no use of the words "DAO" and "Factory". Remember to
# change the func doc to suite!
def create_datastore(db_path=None, keyspace=None, backend=None):
    """
    Create a DataStore for handling some type of backend.

    Given a uri/path (and, if required, the name of a keyspace),
    figures out which backend is required. You can also provide it with an
    existing DAOFactory if you'd like to reuse a connection.

    :param db_path: The path/IP/URI/DAOFactory pointing to the database.
    :param keyspace: The keyspace at <uri> to connect to (Cassandra only).
    :param backend: Normally, the uri will be used to determine the
                    required backend. To override this behavior, provide
                    the desired backend here (case-insensitive, one of
                    "sql", or "cassandra"). Ignored if a DAOFactory is provided.
    """
    # If they've provided a DAOFactory, ignore backend
    if isinstance(db_path, sina_sql.DAOFactory):
        return DataStore(db_path)
    elif isinstance(db_path, sina_cass.DAOFactory):
        return DataStore(db_path)

    # Else determine a backend
    if backend is None:
        backend = "sql" if keyspace is None else "cassandra"
    elif backend == "sql":
        connection = sina_sql.DAOFactory(db_path)
    elif backend == "casandra":
        if HAS_CASSANDRA:
            connection = sina_cass.DAOFactory(db_path, keyspace)
        else:
            raise ImportError("A Cassandra backend cannot be accessed until "
                              "Cassandra dependencies are loaded into the "
                              "environment. See the README.")
    else:
        raise ValueError("Given unrecognized backend: {}".format(backend))
    return DataStore(connection)


class DataStore():
    """Mediates interactions between users and data."""

    def __init__(self, connection):
        """Define attributes needed by a datastore."""
        self.connection = connection
        self.records = self.RecordOperations(connection)
        self.relationships = self.RelationshipOperations(connection)

    def close(self):
        """Close any resources held by this datastore."""
        self.connection.close()

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

    class RecordOperations():
        """
        Defines the queries users can perform on Records.

        This should be considered the "source of truth" in terms of what Record
        operations are available to users and what each does.

        This doesn't handle implementation, helper methods, etc; it's for
        defining the user interface.
        """

        def __init__(self, connection):
            """Create object(s) we'll need for performing queries."""
            self.accessor = connection.create_record_dao()

        # -------------------- Basic operations ---------------------
        def get(self, ids_to_get):
            """
            Given one or more Record ids, return matching Record(s).

            :param ids_to_get: The id(s) of the Record(s) to return.

            :returns: If provided an iterable, a generator of Record objects,
                      else a single Record object.

            :raises ValueError: if no Record is found for some id.
            """
            return self.accessor.get(ids_to_get)

        def insert(self, records_to_insert):
            """
            Given one or more Records, insert them into the DAO's backend.

            :param records: A Record or iter of Records to insert
            """
            self.accessor.insert(records_to_insert)

        def delete(self, ids_to_delete):
            """
            Given one or more Record ids, delete all mention from the DAO's backend.

            This includes removing all data, raw(s), any relationships
            involving it/them, etc.

            :param ids_to_delete: A Record id or iterable of Record ids to delete.
            """
            return self.accessor.delete(ids_to_delete)

        # ------------------ Operations tied to Record type -------------------
        def get_by_type(self, type, ids_only=False):
            """
            Given a type of Record, return all Records of that type.

            :param type: The type of Record to return
            :param ids_only: whether to return only the ids of matching Records

            :returns: A generator of matching Records.
            """
            return self.accessor.get_all_of_type(type, ids_only)

        def get_types(self):
            """
            Return all types of Records available in the backend.

            :returns: A generator of types of Record.
            """
            return self.accessor.get_available_types()

        # ------------------ Operations tied to Record data -------------------
        def get_by_data(self, **kwargs):
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
            return self.accessor.data_query(**kwargs)

        def get_data(self, data_list, id_list=None):
            """
            Retrieve a subset of data for some or all Records.

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
            data, it will be omitted.

            :param data_list: A list of the names of data fields to find
            :param id_list: A list of the record ids to find data for, None if
                            all Records should be considered.

            :returns: a dictionary of dictionaries containing the requested
                      data, keyed by record_id and then data field name.
            """
            return self.accessor.get_data_for_records(data_list, id_list)

        def get_by_max(self, scalar_name, count=1, ids_only=False):
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
            return self.accessor.get_with_max(scalar_name, count, ids_only)

        def get_by_min(self, scalar_name, count=1, ids_only=False):
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
            return self.accessor.get_with_min(scalar_name, count, ids_only)

        # ------------------ Operations tied to Record files -------------------
        def get_by_file_uri(self, uri, accepted_ids_list=None, ids_only=False):
            """
            Return all records associated with files whose uris match some arg.

            Supports the use of % as a wildcard character. Note that you may or
            may not get duplicates depending on the backend; call set() to
            collapse the returned generator if required.

            :param uri: The uri to use as a search term, such as "foo.png"
            :param accepted_ids_list: A list of ids to restrict the search to.
                                      If not provided, all ids will be used.
            :param ids_only: whether to return only the ids of matching Records

            :returns: A generator of matching Records
            """
            return self.accessor.get_given_document_uri(uri, accepted_ids_list,
                                                        ids_only)

        # TODO: "mime type" here, but "mimetype" in the schema. Which to use?
        def get_by_file_mime_type(self, mime_type, ids_only=False):
            """
            Return all records or IDs with documents of a given mimetype.

            :param mimetype: The mimetype to use as a search term
            :param ids_only: Whether to only return the ids

            :returns: Record object or IDs fitting the criteria.
            """
            return self.accessor.get_with_mime_type(mime_type, ids_only)

    class RelationshipOperations():
        """
        Defines the queries users can perform on Relationships.

        This should be considered the "source of truth" in terms of what
        Relationship operations are available to users and what each does.

        This doesn't handle implementation, helper methods, etc; it's for
        defining the user interface.
        """

        def __init__(self, connection):
            """Create object(s) we'll need for performing queries."""
            self.accessor = connection.create_relationship_dao()

        def get(self, subject_id=None, predicate=None, object_id=None):
            """Return all relationships that fulfill one or more criteria."""
            return self.accessor.get(subject_id, predicate, object_id)

        def insert(self, relationships_to_insert):
            """
            Given one or more Relationships, insert them into a backend.

            :param relationships_to_insert: Relationships to insert
            """
            self.accessor.insert(relationships_to_insert)
