"""
Describes functionality needed by DAOs and implements backend-independent logic.

Each object here should be implemented in each backend. Note that these DAOs
exist more as contracts and helpers than as descriptions of functionality--see
datastore.py for up-to-date user-level descriptions of what everything should
do.
"""
from abc import ABCMeta, abstractmethod
import copy
import logging
import numbers

import six

import sina.model
import sina.sjson as json
from sina.utils import DataRange, Negation

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

        _record_builder is for internal use only, the function used to create a Record object
        (or one of its children) from the raw. Should not be touched by the user.

        Likewise, chunk_size is a machine-specific parameter set to 999 for safety to limit
        the size of an IN query below the compiled max in SQL. Should usually not be touched.

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

    def _do_delete_all_records(self):
        """Implement logic for Datastore's delete_all_contents()."""
        # Relies on the propagated deletes of the RecordDAO, which also wipe out
        # relationships. Could be made more efficient with the use of TRUNCATE or the
        # like, but if this somehow becomes a performance bottleneck and requires
        # that upgrade, make sure you add backend-specific tests that make sure all
        # tables are cleared. At that point, it may belong in the DAOFactory.
        self.delete(self.get_all(ids_only=True))

    def update(self, records):
        """
        Given one or more Records, update them in the backend.

        :param records: A Record or iterable of Records to update.
        """
        if isinstance(records, sina.model.Record):
            LOGGER.debug('Updating record with id=%s', records.id)
            ids = [records.id]
            records = [sina.model.flatten_library_content(records)]
        else:
            records = [sina.model.flatten_library_content(record) for record in records]
            ids = [record.id for record in records]
            LOGGER.debug('Updating records with ids=%s', ids)
        if not all(self.exist(ids)):
            raise ValueError("Can't update a record that hasn't been inserted!")
        self._do_update(records)

    @abstractmethod
    def _do_update(self, records):
        """Handle the logic of the update itself."""
        raise NotImplementedError

    def insert(self, records, ingest_funcs=None,
               ingest_funcs_preserve_raw=None):
        """
        Given one or more Records, insert them into the DAO's backend.

        :param records: A Record or iter of Records to insert
        :param ingest_funcs: A function or list of functions to
                             run against each record before insertion.
                             We queue them up to run here. They will be run in list order.
        :param ingest_funcs_preserve_raw: Whether the postprocessing is allowed
                                          to touch the underlying json on ingest.
                                          If we can interact with the raw, we don't
                                          need to pass an unaltered set of records.
                                          MUST BE SPECIFIED if using ingest_funcs
        """
        if isinstance(records, (sina.model.Record, sina.model.Run)):
            records = [records]
        if callable(ingest_funcs):
            ingest_funcs = [ingest_funcs]
        if ingest_funcs is None:
            self._do_insert(sina.model.flatten_library_content(record) for record in records)
            return
        else:
            if ingest_funcs_preserve_raw is None:
                raise ValueError(
                    "`ingest_funcs_preserve_raw` must be specified when using ingest_funcs")
        self._do_insert(self._do_process(record, ingest_funcs,
                                         ingest_funcs_preserve_raw)
                        for record in records)

    @staticmethod
    def _do_process(record, postprocessing_funcs, preserve_raw):
        """Simply applies a set of functions to some record and returns the results."""
        if preserve_raw:
            preserved_raw = copy.deepcopy(record.raw)
        for func in postprocessing_funcs:
            record = func(record)
        record = sina.model.flatten_library_content(record)
        if preserve_raw:
            if not record.library_data:
                # flatten_library_content usually skips anything without library data
                # for efficiency, but we need its created _FlatRecord here to decouple
                # the raw from the data.
                # pylint: disable=protected-access
                record = sina.model._FlatRecord(**record.raw)
            record.raw = preserved_raw
        return record

    @abstractmethod
    def _do_insert(self, records):
        """Handle the logic of the insert itself."""
        raise NotImplementedError

    @abstractmethod
    # Sphinx has an issue with trailing-underscore params, we need to escape it for the doc
    # pylint: disable=anomalous-backslash-in-string
    def get_raw(self, id_):
        """
        Get the raw content of the record identified by the given ID.

        :param id\_: the ID of the record
        :return: the raw JSON for the specified record
        :raises: ValueError if the record does not exist
        """
        raise NotImplementedError

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
        LOGGER.debug('Finding all records fulfilling criteria: %s', kwargs.items())
        # No kwargs is bad usage. Bad kwargs are caught in sort_criteria().
        if not kwargs.items():
            raise ValueError("You must supply at least one criterion.")
        return self._do_data_query(criteria=kwargs)

    @abstractmethod
    def _do_data_query(self, criteria, id_pool=None):
        """Handle the backend dependent logic of data_query."""
        raise NotImplementedError

    def get_given_data(self, **kwargs):
        """Alias of data_query() to fit historical naming convention."""
        return self.data_query(**kwargs)

    @staticmethod
    def _ensure_is_list(arg):
        """
        Ensure args are expressed as lists.

        For user QoL, some queries can take either a single criterion
        (ex: "run") or several as a list (ex: ["run", "test", "msub"]).
        This method is used to standardize into the list expected by some
        backend-side query functions.
        """
        if isinstance(arg, six.string_types):
            return [arg]
        return list(arg)  # safety cast for gens

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

    def get_all_of_type(self, types, ids_only=False, id_pool=None):
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
        if isinstance(types, Negation):
            types.arg = self._ensure_is_list(types.arg)
        else:
            types = self._ensure_is_list(types)
        # safety cast for id_pool as well
        if id_pool is not None:
            id_pool = list(id_pool)  # safety cast for gens
        LOGGER.debug('Getting all records with types in %s.', types)
        return self._do_get_all_of_type(types, ids_only, id_pool)

    @abstractmethod
    def _do_get_all_of_type(self, types, ids_only=False, id_pool=None):
        """Handle backend-specific logic for get_all_of_type."""
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

    @abstractmethod
    def get_curve_set_names(self):
        """
        Return the names of all curve sets available in the backend.

        :returns: An iterable of curve set names.
        """
        raise NotImplementedError

    def exist(self, test_ids):
        """
        Given an (iterable of) id(s), return boolean (list) of whether those
        record(s) exist or not.

        :param test_ids: The id(s) of the Record(s) to test.

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
    def data_names(self, record_type, data_types, filter_constants):
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
        raise NotImplementedError

    def get_given_document_uri(self, uri, accepted_ids_list=None, ids_only=False):
        """
        Handle shared backend logic for datastore's find_with_file_uris().

        NOTE: Args were moved and cleaned up for datastore version. This old
        version uses accepted_ids_list instead of id_pool.
        """
        LOGGER.debug('Getting record with uris matching uri criterion %s', uri)
        if accepted_ids_list is not None:
            id_pool = list(accepted_ids_list)
            LOGGER.debug('Restricting to %i ids.', len(id_pool))
        return self._do_get_given_document_uri(uri=uri,
                                               id_pool=accepted_ids_list,
                                               ids_only=ids_only)

    @abstractmethod
    def _do_get_given_document_uri(self, uri, id_pool=None, ids_only=False):
        """Handle backend-specific logic for datastore's find_with_file_uris()."""
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
    def get_with_mime_type(self, mimetype, ids_only=False, id_pool=None):
        """
        Return all records or IDs with documents of a given mimetype.

        :param mimetype: The mimetype to use as a search term
        :param ids_only: Whether to only return the ids
        :param id_pool: Used when combining queries: a pool of ids to restrict
                        the query to. Only records with ids in this pool can be
                        returned.

        :returns: Record object or IDs fitting the criteria.
        """
        raise NotImplementedError

    # High arg count is inherent to the functionality.
    # pylint: disable=too-many-arguments
    def _find(self, types=None, data=None, file_uri=None,
              mimetype=None, id_pool=None, ids_only=False,
              query_order=("data", "file_uri", "mimetype", "types")):
        """Implement cross-backend logic for the DataStore method of the same name."""
        LOGGER.debug('Performing a general find() query with order %s', query_order)
        query_map = {"data": (self._do_data_query, data),
                     "file_uri": (self._do_get_given_document_uri, file_uri),
                     "mimetype": (self.get_with_mime_type, mimetype),
                     "types": (self.get_all_of_type, types)}

        if all((x is None for x in [types, data, file_uri, mimetype])):
            # Not passing any filter is valid usage; we return all.
            if id_pool is None:
                return self.get_all(ids_only=ids_only)
            # Passing in only id_pool is valid usage; we return all that exist.
            existing_ids = [x[1] for x in zip(self.exist(id_pool), id_pool) if x[0]]
            if ids_only:
                return (x for x in existing_ids)
            return self.get(existing_ids)

        for query_type in query_order:
            query_func, arg = query_map[query_type]
            if arg is not None:
                if query_type == "data":
                    # Data has no ids_only
                    id_pool = list(query_func(arg, id_pool=id_pool))
                else:
                    # This usage of query_func seems to confuse pylint; it complains as
                    # long as I'm using ids_only=True, maybe it's "seeing" the call above.
                    id_pool = list(
                        query_func(arg,  # pylint: disable=unexpected-keyword-arg
                                   id_pool=id_pool,
                                   ids_only=True))
                # Break early, as an empty id_pool is bad usage for a query.
                if not id_pool:
                    return (x for x in [])
        if ids_only:
            return (x for x in id_pool)
        return self.get(id_pool)


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
