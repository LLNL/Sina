"""Module for handling miscellany."""
from __future__ import print_function
import logging
import json
import os
import errno
import uuid
import csv
import time
import datetime
from numbers import Real
from enum import Enum
from multiprocessing.pool import ThreadPool
from collections import OrderedDict

import six

import sina.model as model

LOGGER = logging.getLogger(__name__)
MAX_THREADS = 8


class ListQueryOperation(Enum):
    """
    Describe operations possible on ListCriteria.

    For descriptions of their functionality, see their helper methods
    (has_all(), etc).
    """

    ANY = "ANY"
    ALL = "ALL"
    ONLY = "ONLY"


def import_many_jsons(factory, json_list):
    """
    Import multiple JSON documents into a supported backend.

    Lazily multithreaded for backends that support parallel ingestion.

    :param factory: The factory used to perform the import.
    :param json_list: List of filepaths to import from.
    """
    LOGGER.info('Importing json list: %s', json_list)
    if factory.supports_parallel_ingestion:
        LOGGER.debug('Factory supports parallel ingest, building thread pool.')
        arg_tuples = [(factory, x) for x in json_list]
        pool = ThreadPool(processes=min(len(json_list), MAX_THREADS))
        pool.map(_import_tuple_args, arg_tuples)
        pool.close()
        pool.join()
    else:
        LOGGER.debug('Factory does not support parallel ingest.')
        for json_file in json_list:
            import_json(factory, json_file)


def _import_tuple_args(unpack_tuple):
    """Unpack args to allow using import_json with ThreadPools in <Python3."""
    import_json(unpack_tuple[0], unpack_tuple[1])


def import_json(factory, json_path):
    """
    Import one JSON document into a supported backend.

    :param factory: The factory used to perform the import.
    :param json_path: The filepath to the json to import.
    """
    LOGGER.debug('Importing %s', json_path)
    with open(json_path) as file:
        data = json.load(file)
    runs = []
    records = []
    local = {}
    for entry in data.get('records', []):
        type = entry['type']
        if 'id' in entry:
            id = entry['id']
        else:
            id = str(uuid.uuid4())
            try:
                local[entry['local_id']] = id
                # Save the UUID to be used for record generation
                entry['id'] = id
            except KeyError:
                raise ValueError("Record requires one of: local_id, id: {}"
                                 .format(entry))
        if type == 'run':
            runs.append(model.generate_run_from_json(json_input=entry))
        else:
            records.append(model.generate_record_from_json(json_input=entry))
    factory.createRunDAO().insert_many(runs)
    factory.createRecordDAO().insert_many(records)
    relationships = []
    for entry in data.get('relationships', []):
        subj, obj = _process_relationship_entry(entry=entry, local_ids=local)
        relationships.append(model.Relationship(subject_id=subj,
                                                object_id=obj,
                                                predicate=entry['predicate']))
    factory.createRelationshipDAO().insert_many(relationships)


def _process_relationship_entry(entry, local_ids):
    """
    Read a JSON Object from Relationships and extract the subject and object.

    This helper method handles replacing local_ids with global ones, as well as
    telling which is in use, and raises any necessary errors.

    :param entry: The JSON object to be processed
    :param local_ids: The dictionary of local_id:global_id pairs

    :returns: A tuple of (subject_id, object_id)

    :raises ValueError: if the relationship doesn't have the required
                        components, or a local_id has no paired global_id.
    """
    LOGGER.debug('Processing relationship entry: %s', entry)
    try:
        subj = local_ids[entry['local_subject']] if 'subject' not in entry else entry['subject']
        obj = local_ids[entry['local_object']] if 'object' not in entry else entry['object']
    except KeyError:
        if not any(subj in ("local_subject", "subject") for subj in entry):
            msg = "Relationship requires one of: subject, local_subject: {}".format(entry)
            LOGGER.error(msg)
            raise ValueError(msg)
        if not any(obj in ("local_object", "object") for obj in entry):
            msg = "Relationship requires one of: object, local_object: {}".format(entry)
            LOGGER.error(msg)
            raise ValueError(msg)
        msg = ("Local_subject and/or local_object must be the "
               "local_id of a Record within file: {}".format(entry))
        LOGGER.error(msg)
        raise ValueError(msg)
    return (subj, obj)


def merge_ranges(list_of_ranges):
    """
    Given a list of DataRanges, merge together any that overlap.

    The new list will be ordered by the ranges' minimums in ascending order.

    :param list_of_ranges: A list of DataRanges to combine.

    :returns: list_of_ranges but merged where applicable and sorted by
              minimums in ascending order.
    """
    # First, we sort the DataRanges with regards to their min (their "left side")
    # This is done to make simple, accurate comparisons; if our ranges are ordered,
    # we can compare a max to its following min, rather than trying to maintain
    # awareness of the full list. The "range.min is not None" clause makes sure None is
    # considered the "smallest possible" for Python 3.
    sorted_ranges = sorted(list_of_ranges, key=lambda range: (range.min is not None, range.min))

    merged_ranges = [sorted_ranges[0]]
    for _range in sorted_ranges[1:]:
        # Prior_range is always the most recent entry in merged_ranges
        prior_range = merged_ranges[-1]
        if _range.overlaps(prior_range):
            # In case one range encompasses another (remember that max==None represents infinity)
            if (not _range.max_is_finite() or
                    (prior_range.max_is_finite() and _range.max > prior_range.max)):
                max_range = _range
            else:
                max_range = prior_range
            new_range = DataRange(min=prior_range.min,
                                  min_inclusive=prior_range.min_inclusive,
                                  max=max_range.max,
                                  max_inclusive=max_range.max_inclusive)
            merged_ranges[-1] = new_range
        else:
            merged_ranges.append(_range)
    return merged_ranges


def invert_ranges(list_of_ranges):
    """
    Given a list of DataRanges, give a new list that represents their opposites.

    Used for has_only queries involving ranges to produce criteria describing
    what a Record must NOT contain.

    :param list_of_ranges: A list of DataRanges to combine and invert.

    :returns: A new list of DataRanges expressing the opposite criteria.

    :raises ValueError: if given nothing to invert; "nothing" inverted is "everything",
                        but we don't allow DataRanges with both ends open, as we
                        won't know if we should be comparing to scalars or strings.
    :raises TypeError: if given both numerical and lexicographic DataRanges.
    """
    if not list_of_ranges:
        raise ValueError("list_of_ranges must contain at least one DataRange")
    if not (all(x.is_numeric_range() for x in list_of_ranges) or
            all(x.is_lexographic_range() for x in list_of_ranges)):
        raise TypeError("list_of_ranges must be only numeric DataRanges or "
                        "only lexicographic DataRanges")
    merged_ranges = merge_ranges(list_of_ranges)
    # If the "leftmost" DataRange is left-closed, we need the inverse to be left-open
    if merged_ranges[0].min_is_finite():
        inverted_ranges = [DataRange(max=merged_ranges[0].min,
                                     max_inclusive=(not merged_ranges[0].min_inclusive))]
    else:
        inverted_ranges = []
    # We continue to find the "gap" between adjacent DataRanges
    for prior_range, current_range in zip(merged_ranges[:-1], merged_ranges[1:]):
        new_range = DataRange(min=prior_range.max,
                              min_inclusive=(not prior_range.max_inclusive),
                              max=current_range.min,
                              max_inclusive=(not current_range.min_inclusive))
        inverted_ranges.append(new_range)
    # As with the leftmost, the rightmost is special. We decide open or closed.
    if merged_ranges[-1].max_is_finite():
        inverted_ranges.append(DataRange(min=merged_ranges[-1].max,
                                         min_inclusive=(not merged_ranges[-1].max_inclusive)))
    return inverted_ranges


def intersect_ordered(iterables):
    """
    Return a generator that yields the intersection of ordered iterators.

    Used when compositing queries where each step returns an iterator of Record
    ids. Important to avoid too much being stored in memory; here, we only store
    the generator stack plus (len(iterables)+C) values.

    :param gen_list: A list of iterators. Must be ordered by the same criteria!

    :returns: A generator that crawls through the iterators and returns
              values that all of them share.

    :raises StopIteration: when it runs out of values
    """
    # Quit fast as we'll be assuming at least one generator.
    if not iterables:
        return

    # Standardize all iterators to generators
    gen_list = []
    for iter in iterables:
        gen_list.append(x for x in iter)

    # Get our first set
    most_recents = []
    for gen in gen_list:
        most_recents.append(six.next(gen))

    while True:
        if most_recents.count(most_recents[0]) == len(most_recents):
            # All our iterators agree
            yield most_recents[0]
            # Get the next
            for index, gen in enumerate(gen_list):
                most_recents[index] = six.next(gen)
        # Once this "else" exits, everything is == or > than max:
        else:
            maxval = max(most_recents)
            # Because our generators are ordered, and because this is an intersection,
            # we know there are no more possible matches once one generator runs out.
            for index, gen in enumerate(gen_list):
                while most_recents[index] < maxval:
                    most_recents[index] = six.next(gen)


def export(factory, id_list, scalar_names, output_type, output_file=None):
    """
    Export records and corresponding scalars.

    :param factory: The DAOFactory to use.
    :param id_list: The list of record ids to export.
    :param scalar_names: The list of scalars to output for each record.
    :param output_type: The type of output to export to. Acceptable values are:
                        csv
    :param output_file: The file to output. If None, then default to a
                        timestamped output.
    """
    LOGGER.info('Exporting to type %s.', output_type)
    LOGGER.debug('Exporting <id_list=%s, scalar_names=%s, output_type=%s, output_file=%s>.',
                 id_list, scalar_names, output_type, output_file)
    if not output_type == 'csv':
        msg = ('Given "{}" for output_type and it must be one of the '
               'following: csv'.format(output_type))
        LOGGER.error(msg)
        raise ValueError(msg)
    if not output_file:
        output_file = ('output_' +
                       (datetime.datetime.fromtimestamp(
                        time.time()).strftime('%Y-%m-%d_%H-%M-%S')) +
                       '.csv')
        LOGGER.debug('Using default output file: %s.', output_file)
    data_to_export = OrderedDict()
    record_dao = factory.createRecordDAO()
    for id in id_list:
        data_to_export[id] = record_dao.get_scalars(id=id,
                                                    scalar_names=scalar_names)
    _export_csv(data=data_to_export,
                scalar_names=scalar_names,
                output_file=output_file)


def _export_csv(data, scalar_names, output_file):
    """
    Export records and corresponding scalars to a csv file.

    :param data: The dictionary of record ids to list of scalars to export.
                 Use OrderedDict (as in export()) to preserve order.
    :param scalar_names: The list of scalars names to output. Used for header.
    :param output_file: The file to output.
    """
    LOGGER.debug('About to write data to csv file: %s', output_file)
    header = ['id'] + scalar_names
    with open(output_file, 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for run, dataset in data.items():
            # Each entry is a dict of scalars
            if dataset:
                writer.writerow([run] + [dataset[scalar]['value'] for scalar in scalar_names])


def parse_data_string(data_string):
    """
    Parse a string into a {name: DataRange} dict for use with data_query().

    Ex: "speed=(3,4] max_height=(3,4]" creates two DataRanges. They are both
    min exclusive, max inclusive, and have a range of 3.0 to 4.0. They are then
    paired up with their respective names and returned as:
    [("speed", range_1), ("max_height", range_2)]

    IMPORTANT CAVEATS: values passed in can't have quotes, equals signs, etc.
    Same conventions as python variable naming: som3cat is fine, cat=sp'm isn't.
    Should look something like "speed=[fast,faster] height=real_tall". In case
    your string looks like a number (ex: version=1.2.8 got updated to 1.3),
    **this will NOT work correctly** and it's time to revisit the function.

    :param data_string: A string of space-separated range descriptions

    :raises ValueError: if given a badly-formatted range, ex: '<foo>=,2]'

    :returns: a dict of {name: DataRange}.

    """
    # This code was lifted from parse_scalars() and only updated enough to avoid
    # breaking things; further refinement should be tackled in another PR.
    # Notable issues are outlined above as "IMPORTANT CAVEATS".

    LOGGER.debug('Parsing string <%s> into DataRange objects.', data_string)
    raw_data = filter(None, data_string.split(" "))
    clean_data = {}

    for entry in raw_data:
        components = entry.split("=")
        name = components[0]

        # Make sure scalar's of the form <foo>=<bar>
        if len(components) < 2 or len(components[1]) == 0:
            raise ValueError('Bad syntax for scalar \'{}\'.'.format(name))
        val_range = components[1].split(",")
        # Dummy DataRange as we can't have an empty range, will be set below.
        data_range = DataRange(float("-inf"), float("inf"))

        if len(val_range) == 1:
            val = val_range[0]
            try:
                val = float(val)
            except ValueError:
                pass  # It's a non-numeric string, we just keep going
            data_range.set_equal(val)
            clean_data[name] = data_range
        elif is_grouped_as_range(components[1]) and len(val_range) == 2:
            data_range.parse_min(val_range[0])
            data_range.parse_max(val_range[1])
            clean_data[name] = data_range
        else:
            raise ValueError('Bad specifier in range for {}'.format(name))

    return clean_data


def is_grouped_as_range(range_string):
    """
    Return whether a string, ex: (2,3], begins & ends in valid range-grouping characters.

    :param range_string: The string to check

    :returns: True if the string has valid range-grouping, else False
    """
    LOGGER.debug('Checking if the following has proper range characters: %s', range_string)
    open_identifier = ["[", "("]
    close_identifier = ["]", ")"]

    if len(range_string) < 2:
        return False
    if range_string[0] not in open_identifier or range_string[-1] not in close_identifier:
        return False
    return True


def sort_and_standardize_criteria(criteria_dict):
    """
    Given a dict of name: criteria, sort into lists by criteria type.

    If any simple equivalence criteria are found (x=5), convert them to DataRanges.

    :param criteria_dict: A dictionary of the form {name_1: criterion_1}
    :returns: A tuple of lists of the form (scalar_criteria, string_criteria,
              scalar_list_criteria, string_list_criteria). Each entry in each
              list is (name, datarange_criterion)
    :raises ValueError: if passed any criterion that isn't a valid number,
                        string, DataRange, or ListCriteria.
    """
    LOGGER.debug('Sorting and standardizing criteria: %s', criteria_dict)
    scalar_criteria = []
    string_criteria = []
    scalar_list_criteria = []
    string_list_criteria = []
    for data_name, criterion in criteria_dict.items():
        if isinstance(criterion, Real):
            scalar_criteria.append((data_name, DataRange(min=criterion,
                                                         max=criterion,
                                                         max_inclusive=True)))
        elif isinstance(criterion, DataRange) and criterion.is_numeric_range():
            scalar_criteria.append((data_name, criterion))
        elif isinstance(criterion, six.string_types):
            string_criteria.append((data_name, DataRange(min=criterion,
                                                         max=criterion,
                                                         max_inclusive=True)))
        elif isinstance(criterion, DataRange) and criterion.is_lexographic_range():
            string_criteria.append((data_name, criterion))
        elif isinstance(criterion, ListCriteria):
            if criterion.is_numeric:
                scalar_list_criteria.append((data_name, criterion))
            elif criterion.is_lexographic:
                string_list_criteria.append((data_name, criterion))
            else:
                raise ValueError("criteria must be a number, string, numerical"
                                 "or lexographic DataRange, or numerical or lexographic"
                                 "ListCriteria. Given a ListCriteria that is neither"
                                 "numerical nor lexographic: {}".format(criterion))
        else:
            # Probably a null range; we don't know what table to look in
            # While we may support this in the future, we don't now.
            # Might also be a dict or something else strange.
            raise ValueError("criteria must be a number, string, numerical"
                             "or lexographic DataRange, or numerical or lexographic"
                             "ListCriteria. Given {}:{}".format(data_name, criterion))
    return (scalar_criteria, string_criteria, scalar_list_criteria, string_list_criteria)


def create_file(path):
    """
    Check if a file exists.

    If it does not, creates an empty file with the given path. Will create
    directories that don't exist in the path.

    :param path: (string, req) The path to create.

    :raises OSError: This shouldn't happen, but unexpected OSErrors will get
        raised (we catch EEXist already).

    """
    LOGGER.debug('Creating new file: %s', path)
    if not os.path.exists(path):
        # Make directory
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as err:
            if err.errno == errno.EEXIST:
                LOGGER.error('Directory already created, or race condition? Check '
                             'path: %s', path)
            else:
                msg = 'Unexpected OSError: {}'.format(err)
                LOGGER.error(msg)
                raise OSError(msg)
        # Make file
        with open(path, 'a+') as f:
            f.close()


def get_example_path(relpath, suffix="-new",
                     example_dirs=["/collab/usr/gapps/wf/examples/",
                                   os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                    "../../examples/"))]):
    """
    Return the fully qualified path name for an example data store, raise exception if none.

    This function checks the paths listed in <example_dirs> for the file specified
    with <relpath>.

    If $SINA_TEST_KERNEL is set, it will initially append <suffix> to relpath's
    filename, ex foo/bar.txt becomes foo/bar<suffix>.txt. If it doesn't find
    anything, it reverts (so it looks for relpath both with and without the suffix).

    The order of example_dirs is important; as soon as something that matches is
    found, the function returns.

    :param relpath: The path, relative to the example_dirs, of the data store
    :param suffix: The test filename suffix
    :param example_dirs: A list of fully qualified paths to root directories
        containing example data
    :returns: The path to the appropriate example data store
    :raises ValueError: if an example data store file does not exist
    """
    LOGGER.debug("Retrieving example data store path: %s, %s, %s", relpath, suffix, example_dirs)

    dirs = [example_dirs] if isinstance(example_dirs, six.string_types) else example_dirs

    paths = [relpath]
    if os.getenv("SINA_TEST_KERNEL") is not None:
        base, ext = os.path.splitext(relpath)
        paths.insert(0, "{}{}{}".format(base, suffix, ext))

    filename = None
    for db_path in paths:
        for root in dirs:
            datastore = os.path.join(root, db_path)
            if os.path.isfile(datastore):
                filename = datastore
                break

    if filename is None:
        raise ValueError("No example data store found for {} in example dirs {}"
                         .format(relpath, example_dirs))

    return filename


def has_all(*args):
    """
    Create a ListCriteria representing the "ALL" operator.

    As an example, has_all("pineapple", "cheese") would match
    ["cheese", "pineapple"] or ["pineapple", "cheese", "pepperoni"], but not
    ["cheese"].

    :param args: The values the ListCriteria will represent. Can be either single values
                 (like "egg" or 12) or DataRanges. Every arg must represent the same
                 type of data, either scalars or strings.
    :returns: A ListCriteria object representing this criterion.
    """
    return ListCriteria(entries=args, operation="ALL")


def has_any(*args):
    """
    Create a ListCriteria representing the "ANY" operator.

    As an example, has_any("pineapple", "cheese") would match
    ["cheese", "pineapple"] or ["pineapple", "cheese", "pepperoni"] or
    ["cheese"], but not ["pepperoni"].

    :param args: The values the ListCriteria will represent. Can be either single values
                 (like "egg" or 12) or DataRanges. Every arg must represent the same
                 type of data, either scalars or strings.
    :returns: A ListCriteria object representing this criterion.
    """
    return ListCriteria(entries=args, operation="ANY")


def has_only(*args):
    """
    Create a ListCriteria representing the "ONLY" operator.

    As an example, has_only("pineapple", "cheese") would match
    ["cheese", "pineapple", "cheese"], but not ["pineapple", "cheese", "pepperoni"]
    or ["cheese"].

    :param args: The values the ListCriteria will represent. Can be either single values
                 (like "egg" or 12) or DataRanges. Every arg must represent the same
                 type of data, either scalars or strings.
    :returns: A ListCriteria object representing this criterion.
    """
    return ListCriteria(entries=args, operation="ONLY")


class ListCriteria(object):
    """
    Express some criteria a list datum must fulfill, such as "contains foo and bar".

    Supports the following types of operation:
    ANY: Passes if one of the entries is found.
    ALL: Passes if all the entries are found.
    ONLY: Passes if ONLY the entries are found, though there can be duplicates.

    Helper object. See has_any(), has_all(), and has_only() for more info. Used with
    data_query() in the backends.
    """

    def __init__(self, entries, operation):
        """
        Initialize ListCriteria with necessary info.

        :param entries: A tuple of entries the operation will be used with.
        :param operation: The operation the ListCriteria represents.
        """
        # The attributes on the next line are all set via properties.
        self._entries, self._operation, self._is_numeric, self._is_lexographic = [None]*4
        self.entries = entries
        self.operation = operation

    @property
    def entries(self):
        """
        Get the ListCriteria's tuple of entries.

        :returns: the ListCriteria's entries.
        """
        return self._entries

    @entries.setter
    def entries(self, entries):
        """
        Set the Listcriteria's entries.

        :param entries: The ListCriteria's entries

        :raises TypeError: if entries aren't a tuple.
        """
        if not isinstance(entries, tuple):
            raise TypeError("Entries must be expressed as a tuple, were {}."
                            .format(entries))
        self._validate_and_set_entries_and_type(entries)

    @property
    def operation(self):
        """
        Get the operation the ListCriteria represents.

        :returns: The ListCriteria's operation, a ListQueryOperation.
        """
        return self._operation

    @operation.setter
    def operation(self, operation):
        """
        Set the operation the ListCriteria represents.

        :param operation: A string representing the ListCriteria's operation
                          ("ANY", "ALL", or "ONLY") or a valid ListQueryOperation.
        """
        if not isinstance(operation, ListQueryOperation):
            self._operation = ListQueryOperation(operation)
        else:
            self._operation = operation

    @property
    def is_numeric(self):
        """
        Get whether the ListCriteria is numeric.

        A numeric ListCriteria's entries are all scalars or numeric DataRanges.
        A ListCriteria cannot be both numeric and lexographic.

        :returns: whether this ListCriteria is numeric.
        """
        return self._is_numeric

    @property
    def is_lexographic(self):
        """
        Get whether the ListCriteria is lexographic.

        A numeric ListCriteria's entries are all strings or lexographic DataRanges.
        A ListCriteria cannot be both lexographic and numeric.

        :returns: whether this ListCriteria is lexographic.
        """
        return self._is_lexographic

    def __repr__(self):
        """Return a comprehensive (debug) representation of a ListCriteria."""
        return ('ListCriteria <entries={}, operation={}>'
                .format(self.entries,
                        self.operation))

    def __str__(self):
        """Return a string representation of a ListCriteria."""
        return self.__repr__()

    def _validate_and_set_entries_and_type(self, entries):
        """
        Ensure entries are valid. If so, updates ListCriteria appropriately.

        :param entries: A tuple of entries the ListCriteria should represent.
        :raises TypeError: if not all entries are lexographic xor numeric,
                           or if there's no entries
        """
        if not entries:
            raise TypeError("Entries must be a tuple of strings/lexographic DataRanges, "
                            "or of scalars/numeric DataRanges, not empty")
        if all((isinstance(x, Real) or
                (isinstance(x, DataRange) and x.is_numeric_range()))
               for x in entries):
            self._is_numeric = True
            self._is_lexographic = False
            self._entries = entries
        elif all((isinstance(x, six.string_types) or
                  (isinstance(x, DataRange) and x.is_lexographic_range()))
                 for x in entries):
            self._is_numeric = False
            self._is_lexographic = True
            self._entries = entries
        else:
            raise TypeError("Entries must be only strings/lexographic DataRanges "
                            "or only scalars/numeric DataRanges.")


class DataRange(object):
    """
    Express a range some data must be within and provide parsing utility functions.

    By default, a DataRange is min inclusive and max exclusive. It can represent
    strings and real numbers (SQL can't handle imaginary numbers)
    """

    def __init__(self, min=None, max=None, min_inclusive=True, max_inclusive=False):
        """
        Initialize DataRange with necessary info.

        :params min: number that scalar is >= or >. None for negative
                          infinity
        :params min_inclusive: True if min inclusive (>=), False for
                                > only
        :params max: number that scalar is < or <=. None for positive
                infinity
        :params max_inclusive: True if max inclusive (<=), False for
                                 < only
        """
        self.min = min
        self.min_inclusive = min_inclusive
        self.max = max
        self.max_inclusive = max_inclusive
        self.validate_and_standardize_range()

    def __repr__(self):
        """Return a comprehensive (debug) representation of a DataRange."""
        return ('DataRange <min={}, min_inclusive={}, max={}, '
                'max_inclusive={}>'.format(self.min,
                                           self.min_inclusive,
                                           self.max,
                                           self.max_inclusive))

    def __str__(self):
        """Return a DataRange in range format ({x, y} [x, y}, {,y], etc.)."""
        return "{}{}, {}{}".format(("[" if self.min_inclusive else "("),
                                   (self.min if self.min_is_finite() else "-inf"),
                                   (self.max if self.max_is_finite() else "inf"),
                                   ("]" if self.max_inclusive else ")"))

    def __contains__(self, value):
        """
        Check whether a value falls within a DataRange.

        :param other: The value to check.
        """
        if self.min_is_finite():
            greater_than_min = value >= self.min if self.min_inclusive else value > self.min
        else:
            greater_than_min = True
        if self.max_is_finite():
            less_than_max = value <= self.max if self.max_inclusive else value < self.max
        else:
            less_than_max = True
        return less_than_max and greater_than_min

    def __eq__(self, other):
        """
        Check whether two DataRanges are equivalent.

        :param other: The object to compare against.
        """
        return(isinstance(other, DataRange) and self.__dict__ == other.__dict__)

    def is_numeric_range(self):
        """
        Return whether the DataRange describes a numeric range.

        We know that if one is a number, the other must be a number or None,
        because we perform validation when they're changed. If the other is
        None, it's still a numeric range, albeit open on one side
        (x<4 vs 3<x<4).
        """
        return (isinstance(self.min, Real) or isinstance(self.max, Real))

    def is_single_value(self):
        """Return whether the DataRange represents simple equivalence (foo=5)."""
        # This method is as simple as it is due to the validation; min
        # and max can't both be None, and they can't be equal but not inclusive.
        return self.min == self.max

    def max_is_finite(self):
        """
        Return whether the DataRange has a finite max bound.

        Used to clarify what code is checking for where DataRanges are
        involved, and to help avoid pitfalls with Python's "0 is False" behavior
        (if datarange.max).

        :returns: whether self.max is finite. If False, its upper bound is infinity.
        """
        return self.max is not None

    def min_is_finite(self):
        """
        Return whether the DataRange has finite min bound.

        :returns: whether self.min is finite. If False, its lower bound is negative infinity.
        """
        return self.min is not None

    def is_lexographic_range(self):
        """
        Return whether the DataRange describes a lexographic range.

        We know that if one is a string, the other must be a string or None,
        because we perform validation when they're changed. If the other is
        None, it's still a lexographic range, albeit open on one side
        (x<"dog" vs "cat"<x<"dog").
        """
        return (isinstance(self.min, six.string_types) or isinstance(self.max, six.string_types))

    def overlaps(self, other):
        """
        Return whether this DataRange and another overlap.

        :param other: Another DataRange to check against for overlap.
        :returns: Whether or not this DataRange and the other overlap.

        :raises TypeError: If trying to check DataRanges of mismatched type for overlap.
        """
        if not (self.is_numeric_range() == other.is_numeric_range()):
            # Comparing numbers and strings may give unexpected behavior. Conceptually
            # they *don't* overlap, but in Python they do; better to leave it to the user.
            raise TypeError("Only DataRanges of the same type (numeric or lexicographic)"
                            " can be tested for overlap.")
        # We standardize our logic by figuring out which is the "lesser" (leftmost on numberline)
        if not self.min_is_finite() or (other.min_is_finite() and self.min < other.min):
            lesser, greater = self, other
        else:
            lesser, greater = other, self
        return (lesser.max > greater.min or
                (lesser.max == greater.min and (lesser.max_inclusive or greater.min_inclusive)))

    def parse_min(self, min_range):
        """
        Parse the minimum half of a range, ex: the "[4" in "[4,2]".

        Sets the DataRange's minimum portion to be inclusive/not depending on
        the arg's min paren/bracket,  and its min number to be whatever's
        provided by the arg.

        :param str min_range: a string of the form '<range_end>[value]',
                               ex: '[4' or '(', that represents the min side
                               of a numerical range
        """
        LOGGER.debug('Setting min of range: %s', min_range)
        if not min_range[0] in ['(', '[']:
            raise ValueError("Bad inclusiveness specifier for range: {}",
                             format(min_range[0]))
        if len(min_range) > 1:
            self.min_inclusive = min_range[0] == '['

            min_arg = min_range[1:]
            try:
                self.min = float(min_arg)
            except ValueError:
                self.min = min_arg
            self.validate_and_standardize_range()

        else:
            # None represents negative infinity in range notation.
            self.min = None
            # Negative infinity can't be inclusive.
            self.min_inclusive = False

    def parse_max(self, max_range):
        """
        Parse the maximum half of a range, ex: the "2]" in "[4,2]".

        Sets the DataRange's maximum portion to be inclusive/not depending on
        the arg's max paren/bracket,  and its max number to be whatever's
        provided by the arg.

        :param str max_range: a string of the form '[value]<range_end>',
                                ex: '4)' or ']', that represents the max side
                                of a numerical range
        """
        LOGGER.debug('Setting max of range: %s', max_range)
        if not max_range[-1] in [')', ']']:
            raise ValueError("Bad inclusiveness specifier for range: {}",
                             format(max_range[-1]))
        if len(max_range) > 1:
            self.max_inclusive = max_range[-1] == ']'
            # We can take strings, but here we're already taking a string.
            # Thus we need to do a check: '"4"]' is passing us a string, but
            # '4]', despite being a string itself, is passing us an int
            max_arg = max_range[:-1]
            try:
                self.max = float(max_arg)
            except ValueError:
                self.max = max_arg
            self.validate_and_standardize_range()
        else:
            # None represents positive infinity in range notation.
            self.max = None
            # Positive infinity can't be inclusive
            self.max_inclusive = False

    def set_equal(self, val):
        """
        Set a DataRange equal to a single value while preserving notation.

        This is provided for the convenience case of testing exact equivalence
        (=5), allowing the user to just write =5 instead of =[5:5].

        :param val: The value (string or number) to set the DataRange to.
        """
        LOGGER.debug('Setting range equal to: %s', val)
        self.min = val
        self.max = val
        self.min_inclusive = True
        self.max_inclusive = True
        self.validate_and_standardize_range()

    def validate_and_standardize_range(self):
        """
        Ensure that members of a range are set to correct types.

        Raise exceptions if not.

        :raises ValueError: if given an impossible range, ex: [3,2]
        :raises TypeError: if the range has a component of the wrong type,
                           ex [2,[-1,-2]], or mismatched types ex [4, "4"]
        """
        # This method defines the assumptions we make about DataRanges. If you
        # change this logic, methods like is_single_value() need changed as well
        LOGGER.debug('Validating and standardizing range of: %s', self)
        if (not self.min_is_finite()) and (not self.max_is_finite()):
            raise ValueError("Null DataRange; min or max must be defined")
        try:
            # Case 1: min or max is number. Other must be number or None.
            if isinstance(self.min, Real) or isinstance(self.max, Real):
                self.min = float(self.min) if self.min_is_finite() else None
                self.max = float(self.max) if self.max_is_finite() else None
            # Case 2: neither min nor max is number. Both must be None or string
            elif (not isinstance(self.min, (six.string_types, type(None)) or
                  not isinstance(self.max, (six.string_types, type(None))))):
                raise ValueError
            # Note that both being None is a special case, since then we don't
            # know if what we're ultimately looking for is a number or string.
        except ValueError:
            msg = "Bad type for portion of range: {}".format(self)
            LOGGER.error(msg)
            raise TypeError(msg)  # TypeError, as ValueError is a bit broad

        if self.min_is_finite():
            min_gt_max = self.max_is_finite() and self.min > self.max
            max_eq_min = self.max_is_finite() and self.min == self.max
            impossible_range = max_eq_min and not (self.min_inclusive and self.max_inclusive)
            if min_gt_max or impossible_range:
                msg = "Bad range for data, min must be <= max: {}".format(self)
                LOGGER.error(msg)
                raise ValueError(msg)
