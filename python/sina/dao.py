"""
Contains toplevel, abstract DAOs used for accessing each type of object.

This module describes the DAOs available, as well as the functions available to
each DAO. While function availabiliy may differ between objects, e.g., Records
and Relationships, it will not differ between backends, e.g., Cassandra and sql.
"""
from abc import ABCMeta, abstractmethod
import logging

import sina.model

LOGGER = logging.getLogger(__name__)


# Disable redefined-builtin, invalid-name due to ubiquitous use of id and type
# pylint: disable=C0103,W0622

class DAOFactory(object):
    """Builds DAOs used for interacting with Mnoda-based data objects."""

    __metaclass__ = ABCMeta
    supports_parallel_ingestion = False

    @abstractmethod
    def create_record_dao(self):
        """
        Create a DAO for interacting with Records.

        :returns: a RecordDAO for the DAOFactory's backend
        """
        raise NotImplementedError

    @abstractmethod
    def create_relationship_dao(self):
        """
        Create a DAO for interacting with Relationships.

        :returns: a RelationshipDAO for the DAOFactory's backend
        """
        raise NotImplementedError

    @abstractmethod
    def create_run_dao(self):
        """
        Create a DAO for interacting with Runs.

        :returns: a RunDAO for the DAOFactory's backend
        """
        raise NotImplementedError


class RecordDAO(object):
    """The DAO responsible for handling Records."""

    __metaclass__ = ABCMeta

    @abstractmethod
    def get(self, id):
        """
        Given the id of a Record, return matching Record or None.

        :param id: The id of the Record to return.

        :returns: The matching Record or None.
        """
        raise NotImplementedError

    def get_many(self, iter_of_ids):
        """
        Given an iterable of ids, retrieve each corresponding Record.

        If a given DAO's backend can bulk read more cleverly,
        this should be reimplemented there.

        :param iter_of_ids: An iterable object of ids to find.

        :returns: A generator of found records
        """
        LOGGER.debug('Getting many records with iter: %s', iter_of_ids)
        for id in iter_of_ids:
            record = self.get(id)
            yield record

    @abstractmethod
    def insert(self, record):
        """
        Given a Record, insert it into the DAO's backend.

        :param record: A Record to insert
        """
        raise NotImplementedError

    def insert_many(self, list_to_insert):
        """
        Given a list of Records, insert each into the DAO's backend.

        If a given DAO's backend can bulk insert more cleverly, this should be
        reimplemented there.

        :param list_to_insert: A list of Records to insert
        """
        LOGGER.debug('Inserting %s records.', len(list_to_insert))
        for item in list_to_insert:
            self.insert(item)

    @abstractmethod
    def delete(self, id):
        """
        Given the id of a Record, delete all mention of it from the DAO's backend.

        This includes removing all its data, its raw, any relationships
        involving it, etc.

        :param id: The id of the Record to delete.
        """
        raise NotImplementedError

    def delete_many(self, ids_to_delete):
        """
        Given a list of Record ids, delete all mentions of them from the DAO's backend.

        If a given DAO's backend can bulk delete more cleverly, this should be
        reimplemented there.

        :param ids_to_delete: A list of the ids of Records to delete.
        """
        LOGGER.debug('Deleting %i records.', len(ids_to_delete))
        for item in ids_to_delete:
            self.delete(item)

    @abstractmethod
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
        raise NotImplementedError

    def get_given_data(self, **kwargs):
        """Alias of data_query() to fit historical naming convention."""
        return self.data_query(**kwargs)

    @abstractmethod
    def get_all_of_type(self, type):
        """
        Given a type of Record, return all Records of that type.

        :param type: The type of Record to return
        """
        raise NotImplementedError

    @abstractmethod
    def get_given_document_uri(self, uri):
        """
        Return all records associated with documents whose uris match some arg.

        Supports the use of % as a wildcard character. Note that you may or may
        not get duplicates depending on the backend.

        :param uri: The uri to use as a search term, such as "foo.png"

        :returns: A generator of matching records
        """
        raise NotImplementedError

    @abstractmethod
    def get_scalars(self, id, scalar_names):
        """
        Retrieve scalars for a given record id.

        Scalars are returned in alphabetical order.

        :param id: The record id to find scalars for
        :param scalar_names: A list of the names of scalars to return

        :returns: A list of scalar JSON objects matching the Mnoda specification
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def get_files(self, id):
        """
        Retrieve files for a given record id.

        Files are returned in the alphabetical order of their URIs

        :param id: The record id to find files for

        :returns: A list of file JSON objects matching the Mnoda specification
        """
        raise NotImplementedError


class RelationshipDAO(object):
    """The DAO responsible for handling Relationships."""

    __metaclass__ = ABCMeta

    @staticmethod
    def _build_relationships(query):
        """
        Given query results, build a list of Relationships.

        :param query: The query results to build from.
        """
        LOGGER.debug('Building relationships from query=%s', query)
        relationships = []
        for relationship in query:
            rel_obj = sina.model.Relationship(subject_id=relationship.subject_id,
                                              object_id=relationship.object_id,
                                              predicate=relationship.predicate)
            relationships.append(rel_obj)
        return relationships

    @abstractmethod
    def insert(self, subject_id=None, object_id=None,
               predicate=None, relationship=None):
        """
        Given a Relationship, insert it into the DAO's backend.

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
        raise NotImplementedError

    def insert_many(self, list_to_insert):
        """
        Given a list of Relationships, insert each into the DAO's backend.

        If a given DAO's backend can bulk insert more cleverly (bulk inserts),
        this should be reimplemented there.

        :param list_to_insert: A list of Relationships to insert
        """
        for item in list_to_insert:
            self.insert(item)

    def get(self, subject_id=None, object_id=None, predicate=None):
        """
        Given Relationship info, return matching Relationships (or empty list).

        Acts as a wrapper for RelationshipDAO's other getters and calls them
        conditionally.

        :param subject_id: the subject_id of Relationships to return
        :param object_id: the object_id of Relationships to return
        :param predicate: the predicate of Relationships to return

        :raises ValueError: if none of the parameters are provided.
        """
        if not (subject_id or object_id or predicate):
            raise ValueError("Must supply subject_id, object_id, or predicate")
        if subject_id:
            return self._get_given_subject_id(subject_id, predicate)
        elif object_id:
            return self._get_given_object_id(object_id, predicate)
        return self._get_given_predicate(predicate)

    @abstractmethod
    def _get_given_subject_id(self, subject_id, predicate=None):
        """
        Given record id, return all Relationships with that id as subject.

        Returns None if none found. Wrapped by get(). Optionally filters on
        predicate as well (TODO: misleading name? Should it be internal?).

        :param subject_id: The subject_id of Relationships to return
        :param predicate: Optionally, the Relationship predicate to filter on.

        :returns: A list of Relationships fitting the criteria or None.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_given_object_id(self, object_id, predicate=None):
        """
        Given record id, return all Relationships with that id as object.

        Returns None if none found. Wrapped by get(). Optionally filters on
        predicate as well.

        :param object_id: The object_id of Relationships to return
        :param predicate: Optionally, the Relationship predicate to filter on.

        :returns: A list of Relationships fitting the criteria or None.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_given_predicate(self, predicate):
        """
        Given predicate, return all Relationships with that predicate.

        :param predicate: The predicate describing Relationships to return

        :returns: A list of Relationships fitting the criteria
        """
        raise NotImplementedError


class RunDAO(object):
    """The DAO responsible for handling Runs, a subtype of Record."""

    __metaclass__ = ABCMeta

    def __init__(self, record_dao):
        """
        Initialize RunDAO with contained RecordDAO and backend.

        :param record_dao: A RecordDAO used to interact with the Record table
        :param backend: The DAO's backend (ex: filepath, SQLite session)
        """
        self.record_dao = record_dao

    @abstractmethod
    def get(self, id):
        """
        Given id, return matching Run from the DAO's backend, or None.

        :param id: The id of the run to return.

        :returns: The matching Run or None.
        """
        raise NotImplementedError

    def get_many(self, iter_of_ids):
        """
        Given an iterable of ids, retrieve each corresponding run from backend.

        If a given DAO's backend can bulk read more cleverly,
        this should be reimplemented there.

        :param iter_of_ids: An iterable object of ids to find.

        :returns: A generator of found runs
        """
        for id in iter_of_ids:
            yield self.get(id)

    @abstractmethod
    def insert(self, run):
        """
        Given a Run, insert it into the DAO's backend.

        :param run: A run to insert
        """
        raise NotImplementedError

    def insert_many(self, list_to_insert):
        """
        Given a list of Runs, insert each into the DAO's backend.

        If a given DAO's backend can bulk insert more cleverly (bulk inserts),
        this should be reimplemented there.

        :param list_to_insert: A list of Runs to insert
        """
        for item in list_to_insert:
            self.insert(item)

    @abstractmethod
    def delete(self, id):
        """
        Given the id of a Run, delete all mention of it from the DAO's backend.

        This includes removing all its data, its raw, any relationships
        involving it, etc.

        :param id: The id of the Run to delete.
        """
        raise NotImplementedError

    def delete_many(self, ids_to_delete):
        """
        Given a list of Run ids, delete all mentions of them from the DAO's backend.

        If a given DAO's backend can bulk delete more cleverly, this should be
        reimplemented there.

        :param ids_to_delete: A list of the ids of Runs to delete.
        """
        LOGGER.debug('Deleting %i runs.', len(ids_to_delete))
        for item in ids_to_delete:
            self.delete(item)

    def get_all(self, ids_only=False):
        """
        Return all Records with type 'run'.

        :param ids_only: whether to return only the ids of matching Runs
                         (used for further filtering)
        :returns: A list of all Records which are Runs
        """
        # Collapsed TODO down, we can reindex on type
        # NYI in Cassandra
        return self.record_dao.get_all_of_type('run', ids_only)

    def data_query(self, **kwargs):
        """
        Call Record's implementation then filter on type.

        :param scalar_range: A sina.ScalarRange describing the criteria

        :returns: A generator of run ids fitting the criteria
        """
        run_gen = self.get_all(ids_only=True)
        if run_gen is None:
            return
        matched_records = set(self.record_dao.data_query(**kwargs))
        if matched_records:
            for run in run_gen:
                if run in matched_records:
                    yield run

    def get_given_data(self, **kwargs):
        """Alias data_query()."""
        return self.data_query(**kwargs)

    def get_given_document_uri(self, uri):
        """
        Return runs associated with a document uri.

        Really just calls Record's implementation.

        :param uri: The uri to match.

        :returns: A generator of Runs fitting the criteria
        """
        records = self.record_dao.get_given_document_uri(uri)
        if records:
            for record in records:
                if record.type == "run":
                    yield sina.model.convert_record_to_run(record)
