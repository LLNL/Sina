"""SQLAlchemy implementations of Mnoda objects."""

from sqlalchemy import (Column, ForeignKey, String, Text, Float, Integer)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Index

Base = declarative_base()


class Relationship(Base):
    """
    Implementation of Relationship table.

    Stores subject/object/predicate triple relationships.
    """

    __tablename__ = 'Relationship'
    id = Column(Integer, primary_key=True)
    subject_id = Column(String(255),
                        ForeignKey('Record.record_id'),
                        nullable=False)
    object_id = Column(String(255),
                       ForeignKey('Record.record_id'),
                       nullable=False)
    predicate = Column(String(255), nullable=False)

    def __init__(self, subject_id=None, object_id=None, predicate=None):
        """Create entry from Relationship info."""
        self.subject_id = subject_id
        self.object_id = object_id
        self.predicate = predicate

    def __repr__(self):
        """Return a string representation of a sql schema Relationship."""
        return ('SQL Schema Relationship <subject_id={}, object_id={},'
                'predicate={}>'.format(self.subject_id,
                                       self.object_id,
                                       self.predicate))


class Record(Base):
    """
    Implementation of Record table.

    Stores records, types, and record blobs.
    """

    __tablename__ = 'Record'
    record_id = Column(String(255), primary_key=True)
    record_type = Column(String(255), nullable=False)
    raw = Column(Text(), nullable=True)
    user_defined = Column(Text(), nullable=True)

    def __init__(self, record_id, record_type, raw=None, user_defined=None):
        """Create Record table entry with id, type, raw."""
        self.record_id = record_id
        self.record_type = record_type
        self.raw = raw
        self.user_defined = user_defined

    def __repr__(self):
        """Return a string representation of a sql schema Record."""
        return ('SQL Schema Record <record_id={}, record_type={}>'
                .format(self.record_id, self.record_type))


class ScalarData(Base):
    """
    Implementation of a table to store scalar-type data.

    The scalar table relates record ids to contained data if (and only if)
    those data entries have numerical values. For example,
    "density":200.14 would be represented here, but "strategy":"best-fit" would
    not be. Instead, "strategy":"best-fit" would go in the Value table.

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'ScalarData'
    record_id = Column(String(255),
                       ForeignKey(Record.record_id),
                       nullable=False,
                       primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    value = Column(Float(), nullable=False)
    tags = Column(Text(), nullable=True)
    units = Column(String(255), nullable=True)
    Index('record_scalar_idx', record_id, name)

    def __init__(self, record_id, name, value, tags=None, units=None):
        """Create entry from id, name, and value, and optionally tags/units."""
        self.record_id = record_id
        self.name = name
        self.value = value
        self.units = units
        self.tags = tags

    def __repr__(self):
        """Return a string representation of a sql schema ScalarData entry."""
        return ('SQL Schema ScalarData: <record_id={}, name={}, value={}, tags={},'
                'units={}>'
                .format(self.record_id,
                        self.name,
                        self.value,
                        self.tags,
                        self.units))


class StringData(Base):
    """
    Implementation of a table to store string-type data.

    The string table relates record ids to contained data if (and only if)
    those data entries have non-numerical values. For example,
    "density":"200.14" would be represented here, but "density":200.14 would
    not be, and would instead go in the scalar table. This is done so we can
    store non-scalar values while still giving users the benefit of numerical
    comparison lookups (being faster than string comparisons).

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'StringData'
    record_id = Column(String(255),
                       ForeignKey(Record.record_id),
                       nullable=False,
                       primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    value = Column(String(255), nullable=False)
    tags = Column(Text(), nullable=True)
    units = Column(String(255), nullable=True)

    def __init__(self, record_id, name, value, tags=None, units=None):
        """Create entry from id, name, and value, and optionally tags/units."""
        self.record_id = record_id
        self.name = name
        self.value = value
        # Arguably, string-based values don't need units. But because the
        # value vs. scalar implementation is hidden from the user, we need
        # to guarantee their availability in any "value"
        self.units = units
        self.tags = tags

    def __repr__(self):
        """Return a string representation of a sql schema StringData entry."""
        return ('SQL Schema StringData: <record_id={}, name={}, value={}, tags={}, '
                'units={}>'
                .format(self.record_id,
                        self.name,
                        self.value,
                        self.tags,
                        self.units))


class Document(Base):
    """
    Implementation of document table.

    The document table relates record ids to involved documents. Documents are
    information belonging to records, and are not directly exposed by the
    DAO. Rather, they belong to/are identified by records.
    """

    __tablename__ = 'Document'
    record_id = Column(String(255),
                       ForeignKey(Record.record_id),
                       nullable=False,
                       primary_key=True)
    uri = Column(String(255), nullable=False, primary_key=True)
    # TODO: What does a file that doesn't have a mimetype look like? Should
    # this be required? Should we fallback to getting file extension
    # from the uri if a mimetype isn't provided?
    mimetype = Column(String(255), nullable=True)
    tags = Column(Text(), nullable=True)

    def __init__(self, record_id, uri, contents=None, mimetype=None, tags=None):
        """Create from record_id, uri, and optionally contents and mimetype."""
        self.record_id = record_id
        self.uri = uri
        self.contents = contents
        self.mimetype = mimetype
        self.tags = tags

    def __repr__(self):
        """Return a string representation of a sql schema Document."""
        return ('SQL Schema Document: <record_id={}, uri={}, mimetype={}, tags={}>'
                .format(self.record_id, self.uri, self.mimetype, self.tags))


class Run(Base):
    """
    Implementation of Run table.

    Stores run metadata. Links to Record table.
    """

    __tablename__ = 'Run'
    record_id = Column(String(255),
                       ForeignKey(Record.record_id),
                       primary_key=True)
    application = Column(String(255), nullable=False)
    user = Column(String(255), nullable=True)
    version = Column(String(255), nullable=True)

    def __init__(self, record_id, application, user=None, version=None):
        """Create Run table entry with id, metadata."""
        self.record_id = record_id
        self.application = application
        self.user = user
        self.version = version

    def __repr__(self):
        """Return a string representation of a sql schema Run."""
        return ('SQL Schema Run: <record_id={}, application={}, user={},'
                'version={}>'.format(self.record_id,
                                     self.application,
                                     self.user,
                                     self.version))
