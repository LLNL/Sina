"""Contains toplevel, abstract objects mirroring the Mnoda schema."""

import json
import logging
import collections
import six
import os

import deepdiff
from pprint import pprint
from texttable import Texttable

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
RESERVED_TYPES = ["run"]  # Types reserved by Record's children


class Record(object):
    """
    A record is any arbitrary object we've chosen to store.

    A record is guaranteed to have exactly two things: an id and a type.
    Records may also have data and/or documents associated with them.

    There are subtypes of Records with additional field support, such as Runs.
    On ingestion, the "type" field determines whether the object is a Record or
    a subtype.

    If using a type reserved for one of Record's children, create an instance
    of that child.
    """

    def __init__(self, id, type, data=None, files=None, user_defined=None):
        """
        Create Record with its id, type, and optional args.

        Currently, data and files are expected to be lists of dicts.
        Lists of strings (ex: ['{"name":"foo"}']) won't be read correctly.
        See the Mnoda section of the documentation for what data and
        files should contain.

        :param id: The id of the record. Should be unique within a dataset
        :param type: The type of record. Some types are reserved for
                            children, see sina.model.RESERVED_TYPES
        :param data: A dict of dicts representing the Record's data.
        :param files: A list of dicts representing the Record's files
        :param user_defined: A dictionary of additional miscellaneous data to
                             store, such as notes. The backend will not index on this.
        """
        self.raw = {}
        # Note these are all going to raw behind the scenes (see __setattr__)
        self.id = id
        self.type = type
        self.data = data if data else {}
        self.files = files if files else []
        self.user_defined = user_defined if user_defined else {}

    @property
    def id(self):
        """Get or set the Record's id."""
        return self['id']

    @id.setter
    def id(self, id):
        self['id'] = id

    @property
    def type(self):
        """Get or set the Record's type."""
        return self['type']

    @type.setter
    def type(self, type):
        self['type'] = type

    @property
    def data(self):
        """Get or set the Record's data dictionary."""
        return self['data']

    @data.setter
    def data(self, data):
        self['data'] = data

    @property
    def files(self):
        """Get or set the Record's file list."""
        return self['files']

    @files.setter
    def files(self, files):
        self['files'] = files

    @property
    def user_defined(self):
        """Get or set the Record's user-defined dictionary."""
        return self['user_defined']

    @user_defined.setter
    def user_defined(self, user_defined):
        self['user_defined'] = user_defined

    def __getitem__(self, key):
        """
        Get the entry in this record with the given key.

        A Record object mimics a dictionary in how it's accessed, with the data
        it represents available within a dictionary called "raw". Here,
        we reroute ex: foo = my_rec["data"]["spam"] to go through this raw dictionary.
        Essentially, it becomes foo = my_rec.raw["data"]["spam"].
        """
        return self.raw[key]

    def __setitem__(self, key, value):
        """
        Set the entry in this record with the given key.

        A Record object mimics a dictionary in how it's accessed, with the data
        it represents available within a dictionary called "raw". Here,
        we reroute ex: my_rec["data"]["spam"] = 2 to go through this raw dictionary.
        Essentially, it becomes my_rec.raw["data"]["spam"] = 2.
        """
        self.raw[key] = value

    def __delitem__(self, key):
        """
        Delete the entry in this record with the given key.

        A Record object mimics a dictionary in how it's accessed, with the data
        it represents available within a dictionary called "raw". Here, we
        reroute ex: del my_rec["data"]["spam"] to go through this raw dictionary.
        Essentially, it becomes del my_rec.raw["data"]["spam"]
        """
        del self.raw[key]

    def __repr__(self):
        """Return a string representation of a model Record."""
        return ('Model Record <id={}, type={}>'
                .format(self.id, self.type))

    def to_json(self):
        """
        Create a JSON string from a Record.

        :returns: A JSON string representing this Record
        """
        return json.dumps(self.raw)

    def is_valid(self, print_warnings=None):
        """Test whether a Record's members are formatted correctly.

        The ingester expects certain types to be reserved, and for data
        and files to follow a specific format. This method will describe any
        issues with a Record.

        :param print_warnings: if true, will print warnings. Warnings are
                                 passed to the logger only by default.
        :returns: A tuple containing true or false if valid for ingestion and
                  a list of warnings.
        """
        warnings = []
        # We should issue a warning if type is reserved and we are not
        # actually a reserved object. This check is removed for now because it
        # warrants significant code changes in sql/cass modules.

        # For files/data, we break immediately on finding any error--in
        # practice these lists can be thousands of entries long, in which case
        # the error is probably in an importer script (and so present in all
        # files/data) and doesn't warrant spamming the logger.
        for entry in self.files:
            if not isinstance(entry, dict):
                (warnings.append("At least one file entry belonging to "
                                 "Record {} is not a dictionary. Value: {}"
                                 .format(self.id, entry)))
                break
            if "uri" not in entry:
                (warnings.append("At least one file entry belonging to "
                                 "Record {} is missing a uri. File: {}"
                                 .format(self.id, entry)))
                break
            # Python2 and 3 compatible way of checking if the tags are
            # a list, tuple, etc (but not a string)
            if (entry.get("tags") and
                (isinstance(entry.get("tags"), six.string_types) or
                 not isinstance(entry.get("tags"), collections.Sequence))):
                (warnings.append("At least one file entry belonging to "
                                 "Record {} has a malformed tag list. File: {}"
                                 .format(self.id, entry)))

        if not isinstance(self.data, dict):
            (warnings.append("Record {}'s data field must be a dictionary!"
                             .format(self.id)))
        else:
            for entry in self.data:
                if not isinstance(self.data[entry], dict):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is not a dictionary. Value: {}"
                                     .format(self.id, entry)))
                    break
                if "value" not in self.data[entry]:
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is missing a value. Value: {}"
                                     .format(self.id, entry)))
                    break
                if (self.data[entry].get("tags") and
                    (isinstance(self.data[entry].get("tags"), six.string_types) or
                     not isinstance(self.data[entry].get("tags"), collections.Sequence))):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} has a malformed tag list. Value: {}"
                                     .format(self.id, entry)))
        try:
            json.dumps(self.raw)
        except ValueError:
            (warnings.append("Record {}'s raw is invalid JSON.'"
                             .format(self.id)))
        if not isinstance(self.user_defined, dict):
            (warnings.append("Record {}'s user_defined section is not a "
                             "dictionary. User_defined: {}"
                             .format(self.id, self.user_defined)))
        if warnings:
            warnstring = "\n".join(warnings)
            if print_warnings:
                print(warnstring)
            LOGGER.warning(warnstring)
            return False, warnings
        return True, warnings


class Relationship(object):
    """
    A Relationship is a triple describing the relationship between two objects.

    Every relationship has exactly three things: the id of its object, the id
    of its subject, and the predicate describing their relationship. A
    Relationship translates in English to:

    <subject> <predicate> <object>, ex:

    Task142 contains Run6249.
    """

    def __init__(self, object_id, subject_id, predicate):
        """Create Relationship from triple info."""
        self.object_id = object_id
        self.subject_id = subject_id
        self.predicate = predicate

    def __repr__(self):
        """Return a string representation of a model Relationship."""
        return ('Model Relationship <object_id={}, subject_id={}, predicate={}>'
                .format(self.object_id, self.subject_id, self.predicate))


class Run(Record):
    """
    A Run is a Record subtype representing one 'finalized' run of some code.

    More precisely, a run represents a single set of inputs, their resulting
    outputs, and some amount of metadata. Outputs include scalars and
    documents. Metadata includes things like the application that generated the
    run. Runs have several special types of metadata (which are tracked as
    instance attributes), and hold additional, miscellaneous data in
    'user_defined'.
    """

    def __init__(self, id, application,
                 user=None, version=None, user_defined=None,
                 data=None, files=None):
        """Create Run from Record info plus metadata."""
        super(Run, self).__init__(id=id,
                                  type="run",
                                  user_defined=user_defined,
                                  data=data,
                                  files=files)
        self.application = application
        self.user = user
        self.version = version

    @property
    def application(self):
        return self['application']

    @application.setter
    def application(self, application):
        self['application'] = application

    @property
    def user(self):
        return self['user']

    @user.setter
    def user(self, user):
        self['user'] = user

    @property
    def version(self):
        return self['version']

    @version.setter
    def version(self, version):
        self['version'] = version

    def __repr__(self):
        """Return a string representation of a model Run."""
        return('Model Run <id={}, application={}, user={}, version={}>'
               .format(self.id,
                       self.application,
                       self.user,
                       self.version))


def generate_record_from_json(json_input):
    """
    Generate a Record from the json input.

    :param json_input: A JSON representation of a Record.
    :raises: ValueError if given invalid json input.
    """
    LOGGER.debug('Generating record from json input: {}'.format(json_input))
    # Must create record first
    try:
        record = Record(id=json_input['id'],
                        type=json_input['type'],
                        user_defined=json_input.get('user_defined'),
                        data=json_input.get('data'),
                        files=json_input.get('files'))
    except KeyError as e:
        msg = 'Missing required key <{}>.'.format(e)
        LOGGER.warn(msg)
        raise ValueError(msg)
    # Then set raw to json_input to grab any additional information.
    record.raw.update({key: val for key, val in json_input.items()
                      if key not in ['id', 'type', 'user_defined', 'data',
                                     'files']})
    return record


def generate_run_from_json(json_input):
    """
    Generate a Run from the json input.

    :param json_input: A JSON representation of a Run.
    :raises: ValueError if given invalid json input.
    """
    LOGGER.debug('Generating run from json input: {}'.format(json_input))
    # Programatically-created Records
    try:
        print(json_input)
        run = Run(id=json_input['id'],
                  user=json_input.get('user'),
                  user_defined=json_input.get('user_defined'),
                  version=json_input.get('version'),
                  application=json_input['application'],
                  data=json_input.get('data'),
                  files=json_input.get('files'))
    except KeyError as e:
        msg = 'Missing required key <{}>.'.format(e)
        LOGGER.warn(msg)
        raise ValueError(msg)
    # Then set raw to json_input to grab any additional information.
    run.raw.update({key: val for key, val in json_input.items()
                    if key not in ['id', 'user', 'user_defined', 'version',
                                   'type', 'application', 'data', 'files']})
    return run


def compare_records(record_one,
                    record_two,
                    ignore_order=True,
                    report_repetition=False,
                    significant_digits=None,
                    verbose_level=2,
                    exclude_paths=[],
                    exclude_types=[],
                    view='tree'):
    """
    Given two records, compare them.

    A comparison of two records consists of the following: Reporting any
    differences between their keys and reporting any differences between
    the values of the keys that are in both records.

    :param record_one: The first record object to compare.
    :param record_two: The second record object to compare.
    :param ignore_order: boolean, default True. Ignores orders for
                         iterables.
    :param report_repetition:  boolean, default False. Reports repetitions
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
    :param view: string, default 'text'. Support 'text' or 'tree'. Text is
                 the regular output. Tree allows you to traverse through
                 the tree of the changed items.
    :returns: A DeepDiff object.
    """
    LOGGER.debug('Diffing records: {} and {}.'.format(record_one, record_two))
    return deepdiff.DeepDiff(record_one.raw,
                             record_two.raw,
                             ignore_order=ignore_order,
                             report_repetition=report_repetition,
                             significant_digits=significant_digits,
                             verbose_level=verbose_level,
                             exclude_paths=exclude_paths,
                             exclude_types=exclude_types,
                             view=view)


def pprint_deep_diff(deep_diff, id_one, id_two):
    """
    Pretty print a DeepDiff object that represents a Record.

    :param deep_diff: The DeepDiff object to pretty print.
    """
    titles = ['key', id_one, id_two]
    values_changed = (list(zip(deep_diff['values_changed']))
                      if 'values_changed' in deep_diff else [])
    type_changes = (list(zip(deep_diff['type_changes']))
                    if 'type_changes' in deep_diff else [])
    iterable_item_removed = (list(zip(deep_diff['iterable_item_removed']))
                             if 'iterable_item_removed' in deep_diff else [])
    iterable_item_added = (list(zip(deep_diff['iterable_item_added']))
                           if 'iterable_item_added' in deep_diff else [])
    dict_item_removed = (list(zip(deep_diff['dictionary_item_removed']))
                         if 'dictionary_item_removed' in deep_diff else [])
    dict_item_added = (list(zip(deep_diff['dictionary_item_added']))
                       if 'dictionary_item_added' in deep_diff else [])
    set_item_added = (list(zip(deep_diff['set_item_added']))
                      if 'set_item_added' in deep_diff else [])
    set_item_removed = (list(zip(deep_diff['set_item_removed']))
                        if 'set_item_removed' in deep_diff else [])
    attribute_added = (list(zip(deep_diff['attribute_added']))
                       if 'attribute_added' in deep_diff else [])
    attribute_removed = (list(zip(deep_diff['attribute_removed']))
                         if 'attribute_removed' in deep_diff else [])
    repitition_change = (list(zip(deep_diff['repetition_change']))
                         if 'repetition_change' in deep_diff else [])
    data = (values_changed +
            type_changes +
            iterable_item_removed +
            iterable_item_added +
            dict_item_removed +
            dict_item_added +
            set_item_added +
            set_item_removed +
            attribute_added +
            attribute_removed +
            repitition_change)
    data_list = [titles]
    for d in data:
        key = d[0].path().strip('root')
        id_one_output = d[0].t1
        id_two_output = d[0].t2
        data_list.append([key, id_one_output, id_two_output])
    table = Texttable()
    table.set_cols_align(['c', 'c', 'c'])
    table.set_cols_valign(['m', 'm', 'm'])
    table.add_rows(data_list)
    print(table.draw() + '\n')
