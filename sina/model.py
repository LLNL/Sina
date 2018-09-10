"""Contains toplevel, abstract objects mirroring the Mnoda schema."""

import json
import logging
import collections
import six

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
    a subtype. If you create a Record with one of these "reserved" types
    (i.e. "run") and try to ingest it, you'll get errors (unless you add
    the child's required fields by hand, but this will confuse is_valid()).

    If using a type reserved for one of Record's children, create an instance
    of that child.
    """

    def __init__(self, record_id, record_type, data=[], files=[],
                 user_defined={}):
        """
        Create Record with its id, type, and optional args.

        Currently, data and files are expected to be lists of dicts.
        Lists of strings (ex: ['{"name":"foo"}']) won't be read correctly.
        See the Mnoda section of the documentation for what data and
        files should contain, and try Record.is_valid(print_warnings=True)
        if you run into issues.

        :param record_id: The id of the record. Should be unique within a dataset
        :param record_type: The type of record. Some types are reserved for
                            children, see sina.model.RESERVED_TYPES
        :param data: A list of dicts representing the Record's data.
        :param files: A list of dicts representing the Record's files
        :param user_defined: A dictionary of additional miscellaneous data to
                             store, such as notes. The backend will not index on this.
        """
        self.raw = {}
        self.record_id = record_id
        self.record_type = record_type
        self.data = data
        self.files = files
        self.user_defined = user_defined

        is_valid, warnings = self._is_valid()
        if not is_valid:
            raise ValueError(warnings)

    @property
    def record_id(self):
        return self['record_id']

    @record_id.setter
    def record_id(self, record_id):
        self['record_id'] = record_id

    @property
    def record_type(self):
        return self['record_type']

    @record_type.setter
    def record_type(self, record_type):
        self['record_type'] = record_type

    @property
    def data(self):
        return self['data']

    @data.setter
    def data(self, data):
        self['data'] = data

    @property
    def files(self):
        return self['files']

    @files.setter
    def files(self, files):
        self['files'] = files

    @property
    def user_defined(self):
        return self['user_defined']

    @user_defined.setter
    def user_defined(self, user_defined):
        self['user_defined'] = user_defined

    def __getitem__(self, key):
        return self.raw[key]

    def __setitem__(self, key, value):
        self.raw[key] = value

    def __delitem__(self, key):
        del self.raw[key]

    def __repr__(self):
        """Return a string representation of a model Record."""
        return ('Model Record <record_id={}, record_type={}>'
                .format(self.record_id, self.record_type))

    def to_json(self):
        """
        Create a JSON string from a Record.

        The created string will not have a 'raw' field, to prevent recursion
        and redundancy. It should only be used with Record that weren't created
        from JSON in the first place.

        The reason we use this instead of json.loads(some_record) is the
        "type" and "id" fields (which have to be renamed in the object to
        avoid collision with Python keywords)

        :returns: A JSON string representing this Record
        """
        json_obj = {"id": self.record_id, "type": self.record_type}
        if self.data:
            json_obj["data"] = self.data
        if self.files:
            json_obj["files"] = self.files
        if self.user_defined:
            json_obj["user_defined"] = self.user_defined
        return json.dumps(json_obj)

    def _is_valid(self, print_warnings=False):
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
        # We should issue a warning if record_type is reserved and we are not
        # actually a reserved object. This check is removed for now because it
        # warrants significant code changes in sql/cass modules.

        # For files/data, we break immediately on finding any error--in
        # practice these lists can be thousands of entries long, in which case
        # the error is probably in an importer script (and so present in all
        # files/data) and doesn't warrant spamming the logger.
        if self.files:
            for entry in self.files:
                if not isinstance(entry, dict):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is not a dictionary. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if "uri" not in entry:
                    (warnings.append("At least one file entry belonging to "
                                     "Record {} is missing a uri. File: {}"
                                     .format(self.record_id, entry)))
                    break
                # Python2 and 3 compatible way of checking if the tags are
                # a list, tuple, etc (but not a string)
                if (entry.get("tags") and
                    (isinstance(entry.get("tags"), six.string_types) or
                     not isinstance(entry.get("tags"), collections.Sequence))):
                    (warnings.append("At least one file entry belonging to "
                                     "Record {} has a malformed tag list. File: {}"
                                     .format(self.record_id, entry)))
        if self.data:
            for entry in self.data:
                if not isinstance(entry, dict):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is not a dictionary. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if "name" not in entry:
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is missing a name. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if "value" not in entry:
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is missing a value. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if (entry.get("tags") and
                    (isinstance(entry.get("tags"), six.string_types) or
                     not isinstance(entry.get("tags"), collections.Sequence))):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} has a malformed tag list. Value: {}"
                                     .format(self.record_id, entry)))
        if self.raw:
            try:
                json.dumps(self.raw)
            except ValueError:
                (warnings.append("Record {}'s raw is invalid JSON.'"
                                 .format(self.record_id)))
        if self.user_defined and not isinstance(self.user_defined, dict):
            (warnings.append("Record {}'s user_defined section is not a "
                             "dictionary. User_defined: {}"
                             .format(self.record_id, self.user_defined)))
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

    def __init__(self, record_id, application,
                 user=None, version=None, user_defined=None,
                 data=None, files=None):
        """Create Run from Record info plus metadata."""
        super(Run, self).__init__(record_id=record_id,
                                  record_type="run",
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
        return('Model Run <record_id={}, application={}, user={}, version={}>'
               .format(self.record_id,
                       self.application,
                       self.user,
                       self.version))

    def to_json(self):
        """
        Create a JSON string from a Run.

        The created string will not have a 'raw' field, to prevent recursion
        and redundancy. It should only be used with Record that weren't created
        from JSON in the first place.

        The reason we use this instead of json.loads(some_record) is the
        "type" and "id" fields (which have to be renamed in the object to
        avoid collision with Python keywords)

        :returns: A JSON string representing this Run
        """
        json_obj = json.loads(super(Run, self).to_json())
        json_obj["application"] = self.application
        if self.user is not None:
            json_obj["user"] = self.user
        # checks 'is not None' because version 0 is falsey
        if self.version is not None:
            json_obj["version"] = self.version
        return json.dumps(json_obj)


def generate_record_from_json(json_input):
    """
    Generates a Record from the json input.

    :param json_input: A JSON representation of a Record.
    :raises: ValueError if given invalid json input.
    """
    LOGGER.debug('Generating record from json input: {}'.format(json_input))
    # Must create record first
    try:
        record = Record(record_id=json_input['id'],
                        record_type=json_input['type'],
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
    Generates a Run from the json input.

    :param json_input: A JSON representation of a Run.
    :raises: ValueError if given invalid json input.
    """
    LOGGER.debug('Generating run from json input: {}'.format(json_input))
    # Must create record first
    try:
        run = Run(record_id=json_input['id'],
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
