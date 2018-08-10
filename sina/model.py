"""Contains toplevel, abstract objects mirroring the Mnoda schema."""

import json
import logging
import collections

logging.basicConfig()
logger = logging.getLogger(__name__)
RESERVED_TYPES = ["run"]  # Types reserved by Record's children

# Python 3 renamed basestring, but 2 requires it here
try:
    basestring
except NameError:
    basestring = str


class Record(object):
    """
    A record is any arbitrary object we've chosen to store.

    A record is guaranteed to have exactly two things: an id and a type.
    Records may also have values and/or documents associated with them, as well
    as a "raw" (the JSON string it was created from, if applicable).

    There are subtypes of Records with additional field support, such as Runs.
    On ingestion, the "type" field determines whether the object is a Record or
    a subtype. If you create a Record with one of these "reserved" types
    (i.e. "run") and try to ingest it, you'll get errors (unless you add
    the child's required fields by hand, but this will confuse is_valid()).

    If using a type reserved for one of Record's children, create an instance
    of that child.
    """

    def __init__(self, record_id, record_type, raw=None, values=[], files=[], user_defined=None):
        """
        Create Record with its id, type, raw, and optional args.

        Currently, values and files are expected to be lists of dicts.
        Lists of strings (ex: ['{"name":"foo"}']) won't be read correctly.
        See the Mnoda section of the documentation for what values and
        files should contain, and try Record.is_valid(print_warnings=True)
        if you run into issues.

        :param record_id: The id of the record. Should be unique within a dataset
        :param record_type: The type of record. Some types are reserved for
                            children, see sina.model.RESERVED_TYPES
        :param raw: The raw JSON used to create this Record, if applicable
        :param values: A list of dicts representing the Record's values
        :param files: A list of dicts representing the Record's files
        :param user_defined: A dictionary of additional miscellaneous data to
                             store, such as notes. The backend will not index on this.
        """
        self.record_id = record_id
        self.record_type = record_type
        self.raw = raw
        self.values = values
        self.files = files
        self.user_defined = user_defined

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
        if self.values:
            json_obj["values"] = self.values
        if self.files:
            json_obj["files"] = self.files
        if self.user_defined:
            json_obj["user_defined"] = self.user_defined
        return json.dumps(json_obj)

    def is_valid(self, print_warnings=False):
        """Test whether a Record's members are formatted correctly.

        The ingester expects certain types to be reserved, and for values
        and files to follow a specific format. This method will describe any
        issues with a Record.

        :param print_warnings: if true, will print warnings. Warnings are
                                 passed to the logger only by default.
        :returns: true if valid for ingestion, else false.
        """
        warnings = []
        if self.record_type in RESERVED_TYPES and type(self) is Record:
            (warnings.append("Record {} is using a type reserved for child: {}"
                             .format(self.record_id, self.record_type)))
        # For files/values, we break immediately on finding any error--in
        # practice these lists can be thousands of entries long, in which case
        # the error is probably in an importer script (and so present in all
        # files/values) and doesn't warrant spamming the logger.
        if self.files:
            for entry in self.files:
                if not isinstance(entry, dict):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is not a dictionary. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if not entry.get("uri"):
                    (warnings.append("At least one file entry belonging to "
                                     "Record {} is missing a uri. File: {}"
                                     .format(self.record_id, entry)))
                    break
                # Python2 and 3 compatible way of checking if the tags are
                # a list, tuple, etc (but not a string)
                if (entry.get("tags") and
                    (isinstance(entry.get("tags"), basestring) or
                     not isinstance(entry.get("tags"), collections.Sequence))):
                    (warnings.append("At least one file entry belonging to "
                                     "Record {} has a malformed tag list. File: {}"
                                     .format(self.record_id, entry)))
        if self.values:
            for entry in self.values:
                if not isinstance(entry, dict):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is not a dictionary. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if not entry.get("name"):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is missing a name. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if not entry.get("value"):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} is missing a value. Value: {}"
                                     .format(self.record_id, entry)))
                    break
                if (entry.get("tags") and
                    (isinstance(entry.get("tags"), basestring) or
                     not isinstance(entry.get("tags"), collections.Sequence))):
                    (warnings.append("At least one value entry belonging to "
                                     "Record {} has a malformed tag list. Value: {}"
                                     .format(self.record_id, entry)))
        if self.raw:
            try:
                json.loads(self.raw)
            except ValueError:
                (warnings.append("Record {}'s raw is invalid JSON.'"
                                 .format(self.record_id)))
        if self.user_defined and not isinstance(self.user_defined, dict):
            (warnings.append("Record {}'s user_defined section is not a "
                             "dictionary. User_defined: {}"
                             .format(self.user_defined, self.user_defined)))
        if warnings:
            warnstring = "\n".join(warnings)
            if print_warnings:
                print(warnstring)
            logger.warning(warnstring)
            return False
        return True


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

    def __init__(self, record_id, application, raw=None,
                 user=None, version=None, user_defined=None,
                 values=None, files=None):
        """Create Run from Record info plus metadata."""
        super(Run, self).__init__(record_id=record_id,
                                  record_type="run",
                                  raw=raw,
                                  user_defined=user_defined,
                                  values=values,
                                  files=files)
        self.application = application
        self.user = user
        self.version = version

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
