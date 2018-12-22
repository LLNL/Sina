"""
Contains toplevel, abstract DAOs used for accessing each type of object.

This module describes the DAOs available, as well as the functions available to
each DAO. While function availabiliy may differ between objects, ex: Records
and Relationships, it will not differ between backends, ex: Cassandra and sql.
"""
from abc import ABCMeta, abstractmethod
import logging
from sqlalchemy.orm.exc import NoResultFound

from sina import model

LOGGER = logging.getLogger(__name__)


class DAOFactory(object):
    """Builds DAOs used for interacting with Mnoda-based data objects."""

    __metaclass__ = ABCMeta
    supports_parallel_ingestion = False

    @abstractmethod
    def createRecordDAO():
        """
        Create a DAO for interacting with Records.

        :returns: a RecordDAO for the DAOFactory's backend
        """
        raise NotImplementedError

    @abstractmethod
    def createRelationshipDAO():
        """
        Create a DAO for interacting with Relationships.

        :returns: a RelationshipDAO for the DAOFactory's backend
        """
        raise NotImplementedError

    @abstractmethod
    def createRunDAO():
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
        LOGGER.debug('Getting many records with iter: {}'.format(iter_of_ids))
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
        LOGGER.debug('Inserting {} records.'.format(len(list_to_insert)))
        for item in list_to_insert:
            self.insert(item)

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
    def get_given_scalars(self, scalar_range_list):
        """
        Return all records with scalars fulfilling some criteria.

        Note that this is a logical 'and'--the record must satisfy every
        conditional provided (which is also why this can't simply call
        get_given_scalar() as get_many() does with get()).

        :param scalar_range_list: A list of 'sina.ScalarRange's describing the
                                 different criteria.

        :returns: A generator of Records fitting the criteria
        """
        raise NotImplementedError

    @abstractmethod
    def get_given_scalar(self, scalar_range):
        """
        Return all records where some scalar fulfills some criteria.

        Example criteria: height > 20.0, 2 < volume <= inf, etc. See
        sina.utils.ScalarRange for further info (import as sina.ScalarRange).

        :param scalar_range: A 'sina.ScalarRange' describing the criteria.

        :returns: A generator of Records fitting the criteria
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

    def compare_records_ids(self,
                            id_one,
                            id_two,
                            ignore_order=True,
                            report_repetition=False,
                            significant_digits=None,
                            verbose_level=2,
                            exclude_paths=[],
                            exclude_types=[],
                            view='tree'):
        """
        Given two record ids, get the records and compare them.

        A comparison of two records consists of the following: Reporting any
        differences between their keys and reporting any differences between
        the values of the keys that are in both records.

        This function uses the package DeepDiff. Many of the parameters given
        here are passed directly to DeepDiff. See their docs at:
        https://deepdiff.readthedocs.io/en/latest

        :param id_one: string. The id of the first record to compare.
        :param id_two: string. The id of the second record to compare.
        :param ignore_order: boolean, default True. Ignores orders for
                             iterables.
        :paramreport_repetition:  boolean, default False. Reports repetitions
                                  when set True.
        :param significant_digits: int >= 0, default None. Digits after the
                                   decimal point.
        :param verbose_level: int >=0. Default 2.
                              0: Won't report values when type changed.
                              1: DeepDiff default.
                              2: Will report values when custom objects or
                                 dictionaries have items added or removed.
        :param exclude_paths: list, default empty list. List of paths to
                              exclude from the report.
        :param exclude_types: list, default empty list. List of object types to
                               exclude from the report.
        :param view: string, default 'tree'. Support 'text' or 'tree'. Text is
                     the regular output. Tree allows you to traverse through
                     the tree of the changed items.
        :raises ValueError: If given an id that we can't find.
        :returns: A DeepDiff object.
        """
        LOGGER.debug('Comparing id={} vs id={}'.format(id_one, id_two))
        try:
            record_one = self.get(id=id_one)
        except NoResultFound:
            msg = 'Could not find record with id <{}>. Check id and '\
                  'database.'.format(id_one)
            LOGGER.error(msg)
            raise ValueError(msg)
        try:
            record_two = self.get(id=id_two)
        except NoResultFound:
            msg = 'Could not find record with id <{}>. Check id and '\
                  'database.'.format(id_two)
            LOGGER.error(msg)
            raise ValueError(msg)
        return model.compare_records(record_one=record_one,
                                     record_two=record_two,
                                     ignore_order=ignore_order,
                                     report_repetition=report_repetition,
                                     significant_digits=significant_digits,
                                     verbose_level=verbose_level,
                                     exclude_paths=exclude_paths,
                                     exclude_types=exclude_types,
                                     view=view)


class RelationshipDAO(object):
    """The DAO responsible for handling Relationships."""

    __metaclass__ = ABCMeta

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
        else:
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

    def __init__(self, record_DAO):
        """
        Initialize RunDAO with contained RecordDAO and backend.

        :param record_DAO: A RecordDAO used to interact with the Record table
        :param backend: The DAO's backend (ex: filepath, SQLite session)
        """
        self.record_DAO = record_DAO

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

        :param list_to_insert: A list of Records to insert
        """
        for item in list_to_insert:
            self.insert(item)

    def get_all(self):
        """
        Return all Records with type 'run'.

        :returns: A list of all Records which are runs
        """
        # Collapsed TODO down, we can reindex on type
        # NYI in Cassandra
        super(RunDAO, self).get_given_type(self, 'run')

    def get_given_scalar(self, scalar_range):
        """
        Return runs where scalar_name's value is within some range.

        Specifically, returns all Runs for which scalar_name
        is between scalar_min and scalar_max (or, if both are None,
        for which scalar_name exists)

        Really just calls Record's implementation.

        :param scalar_range: A sina.ScalarRange describing the criteria

        :returns: A generator of Runs fitting the criteria
        """
        records = self.record_DAO.get_given_scalar(scalar_range)
        if records:
            for record in records:
                if record.type == "run":
                    yield self._convert_record_to_run(record)

    def get_given_document_uri(self, uri):
        """
        Return runs associated with a document uri.

        Really just calls Record's implementation.

        :param uri: The uri to match.

        :returns: A generator of Runs fitting the criteria
        """
        records = self.record_DAO.get_given_document_uri(uri)
        if records:
            for record in records:
                if record.type == "run":
                    yield self._convert_record_to_run(record)
