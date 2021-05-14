"""
Describes functionality needed by DAOs and implements backend-independent logic.

Each object here should be implemented in each backend. Note that these DAOs
exist more as contracts and helpers than as descriptions of functionality--see
datastore.py for up-to-date user-level descriptions of what everything should
do.
"""
from abc import ABCMeta, abstractmethod
import logging
import numbers

import six

import sina.model
import sina.sjson as json
from sina.utils import DataRange

LOGGER = logging.getLogger(__name__)

# Disable pylint checks due to ubiquitous use of id and type
# pylint: disable=invalid-name,redefined-builtin


class RecordDAO(object):
    """The DAO responsible for handling Records."""

    __metaclass__ = ABCMeta

    def get(self, ids, _record_builder=sina.model.generate_record_from_json, chunk_size=999):
        """
        Given an (iterable of) id(s), return matching Record(s).

        :param ids: The id(s) of the Record(s) to return.
        :param chunk_size: Size of chunks to pull records in.
        :param _record_builder: The function used to create a Record object
                                (or one of its children) from the raw. Does not
                                need to be touched by the user.

        :returns: If provided an iterable, a generator of Record objects, else a
                  single Record object.

        :raises ValueError: if no Record is found for some id.
        """

        if isinstance(ids, six.string_types):
            LOGGER.debug('Getting record with id=%s', ids)
            return self._get_one(ids, _record_builder)

        ids = list(ids)
        LOGGER.debug('Getting records with ids in %s', ids)
        return self._get_many(ids, _record_builder, chunk_size)

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
        raw = self.get_raw(id)
        return _record_builder(json_input=json.loads(raw))

    @abstractmethod
    def _get_many(self, ids, _record_builder, chunk_size):
        """
        Apply some "get" function to an iterable of Record ids.

        Because the overload needs to be invisible to the user, we need to
        be able to return both a generator (from a list) and non-generator
        (from a single ID). This is the framework for allowing it.

        Currently, this makes sense because Cassandra can't batch reads. May
        be worth revisiting.

        :param id: An Iterable of Record ids to return
        :param _record_builder: The function used to create a Record object
                                (or one of its children) from the raw.

        :returns: A generator of Records if found, else None.

        :raises ValueError: if no Record is found for the ids.
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

    def update(self, records):
        """
        Given one or more Records, update them in the backend.

        :param records: A Record or iterable of Records to update.
        """
        if isinstance(records, sina.model.Record):
            LOGGER.debug('Updating record with id=%s', records.id)
            ids = [records.id]
            records = [records]
        else:
            records = list(records)  # In case it's a generator
            ids = [record.id for record in records]
            LOGGER.debug('Updating records with ids=%s', ids)
        if not all(self.exist(ids)):
            raise ValueError("Can't update a record that hasn't been inserted!")
        self._do_update(records)

    @abstractmethod
    def _do_update(self, records):
        """Handle the logic of the upate itself."""
        raise NotImplementedError

    @abstractmethod
    def insert(self, records):
        """
        Given one or more Records, insert them into the DAO's backend.

        :param records: A Record or iter of Records to insert
        """
        raise NotImplementedError

    @abstractmethod
    def get_raw(self, id_):
        """
        Get the raw content of the record identified by the given ID.

        :param id_: the ID of the record
        :return: the raw JSON for the specified record
        :raises: ValueError if the record does not exist
        """
        raise NotImplementedError

    @abstractmethod
    def data_query(self, **kwargs):
        """
        Return the ids of all Records whose data fulfill some criteria.

        Criteria are expressed as keyword arguments. Each keyword
        is the name of an entry in a Record's data field, and it's set
        equal to a single value, a DataRange (see utils.DataRanges
        for more info), or a special criteria (ex: ScalarListCriteria
        from has_all(), see utils) that expresses the desired value/range of
        values. All criteria must be satisfied for an ID to be returned:

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

    def get_all(self, ids_only):
        """
        Return all Records.

        :param ids_only: whether to return only the ids of matching Records

        :returns: A generator of all Records.
        """
        raise NotImplementedError

    @abstractmethod
    def get_available_types(self):
        """
        Return a list of all the Record types in the database.

        :returns: A list of types present (ex: ["run", "experiment"])
        """
        raise NotImplementedError

    def exist(self, test_ids):
        """
        Given an (iterable of) id(s), return boolean (list) of whether those
        record(s) exist or not.

        :param ids: The id(s) of the Record(s) to test.

        :returns: If provided an iterable, a generator of bools pertaining to
                  the ids' existence, else a single boolean value.
        """

        if isinstance(test_ids, six.string_types):
            LOGGER.debug('Getting record with id=%s', test_ids)
            return self._one_exists(test_ids)

        LOGGER.debug('Getting records with ids in %s', test_ids)
        return self._many_exist(test_ids)

    @abstractmethod
    def _one_exists(self, test_id):
        """
        Given an id, return boolean

        :param ids: The id(s) of the Record(s) to test.

        :returns: A single boolean value pertaining to the id's existence.
        """
        raise NotImplementedError

    @abstractmethod
    def _many_exist(self, test_ids):
        """
        Given an iterable of ids, return boolean list of whether those
        records exist or not.

        :param ids: The ids of the Records to test.

        :returns: A generator of bools pertaining to the ids' existence.
        """
        raise NotImplementedError

    @abstractmethod
    def data_names(self, record_type, data_types):
        """
        Return a list of all the data labels for data of a given type.
        Defaults to getting all data names for a given record type.

        :param record_type: Type of records to get data names for.
        :param data_types: A single data type or a list of data types
                           to get the data names for.

        :returns: A generator of data names.
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

        :returns: A list of scalar JSON objects matching the Sina specification
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

    @abstractmethod
    def get_with_mime_type(self, mimetype, ids_only=False):
        """
        Return all records or IDs with documents of a given mimetype.

        :param mimetype: The mimetype to use as a search term
        :param ids_only: Whether to only return the ids

        :returns: Record object or IDs fitting the criteria.
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
    def insert(self, relationships=None, subject_id=None, object_id=None,
               predicate=None):
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

    def delete(self, subject_id=None, object_id=None, predicate=None):
        """
        Given one or more criteria, delete all matching Relationships from the DAO's backend.

        This does not affect records, data, etc. Only Relationships.

        :raise ValueError: if no criteria are specified.
        """
        LOGGER.debug('Deleting relationships with subject_id=%s, '
                     'predicate=%s, object_id=%s.',
                     subject_id, predicate, object_id)
        if subject_id is None and object_id is None and predicate is None:
            raise ValueError("Must specify at least one of subject_id, object_id, or predicate")
        self._do_delete(subject_id, object_id, predicate)

    @abstractmethod
    def _do_delete(self, subject_id=None, object_id=None, predicate=None):
        """Handle the actual deletion process."""
        raise NotImplementedError


class DAOFactory(object):
    """Builds DAOs used for interacting with Sina data objects."""

    supports_parallel_ingestion = False

    @abstractmethod
    def create_record_dao(self):
        """Create a DAO for interacting with Records."""
        raise NotImplementedError

    @abstractmethod
    def create_relationship_dao(self):
        """Create a DAO for interacting with Relationships."""
        raise NotImplementedError

    @staticmethod
    def create_run_dao():
        """Create a DAO for interacting with Runs."""
        raise AttributeError("This method is no longer available in DAOFactory."
                             "Runs are no longer treated as a special type. "
                             "Please create a recordDAO and filter on type "
                             "instead.")

    @abstractmethod
    def close(self):
        """Close any resources held by this DataHandler."""
        raise NotImplementedError

    def __enter__(self):
        """
        Use this factory as a context manager.

        :return: this factory
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Call this factory's close() method.

        :param exc_type: the type of any raised exception
        :param exc_val: the value of any raised exception
        :param exc_tb: the stack trace of any raised exception
        :return: whether a raised exception should be suppressed
        """
        self.close()
        return False
