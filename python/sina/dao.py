"""
Contains toplevel, abstract DAOs used for accessing each type of object.

This module describes the DAOs available, as well as the functions available to
each DAO. While function availabiliy may differ between objects, e.g., Records
and Relationships, it will not differ between backends, e.g., Cassandra and sql.
"""
from abc import ABCMeta, abstractmethod
import logging
import numbers

import six

import sina.model
from sina.utils import DataRange

LOGGER = logging.getLogger(__name__)


# Disable pylint checks due to ubiquitous use of id and type
# pylint: disable=invalid-name,redefined-builtin

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

    def get(self, ids, _record_builder=sina.model.generate_record_from_json):
        """
        Given an (iterable of) id(s), return matching Record(s).

        :param ids: The id(s) of the Record(s) to return.
        :param _record_builder: The function used to create a Record object
                                (or one of its children) from the raw. Used
                                by DAOs calling get() (RecordDAO, RunDAO), does not
                                need to be touched by the user.

        :returns: If provided an iterable, a generator of Record objects, else a
                  single Record object.

        :raises ValueError: if no Record is found for some id.
        """
        def gen_records(ids):
            """Hack around the limitation of returning generators XOR non-gens."""
            for id in ids:
                yield self._get_one(id, _record_builder)

        if isinstance(ids, six.string_types):
            LOGGER.debug('Getting record with id=%s', ids)
            return self._get_one(ids, _record_builder)
        ids = list(ids)
        LOGGER.debug('Getting records with ids in=%s', ids)
        return gen_records(ids)

    @abstractmethod
    def _get_one(self, id, _record_builder):
        """
        Apply some "get" function to a single Record id.

        Because the overload needs to be invisible to the user, we need to
        be able to return both a generator (from a list) and non-generator
        (from a single ID). This is the framework for allowing it.

        Currently, this makes sense because Cassandra can't batch reads. May
        be worth revisiting.

        :param id: A Record id to return
        :param _record_builder: The function used to create a Record object
                                (or one of its children) from the raw.

        :returns: A Record if found, else None.

        :raises ValueError: if no Record is found for the id.
        """
        raise NotImplementedError

    @abstractmethod
    def insert(self, records):
        """
        Given one or more Records, insert them into the DAO's backend.

        :param records: A Record or iter of Records to insert
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids):
        """
        Given one or more Record ids, delete all mention from the DAO's backend.

        This includes removing all data, raw(s), any relationships
        involving it/them, etc.

        :param ids: A Record id or iterable of Record ids to delete.
        """
        raise NotImplementedError

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

    @staticmethod
    def _criteria_are_for_scalars(criteria):
        """
        Determine whether criteria for a single datum describes scalars or strings.

        If criteria are mixed (both scalar and string criteria), raise an error.

        :param criteria: The criteria to check.
        :returns: True if they're all scalar criteria, false if all string criteria.
        :raises TypeError: if mixed-type criteria are provided.
        """
        criterion_is_for_scalars = []
        for criterion in criteria:
            if isinstance(criterion, DataRange):
                criterion_is_for_scalars.append(criterion.is_numeric_range())
            else:
                criterion_is_for_scalars.append(isinstance(criterion, numbers.Real))
        if not all(criterion_is_for_scalars[0] == x for x in criterion_is_for_scalars):
            raise TypeError("String and scalar criteria cannot be mixed for one datum. Given: {}"
                            .format(criteria))
        return criterion_is_for_scalars[0]

    @abstractmethod
    def get_all_of_type(self, type, ids_only=False):
        """
        Given a type of Record, return all Records of that type.

        :param type: The type of Record to return
        :param ids_only: whether to return only the ids of matching Records

        :returns: A generator of matching Records.
        """
        raise NotImplementedError

    @abstractmethod
    def get_available_types(self):
        """
        Return a list of all the Record types in the database.

        :returns: A list of types present (ex: ["run", "experiment"])
        """
        raise NotImplementedError

    @abstractmethod
    def get_given_document_uri(self, uri, accepted_ids_list=None, ids_only=False):
        """
        Return all records associated with documents whose uris match some arg.

        Supports the use of % as a wildcard character. Note that you may or may
        not get duplicates depending on the backend.

        :param uri: The uri to use as a search term, such as "foo.png"
        :param accepted_ids_list: A list of ids to restrict the search to.
                                  If not provided, all ids will be used.
        :param ids_only: whether to return only the ids of matching Records

        :returns: A generator of matching Records
        """
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    def get_scalars(self, id, scalar_names):
        """
        LEGACY: Retrieve scalars for a given record id.

        Scalars are returned in alphabetical order. Consider using Record.data instead.

        :param id: The record id to find scalars for
        :param scalar_names: A list of the names of scalars to return

        :returns: A list of scalar JSON objects matching the Mnoda specification
        """
        raise NotImplementedError

    @abstractmethod
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
    def insert(self, relationships=None, subject_id=None,
               object_id=None, predicate=None):
        """
        Given one or more Relationships, insert into the DAO's backend.

        This can create an entry from either an existing Relationship object
        or from its components (subject id, object id, predicate). If all four
        are provided, the Relationship will be used.

        A Relationship describes the connection between two objects in the
        form <subject_id> <predicate> <object_id>, ex:

        Task44 contains Run2001

        :param subject_id: The id of the subject.
        :param object_id: The id of the object.
        :param predicate: A string describing the relationship.
        :param relationships: A Relationship object to build entry from, or an
                             iterable of them

        :raises: A ValueError if neither Relationship nor the subject_id,
                 object_id, and predicate args are provided.
        """
        raise NotImplementedError

    @staticmethod
    def _validate_insert(relationship=None, subject_id=None,
                         object_id=None, predicate=None):
        """
        Make sure that what we're trying to insert forms a valid Relationship.

        A user can give us either the components for a Relationship or the
        Relationship itself. This helper figures out which and arranges the
        components so that the "real" Relationship insert() can insert cleanly.
        It raises warnings/errors if anything's out of place.

        :param subject_id: The id of the subject.
        :param object_id: The id of the object.
        :param predicate: A string describing the relationship.
        :param relationship: A Relationship object to build entry from.
        :returns: The subject_id, object_id, and predicate

        :raises: A ValueError if neither Relationship nor the subject_id,
                 object_id, and predicate args are provided.
        """
        LOGGER.debug('Inserting relationship=%s, subject_id=%s, object_id=%s, '
                     'and predicate=%s.', relationship, subject_id, object_id, predicate)
        if all([relationship, subject_id, object_id, predicate]):
            LOGGER.warning('Given both relationship object and '
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
        return subject_id, object_id, predicate

    @abstractmethod
    def get(self, subject_id=None, object_id=None, predicate=None):
        """
        Given Relationship info, return matching Relationships (or empty list).

        Acts as a wrapper for RelationshipDAO's other getters and calls them
        conditionally.

        :param subject_id: the subject_id of Relationships to return
        :param object_id: the object_id of Relationships to return
        :param predicate: the predicate of Relationships to return
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
    def _return_only_run_ids(self, ids):
        """
        Given a(n iterable) of id(s) which might be any type of Record, clear out non-Runs.

        :param ids: An id or iterable of ids to sort through

        :returns: For each id, the id if it belongs to a Run, else None. Returns an iterable
                  if "ids" is an iterable, else returns a single value.
        """
        raise NotImplementedError

    def get(self, ids):
        """
        Given a(n iterable of) id(s), return matching Run(s) from the DAO's backend.

        :param ids: The id or an iterable of ids to find and return Runs for. If a
                    Record with that id exists but is not a Run, it won't be returned.

        :returns: If provided an iterable, a generator containing either
                  a matching Run or None for each identifier provided. In the
                  case that an id (not an iterator of ids) is provided, will
                  return a Run or None.

        :raises ValueError: if no Record is found for some id(s).
        """
        if isinstance(ids, six.string_types):
            LOGGER.debug('Getting Run with id: %s', ids)
            run_ids = self._return_only_run_ids(ids)
            if run_ids is None:
                raise ValueError("No Run found with id {}.".format(id))
        else:
            LOGGER.debug('Getting Runs with ids: %s', ids)
            run_ids = list(self._return_only_run_ids(ids))  # Gen safety
            if None in run_ids:
                ids_not_found = set(ids).difference(run_ids)
                raise ValueError("No Runs found with ids: {}".format(ids_not_found))
        return self.record_dao.get(run_ids, _record_builder=sina.model.generate_run_from_json)

    @abstractmethod
    def insert(self, runs):
        """
        Given a(n iterable of) Run(s), insert them into the DAO's backend.

        :param runs: A Run or iterable of Runs to insert
        """
        raise NotImplementedError

    @abstractmethod
    def delete(self, ids):
        """
        Given a(n iterable of) Run id(s), delete all mention from the DAO's backend.

        This includes removing all data, raw(s), any relationships
        involving it/them, etc.

        :param ids: A Run id or iterable of Run ids to delete.
        """
        raise NotImplementedError

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
        matched_runs = self._return_only_run_ids(self.record_dao.data_query(**kwargs))
        for entry in matched_runs:
            if entry is not None:
                yield entry

    def get_given_data(self, **kwargs):
        """Alias data_query()."""
        return self.data_query(**kwargs)

    def get_given_document_uri(self, uri, accepted_ids_list=None, ids_only=False):
        """
        Return Runs associated with a document uri.

        Mostly identical to Record's implementation, also filters out non-Runs.

        :param uri: The uri to match.
        :param accepted_ids_list: A list of ids to restrict the search to.
                                  If not provided, all ids will be used.
        :param ids_only: whether to return only the ids of matching Runs
                         (used for further filtering)

        :returns: A generator of Runs fitting the criteria
        """
        records = self.record_dao.get_given_document_uri(uri,
                                                         accepted_ids_list=accepted_ids_list,
                                                         ids_only=ids_only)
        if ids_only:
            for run_id in self._return_only_run_ids(records):
                yield run_id
        else:
            for record in records:
                if record.type == "run":
                    yield sina.model.generate_run_from_json(record.raw)
