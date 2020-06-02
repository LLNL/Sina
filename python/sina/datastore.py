"""Defines the DataStore, Sina's toplevel data interaction object."""
from abc import ABCMeta, abstractmethod

import six

import sina.datastores.sql as sina_sql
try:
    import sina.datastores.cass as sina_cass
    HAS_CASSANDRA = True

except ImportError:
    # Not having Cassandra is a possibility. If someone tries to use Cassandra
    # without the dependencies, we raise a descriptive error in the DataStore.
    HAS_CASSANDRA = False

import sina.model
import sina.dao


def create_datastore(db_path=None, keyspace=None, backend=None):
    """
    Create a DataStore for handling some type of backend.

    Given a uri/path (and, if required, the name of a keyspace),
    figures out which backend is required. You can also provide it with an
    existing DAOFactory.

    :param db_path: The path/IP/URI/DAOFactory pointing to the database.
    :param keyspace: The keyspace at <uri> to connect to (Cassandra only).
    :param backend: Normally, the uri will be used to determine the
                    required backend. To override this behavior, provide
                    the desired backend here (case-insensitive, one of
                    "sql", or "cassandra")
    """
    if backend is None:
        if isinstance(db_path, sina_sql.DAOFactory):
            backend = "sql"
        elif isinstance(db_path, sina_cass.DAOFactory):
            backend = "cassandra"
        else:
            backend = "sql" if keyspace is None else "cassandra"
    if backend == "sql":
        return SQLDataStore(db_path)
    elif backend == "cassandra":
        return CassandraDataStore(db_path, keyspace)
    else:
        raise ValueError("Given unrecognized backend: {}".format(backend))


@six.add_metaclass(ABCMeta)
class DataStore(sina.dao.RecordDAO, sina.dao.RelationshipDAO):
    """Defines the basic implementation of DataStore classes."""

    @abstractmethod
    def __init__(self, db_path=None):
        """Define attributes needed by a datastore."""
        self.factory = None
        raise NotImplementedError

    @abstractmethod  # override with proper parent
    def insert_records(self, records_to_insert):
        """Wrap record insertion for explicit use."""
        raise NotImplementedError

    @abstractmethod  # override with proper parent
    def insert_relationships(self, relationships_to_insert):
        """Wrap relationship insertion for explicit use."""
        raise NotImplementedError

    @abstractmethod  # override with proper parent
    def get_records(self, records_to_get):
        """Wrap getting records for explicit use."""
        raise NotImplementedError

    @abstractmethod  # override with proper parent
    def get_relationships(self, subject_id=None, predicate=None,
                          object_id=None):
        """Wrap getting relationships for explicit use."""
        raise NotImplementedError

    # Unifies functionality of DAOs, Pylint is not aware
    # pylint: disable=arguments-differ
    @classmethod
    def get(cls, _):
        """Wrap getting relationships for explicit use."""
        raise AttributeError("get() is ambiguous for DataStore and is not "
                             "implemented. Use either get_record() or "
                             "get_relationship, or see the DAO objects.")

    # Unifies functionality of DAOs, Pylint is not aware
    # pylint: disable=arguments-differ
    def insert(self, objects_to_insert):
        """
        Given one or more Sina objects, insert them into the DAO's backend.

        :param objects_to_insert: Some Sina object(s) (Records, Relationships)
                                  to insert
        """
        if isinstance(objects_to_insert, sina.model.Record):
            self.insert_records(objects_to_insert)
        elif isinstance(objects_to_insert, sina.model.Relationship):
            self.insert_relationships(objects_to_insert)
        else:
            records = []
            relationships = []
            for sina_object in objects_to_insert:
                if isinstance(sina_object, sina.model.Record):
                    records.append(sina_object)
                else:
                    relationships.append(sina_object)
            self.insert_records(records)
            self.insert_relationships(relationships)

    def close(self):
        """Close any resources held by this datastore."""
        self.factory.close()

    def __enter__(self):
        """Use the datastore as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the datastore's resources."""
        return self.factory.close()


if HAS_CASSANDRA:
    class CassandraDataStore(DataStore, sina_cass.RecordDAO,
                             sina_cass.RelationshipDAO):
        """Builds DAOs used for interacting with the Sina Cassandra backend."""

        def __init__(self, db_path=None, keyspace=None):
            """Perform initializations for accessing Cassandra data."""
            # Pylint expects abstract super init to be called.
            # pylint: disable=super-init-not-called
            if isinstance(db_path, sina_cass.DAOFactory):
                self.factory = db_path
            else:
                self.factory = sina_cass.DAOFactory(db_path, keyspace)

        def insert_records(self, records_to_insert):
            """Wrap record insertion for explicit use."""
            return sina_cass.RecordDAO.insert(self, records_to_insert)

        def insert_relationships(self, relationships_to_insert):
            """Wrap relationship insertion for explicit use."""
            return sina_cass.RelationshipDAO.insert(self,
                                                    relationships_to_insert)

        def get_records(self, records_to_get):
            """Wrap getting records for explicit use."""
            return sina_cass.RecordDAO.get(self, records_to_get)

        def get_relationships(self, subject_id=None, predicate=None,
                              object_id=None):
            """Wrap getting relationships for explicit use."""
            return sina_cass.RelationshipDAO.get(self, subject_id=subject_id,
                                                 predicate=predicate,
                                                 object_id=object_id)
else:
    class CassandraDataStore(object):
        """An error-throwing dummy in case Cassandra's unavailable."""

        # Dummy class is not expected to have public methods
        # pylint: disable=too-few-public-methods
        def __init__(self):
            """Raise a descriptive error and exit."""
            raise ImportError("A CassandraDataStore cannot be created until "
                              "Cassandra dependencies are loaded into the "
                              "environment. See the README.")


class SQLDataStore(DataStore, sina_sql.RecordDAO, sina_sql.RelationshipDAO):
    """Builds DAOs used for interacting with the Sina SQL backend."""

    def __init__(self, db_path=None):
        """Perform initializations for accessing SQL data."""
        # Pylint expects abstract super init to be called.
        # pylint: disable=super-init-not-called
        if isinstance(db_path, sina_sql.DAOFactory):
            self.factory = db_path
        else:
            self.factory = sina_sql.DAOFactory(db_path)
        self.session = self.factory.session

    def insert_records(self, records_to_insert):
        """Wrap record insertion for explicit use."""
        return sina_sql.RecordDAO.insert(self, records_to_insert)

    def insert_relationships(self, relationships_to_insert):
        """Wrap relationship insertion for explicit use."""
        return sina_sql.RelationshipDAO.insert(self, relationships_to_insert)

    def get_records(self, records_to_get):
        """Wrap getting records for explicit use."""
        return sina_sql.RecordDAO.get(self, records_to_get)

    def get_relationships(self, subject_id=None, predicate=None, object_id=None):
        """Wrap getting relationships for explicit use."""
        return sina_sql.RelationshipDAO.get(self, subject_id=subject_id,
                                            predicate=predicate,
                                            object_id=object_id)
