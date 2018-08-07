"""Contains toplevel, abstract objects mirroring the Mnoda schema."""


class Record(object):
    """
    A record is any arbitrary object we've chosen to store.

    A record is guaranteed exactly three things: an id, a type, and the raw
    version of its contents (a JSON object). Depending on
    its type, a record might also be something else (ex: a Run). Records may
    also have values and/or documents associated with them.
    """

    def __init__(self, record_id, record_type, raw, values=None, files=None):
        """Create Record with its id, type, raw, and optional args."""
        self.record_id = record_id
        self.record_type = record_type
        self.raw = raw
        self.values = values
        self.files = files

    def __repr__(self):
        """Return a string representation of a model Record."""
        return ('Model Record <record_id={}, record_type={}>'
                .format(self.record_id, self.record_type))


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
                 user=None, user_defined=None, version=None,
                 values=None, files=None):
        """Create Run from Record info plus metadata."""
        super(Run, self).__init__(record_id=record_id,
                                  record_type="run",
                                  raw=raw,
                                  values=values,
                                  files=files)
        self.application = application
        self.user = user
        self.user_defined = user_defined
        self.version = version

    def __repr__(self):
        """Return a string representation of a model Run."""
        return('Model Run <record_id={}, application={}, user={}, version={}>'
               .format(self.record_id,
                       self.application,
                       self.user,
                       self.version))
