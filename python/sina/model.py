"""Contains toplevel, abstract objects mirroring the Sina schema."""
from __future__ import print_function
import json
import logging
import collections
import numbers

import six

logging.basicConfig()
LOGGER = logging.getLogger(__name__)
RESERVED_TYPES = ["run"]  # Types reserved by Record's children


# Disable redefined-builtin, invalid-name due to ubiquitous use of id and type
# pylint: disable=invalid-name,redefined-builtin

# We don't mind the high instance attribute count since this is essentially
# a reflection of our schema.
class Record(object):  # pylint: disable=too-many-instance-attributes
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

    # Disable the pylint check if and until the team decides to refactor the code
    def __init__(self, id, type, data=None,  # pylint: disable=too-many-arguments
                 curve_sets=None, files=None, user_defined=None):
        """
        Create Record with its id, type, and optional args.

        Currently, data and files are expected to be lists of dicts.
        Lists of strings (ex: ['{"name":"foo"}']) won't be read correctly.
        See the Sina schema section of the documentation for what data and
        files should contain.

        :param id: The id of the record. Should be unique within a dataset
        :param type: The type of record. Some types are reserved for
                            children, see sina.model.RESERVED_TYPES
        :param data: A dict of dicts representing the Record's data.
        :param curve_sets: A dict of dicts representing the Record's curve sets.
        :param files: A list of dicts representing the Record's files
        :param user_defined: A dictionary of additional miscellaneous data to
                             store, such as notes. The backend will not index on this.
        """
        # We store curve names specially so we don't need to loop through the
        # curve sets every time a piece of data is added.
        self.curve_names = set()

        self.raw = {}
        # Items in this block are going to raw behind the scenes (see __setattr__)
        self.id = id
        self.type = type
        self.data = data if data else {}
        self.curve_sets = curve_sets if curve_sets else {}
        self.files = files if files else {}
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
        if self.curve_names.intersection(data.keys()):
            msg = ("Record {} has overlapping curve and data entries. Make sure "
                   "you haven't duplicated your curve values into record.data. "
                   "Overlapping entries: {}"
                   .format(self.id, self.curve_names.intersection(self.data.keys())))
            raise ValueError(msg)
        self['data'] = data

    @property
    def curve_sets(self):
        """Get or set the Record's curve dictionary."""
        return self['curve_sets']

    @curve_sets.setter
    def curve_sets(self, curve_sets):
        """
        Set the Record's curve sets to a new dict of curve sets.

        This only works for rec.curve_sets = {"curveset_1" ...}. Indexing in
        won't trigger it.
        """
        names = self._find_curve_names_and_collisions(curve_sets)
        self['curve_sets'] = curve_sets
        self.curve_names = names

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

    def add_data(self, name, value, units=None, tags=None):
        """
        Add a data entry to a Record.

        Will throw an error if that datum is already part of the Record.

        :param name: The name describing the data (ex: "direction", "volume", "time")
        :param value: The data's value (ex: "northwest", 12, [0, 1, 3, 6])
        :param units: Units for the value. Optional (ex: "cm^3", "seconds")
        :param tags: List of tags describing this data. Optional (ex: ["inputs", "opt"])

        :raises ValueError: if a datum with that name is already part of the record.
        """
        if name in self.data:
            raise ValueError('Duplicate datum: "{}" is already an entry in Record "{}".'
                             .format(name, self.id))
        if name in self.curve_names:
            raise ValueError('Name collision: "{}" is already the name of a '
                             'curve entry in Record "{}"'.format(name, self.id))
        else:
            self.set_data(name, value, units, tags)

    def set_data(self, name, value, units=None, tags=None):
        """
        Set a data entry for a Record.

        If that datum doesn't exist, add it. If it does, update it.

        :param name: The name describing the data (ex: "direction", "volume", "time")
        :param value: The data's value (ex: "northwest", 12, [0, 1, 3, 6])
        :param units: Units for the value. Optional (ex: "cm^3", "seconds")
        :param tags: List of tags describing this data. Optional (ex: ["inputs", "opt"])
        """
        datum = {"value": value}
        if units is not None:
            datum["units"] = units
        if tags is not None:
            datum["tags"] = tags
        self.data[name] = datum

    def add_file(self, uri, mimetype=None, tags=None):
        """
        Add file info to a Record.

        Will throw an error if a file with that uri is already recorded in the Record.

        :param uri: The uri that uniquely describes the file. (ex: "/g/g10/doe/foo.txt")
        :param mimetype: The mimetype of the file. Optional (ex: "text/html")
        :param tags: List of tags describing this file. Optional (ex: ["post-processing"])

        :raises ValueError: if a file with that uri is already recorded in the Record.
        """
        if uri in self.files:
            raise ValueError('Duplicate file: "{}" is already a file in Record "{}".'
                             .format(uri, self.id))
        else:
            self.set_file(uri, mimetype, tags)

    def set_file(self, uri, mimetype=None, tags=None):
        """
        Set a file's info for a Record.

        If that file doesn't exist, add its info. If it does, update it.

        :param uri: The uri that uniquely describes the file. (ex: "/g/g10/doe/foo.txt")
        :param mimetype: The mimetype of the file. Optional (ex: "text/html")
        :param tags: List of tags describing this file. Optional (ex: ["post-processing"])
        """
        file_info = {}
        if mimetype is not None:
            file_info["mimetype"] = mimetype
        if tags is not None:
            file_info["tags"] = tags
        self.files[uri] = file_info

    def to_json(self):
        """
        Create a JSON string from a Record.

        :returns: A JSON string representing this Record
        """
        return json.dumps(self.raw)

    # Disable the pylint check if and until the team decides to refactor the code
    def is_valid(self, print_warnings=None):  # pylint: disable=too-many-branches
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
        for file_info in self.files.values():
            if not isinstance(file_info, dict):
                (warnings.append("At least one file entry belonging to "
                                 "Record {} is not a dictionary. Value: {}"
                                 .format(self.id, file_info)))
                break
            # Python2 and 3 compatible way of checking if the tags are
            # a list, tuple, etc (but not a string)
            if (file_info.get("tags") and
                    (isinstance(file_info.get("tags"), six.string_types) or
                     not isinstance(file_info.get("tags"), collections.Sequence))):
                (warnings.append("At least one file entry belonging to "
                                 "Record {} has a malformed tag list. File: {}"
                                 .format(self.id, file_info)))

        if not isinstance(self.data, dict):
            (warnings.append("Record {}'s data field must be a dictionary!"
                             .format(self.id)))
        else:
            # We have to do an extra check for collisions in case of
            # record["data"] usage.
            data_names = set(self.data.keys())
            if data_names.intersection(self.curve_names):
                (warnings.append("Data and curve name overlap: {}"
                                 .format(data_names.intersection(self.curve_names))))
            for entry in self.data:
                # Check data entry is a dictionary
                if not isinstance(self.data[entry], dict):
                    (warnings.append("At least one data entry belonging to "
                                     "Record {} is not a dictionary. "
                                     "Value: {}".format(self.id, entry)))
                    break
                if "value" not in self.data[entry]:
                    (warnings.append("At least one data entry belonging "
                                     "to Record {} is missing a value. "
                                     "Value: {}".format(self.id, entry)))
                    break
                if isinstance(self.data[entry]['value'], list):
                    try:
                        (validated_list,
                         scalar_index,
                         string_index) = _is_valid_list(
                             list_of_data=self.data[entry]["value"])
                    except ValueError as context:
                        warnings.append(str(context))
                        break
                    if not validated_list:
                        (warnings.append(
                            "A data entry may not have a list of different types. "
                            "They must all be scalars or all strings. Check "
                            "indicies: {}, {}".format(scalar_index, string_index)))
                        break
                if (self.data[entry].get("tags") and
                        (isinstance(self.data[entry].get("tags"),
                                    six.string_types) or
                         not isinstance(self.data[entry].get("tags"),
                                        collections.Sequence))):
                    (warnings.append("At least one value entry belonging "
                                     "to Record {} has a malformed tag "
                                     "list. Value: {}".format(self.id, entry)))
        try:
            json.dumps(self.raw)
        except ValueError:
            (warnings.append("Record {}'s raw is invalid JSON.'".format(self.id)))
        if not isinstance(self.user_defined, dict):
            (warnings.append("Record {}'s user_defined section is not a "
                             "dictionary. User_defined: {}".format(self.id, self.user_defined)))
        if warnings:
            warnstring = "\n".join(warnings)
            if print_warnings:
                print(warnstring)
            LOGGER.warning(warnstring)
            return False, warnings
        return True, warnings

    def _find_curve_names_and_collisions(self, new_curves):
        """
        Add names the curve name set if they're not collisions.

        This is used to check datum name collisions.

        :returns: A set of curve names
        :raises: ValueError if any of the curve names are already datum names.
        """
        new_names = set()
        collision_names = set()
        for entry in new_curves.values():
            for subcategory in ["independent", "dependent"]:
                for name in entry[subcategory].keys():
                    if name in self.data:
                        collision_names.add(name)
                    new_names.add(name)
        if collision_names:
            msg = ("Record {} has overlapping curve and data entries. Make sure "
                   "you haven't duplicated your curve values into record.data. "
                   "Overlapping entries: {}")
            raise ValueError(msg.format(self.id, collision_names))
        return new_names


# Disable pylint check to if and until the team decides to address the issue
class Relationship(object):  # pylint: disable=too-few-public-methods
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

    def to_json_dict(self):
        """
        Create an object ready to dump as JSON.

        Relationship's internal names don't match the schema (ex: we call object object_id to
        avoid overwriting Python's "object".) This performs the necessary name-swaps.

        You probably want to use to_json().

        :return: A dictionary representing the relationship, ready to dump.
        """
        return {"subject": self.subject_id, "predicate": self.predicate, "object": self.object_id}

    def to_json(self):
        """
        Create a JSON string from a Relationship.

        :returns: A JSON string representing this Relationship
        """
        return json.dumps(self.to_json_dict())


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

    def __init__(self, id, application,  # pylint: disable=too-many-arguments
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
        """Return the Run's application."""
        return self['application']

    @application.setter
    def application(self, application):
        """Set the Run's application."""
        self['application'] = application

    @property
    def user(self):
        """Return the Run's user."""
        return self['user']

    @user.setter
    def user(self, user):
        """Set the Run's user."""
        self['user'] = user

    @property
    def version(self):
        """Return the Run's version."""
        return self['version']

    @version.setter
    def version(self, version):
        """Set the Run's version."""
        self['version'] = version

    def __repr__(self):
        """Return a string representation of a model Run."""
        return('Model Run <id={}, application={}, user={}, version={}>'
               .format(self.id,
                       self.application,
                       self.user,
                       self.version))


def _is_valid_list(list_of_data):
    """
    Check if a list of data is valid.

    Validity means that all entries in the list are either strings or all
    are scalars.

    :param list_of_data: The list of data to check is valid.
    :returns: A Tuple consisting of a Boolean and two Integers. The Boolean
    is True if the list is valid, False otherwise. If False, the two
    Integers are two indexes of differing types of values (the first being
    an index of a scalar and the second being a index of a string). If True
    they are None.
    """
    LOGGER.debug('Checking if list of length %i is valid.', len(list_of_data))
    is_scalar = False
    is_string = False
    latest_scalar = None
    latest_string = None
    for index, list_entry in enumerate(list_of_data):
        if isinstance(list_entry, numbers.Real):
            latest_scalar = index
            is_scalar = True
        elif isinstance(list_entry, six.string_types):
            latest_string = index
            is_string = True
        else:
            raise ValueError("List of data contains entry that isn't a "
                             "string or scalar. value: {}, type: {}, index:"
                             " {}.".format(list_entry, type(list_entry),
                                           index))
        if is_scalar and is_string:
            LOGGER.debug('Found invalid list.')
            return (False, latest_scalar, latest_string)
    return (True, None, None)


def generate_record_from_json(json_input):
    """
    Generate a Record from the json input.

    :param json_input: A JSON representation of a Record.
    :raises: ValueError if given invalid json input.
    """
    LOGGER.debug('Generating record from json input: %s', json_input)
    # Must create record first
    try:
        record = Record(id=json_input['id'],
                        type=json_input['type'],
                        user_defined=json_input.get('user_defined'),
                        data=json_input.get('data'),
                        curve_sets=json_input.get('curve_sets'),
                        files=json_input.get('files'))
    except KeyError as context:
        msg = 'Missing required key <{}>.'.format(context)
        LOGGER.error(msg)
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
    LOGGER.debug('Generating run from json input: %s', json_input)
    # Programatically-created Records
    try:
        run = Run(id=json_input['id'],
                  user=json_input.get('user'),
                  user_defined=json_input.get('user_defined'),
                  version=json_input.get('version'),
                  application=json_input['application'],
                  data=json_input.get('data'),
                  files=json_input.get('files'))
    except KeyError as context:
        msg = 'Missing required key <{}>.'.format(context)
        LOGGER.error(msg)
        raise ValueError(msg)
    # Then set raw to json_input to grab any additional information.
    run.raw.update({key: val for key, val in json_input.items()
                    if key not in ['id', 'user', 'user_defined', 'version',
                                   'type', 'application', 'data', 'files']})
    return run


def convert_record_to_run(record):
    """
    Build a Run using a Record and run metadata found in the Record's raw.

    Given a Record with all the characteristics of a Run (type is "run",
    "application" field set, etc.), use the Record's raw data to build a
    Run object instead.

    :param record: A Record object to build the Run from.
    :returns: A Run representing the Record plus metadata.
    :raises ValueError: if given a Record that can't be converted to a Run.
    """
    LOGGER.debug('Converting %s to run.', record)
    if record.type == 'run':
        return generate_run_from_json(json_input=record.raw)
    else:
        msg = ('Record must be of subtype Run to convert to Run. Given '
               '{}.'.format(record.id))
        LOGGER.warn(msg)
        raise ValueError(msg)
