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

# Observations:
# One thing I'm starting to worry about for the ds.records_* naming convention
# is the implication of plural as part of all the names. If we had
# records.get instead of get_records, it's much clearer that the get() works
# for one or more, not just "more".

# A weakness of the ds.records.data / ds.records.files naming is that it
# feels like it implies *returning*, rather than *querying on*, data/files.
# I'm going to stop with those names for now.


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
        factory = sina_sql.DAOFactory(db_path)
    elif backend == "cassandra":
        factory = sina_cass.DAOFactory(db_path, keyspace)
    else:
        raise ValueError("Given unrecognized backend: {}".format(backend))
    return DataStore(factory)


class DataStore():
    """Defines the basic implementation of DataStore classes."""

    def __init__(self, connection):
        """Define attributes needed by a datastore."""
        self.connection = None
        self.records = connection.create_record_dao()
        self.relationships = connection.create_relationship_dao()

    def close(self):
        """Close any resources held by this datastore."""
        self.factory.close()

    def __enter__(self):
        """Use the datastore as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the datastore's resources."""
        return self.factory.close()

    def insert_records(self, records_to_insert):
        """Wrap record insertion for explicit use."""
        # records.insert
        self.records.insert(records_to_insert)

    def insert_relationships(self, relationships_to_insert):
        """Wrap relationship insertion for explicit use."""
        # relationships.insert
        self.relationships.insert(relationships_to_insert)

    def get_records(self, records_to_get):
        """Wrap getting records for explicit use."""
        # records.get
        return self.records.get(records_to_get)

    def get_relationships(self, subject_id=None, predicate=None,
                          object_id=None):
        """Wrap getting relationships for explicit use."""
        # relationships.get
        return self.relationships.get(subject_id, predicate, object_id)

    # "Unifies" functionality of DAOs, Pylint is not aware
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
        # records.insert
        # relationships.insert
        # MAYBE plain old insert() continues to exist? "Datastore-wide"
        # methods feel like they make sense to me, there just wouldn't be
        # a huge number.
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

    # There's only one delete right now, but there could be more.
    def delete_records(self, objects_to_delete):
        """
        Given one or more Sina objects, insert them into the DAO's backend.

        :param objects_to_delete: Some id(s) of Record(s) to delete.
        """
        # records.delete
        return self.records.delete(objects_to_delete)

    def get_records_with_data(self, **kwargs):
        """
        """
        # With or given? I prefer "with" because of how it reads once there
        # are args. get_records_with_data() looks like it's just getting
        # all records with data (no), but get_records_with_data(volume=10)
        # reads better to me than the prior get_given_data(volume=10).
        # but this is much more obvious for get_with_max vs. get_given_max.
        # Latter doesn't really make sense.
        # records.query_data
        # records.data.get_with_data
        return self.records.data_query(kwargs)

    def get_records_of_type(self, type, ids_only=False):
        """
        """
        # records.get_by_type
        return self.records.get_all_of_type(type, ids_only)

    def get_record_types(self):
        """
        """
        # records.get_types
        return self.records.get_available_types()

    def get_records_with_file_uri(self, uri, accepted_ids_list=None,
                                  ids_only=False):
        """
        """
        # records.get_with_file_uri
        # records.files.get_with_uri
        return self.records.get_given_document_uri(self, uri, accepted_ids_list,
                                                   ids_only)

    def get_records_with_max(self, scalar_name, count=1, id_only=False):
        """
        """
        # records.get_with_max
        return self.records.get_with_max(scalar_name, count, id_only)

    def get_records_with_min(self, scalar_name, count=1, id_only=False):
        """
        """
        # records.get_with_min
        return self.records.get_with_min(scalar_name, count, id_only)

    # Get_scalars is legacy, will not be carried forward here.

    def get_data_for_records(self, data_list, id_list=None):
        """
        """
        # records.get_data
        return self.records.get_data_for_records(data_list, id_list)

    def get_records_with_mime_type(self, mimetype, ids_only=False):
        """
        """
        # Note: it's mime_type in the name but mimetype elsewhere.
        # records.get_with_mime_type
        return self.records.get_with_mime_type(mimetype, ids_only)
