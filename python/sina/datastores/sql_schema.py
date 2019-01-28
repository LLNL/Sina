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
                        ForeignKey('Record.id'),
                        nullable=False)
    object_id = Column(String(255),
                       ForeignKey('Record.id'),
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
    id = Column(String(255), primary_key=True)
    type = Column(String(255), nullable=False)
    raw = Column(Text(), nullable=True)

    def __init__(self, id, type, raw=None):
        """Create Record table entry with id, type, raw."""
        self.id = id
        self.type = type
        self.raw = raw

    def __repr__(self):
        """Return a string representation of a sql schema Record."""
        return ('SQL Schema Record <id={}, type={}>'
                .format(self.id, self.type))


class ScalarData(Base):
    """
    Implementation of a table to store scalar-type data.

    The scalar table relates record ids to contained data if (and only if)
    those data entries have numerical values. For example,
    "density":200.14 would be represented here, but "strategy":"best-fit" would
    not be. Instead, "strategy":"best-fit" would go in the StringData table.

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'ScalarData'
    id = Column(String(255),
                ForeignKey(Record.id),
                nullable=False,
                primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    value = Column(Float(), nullable=False)
    tags = Column(Text(), nullable=True)
    units = Column(String(255), nullable=True)
    Index('record_scalar_idx', id, name)

    def __init__(self, id, name, value, tags=None, units=None):
        """Create entry from id, name, and value, and optionally tags/units."""
        self.id = id
        self.name = name
        self.value = value
        self.units = units
        self.tags = tags

    def __repr__(self):
        """Return a string representation of a sql schema ScalarData entry."""
        return ('SQL Schema ScalarData: <id={}, name={}, value={}, tags={},'
                'units={}>'
                .format(self.id,
                        self.name,
                        self.value,
                        self.tags,
                        self.units))


class ListScalarDataMaster(Base):
    """
    Implementation of a table to store info about lists of scalar-type data.

    Info that applies to all values in the list are stored here. The list
    scalar tables relates record ids to contained lists of data if (and only
    if) those data entries have lists of numerical values. For example,
    "density":{"value":[200.14, 12]} would be represented here, but
    "strategy":{"value":["best-fit", "some-string"]} would not be. Instead,
    it would go in the ListStringDataMaster table. Scalar and
    string data cannot be mixed in the same list. The list entries themselves
    are stored in the ListScalarDataEntry table.

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'ListScalarDataMaster'
    id = Column(String(255),
                ForeignKey(Record.id, ondelete='CASCADE',
                           deferrable=True, initially='DEFERRED'),
                nullable=False,
                primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    tags = Column(Text(), nullable=True)
    units = Column(String(255), nullable=True)

    def __init__(self, id, name, tags=None, units=None):
        """
        Create a ListScalarDataMaster entry with the given args.

        :param id: The record id associated with this value.
        :param name: The name of the datum associated with this value.
        :param tags: A list of tags to store.
        :param units: The associated units of the value.
        """
        self.id = id
        self.name = name
        self.tags = tags
        self.units = units

    def __repr__(self):
        """Return a string repr. of a sql schema ListScalarDataMaster entry."""
        return ('SQL Schema ListScalarDataMaster: <id={}, name={}, tags={}, '
                'units={}>'
                .format(self.id,
                        self.name,
                        self.tags,
                        self.units))


class ListScalarDataEntry(Base):
    """
    Implementation of a table to store list entries of scalar-type data.

    This table contains scalar-data list entries related to a list from the
    ListScalarDataMaster table.

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'ListScalarDataEntry'
    id = Column(String(255),
                ForeignKey(Record.id, ondelete='CASCADE',
                           deferrable=True, initially='DEFERRED'),
                nullable=False,
                primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    index = Column(Integer(), nullable=False, primary_key=True)
    value = Column(Float(), nullable=False)
    Index('record_scalar_list_idx', id, name, index)

    def __init__(self, id, name, value, index):
        """
        Create a ListScalarDataEntry entry with the given args.

        :param id: The record id associated with this value.
        :param name: The name of the datum associated with this value.
        :param index: The location in the scalar list of the value.
        :param value: The value to store.
        """
        self.id = id
        self.name = name
        self.index = index
        self.value = value

    def __repr__(self):
        """Return a string repr. of a sql schema ListScalarDataEntry entry."""
        return ('SQL Schema ListScalarDataEntry: <id={}, name={}, index={}, '
                'value={}>'
                .format(self.id,
                        self.name,
                        self.index,
                        self.value))


class StringData(Base):
    """
    Implementation of a table to store string-type data.

    The string table relates record ids to contained data if (and only if)
    those data entries have non-numerical values. For example,
    "strategy":{"value": "best-fit"} would be represented here,
    but "density":200.14 would not be, and would instead go in the scalar
    table. This is done so we can store non-scalar values while still giving
    users the benefit of numerical comparison lookups (being faster than string
    comparisons).

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'StringData'
    id = Column(String(255),
                ForeignKey(Record.id),
                nullable=False,
                primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    value = Column(String(255), nullable=False)
    tags = Column(Text(), nullable=True)
    units = Column(String(255), nullable=True)

    def __init__(self, id, name, value, tags=None, units=None):
        """Create entry from id, name, and value, and optionally tags/units."""
        self.id = id
        self.name = name
        self.value = value
        # Arguably, string-based values don't need units. But because the
        # value vs. scalar implementation is hidden from the user, we need
        # to guarantee their availability in any "value"
        self.units = units
        self.tags = tags

    def __repr__(self):
        """Return a string representation of a sql schema StringData entry."""
        return ('SQL Schema StringData: <id={}, name={}, value={}, tags={}, '
                'units={}>'
                .format(self.id,
                        self.name,
                        self.value,
                        self.tags,
                        self.units))


class ListStringDataMaster(Base):
    """
    Implementation of a table to store info about lists of string-type data.

    Info that applies to all values in the list are stored here. The list
    string table relates record ids to contained lists of data if (and
    only if) those data entries have lists of non-numerical values. For
    example, "strategy":{"value":["best-fit", "some-string"]} would be
    represented here, but "density":{"value":[200.14, 12]} would not be, and
    would instead go in the ListScalarDataMaster table. This is done so we can
    store non-scalar values while still giving users the benefit of numerical
    comparison lookups (being faster than string comparisons). Scalar and
    string data cannot be mixed in the same list. The list entries themselves
    are stored in the ListStringDataEntry table.

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'ListStringDataMaster'
    id = Column(String(255),
                ForeignKey(Record.id, ondelete='CASCADE',
                           deferrable=True, initially='DEFERRED'),
                nullable=False,
                primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    tags = Column(Text(), nullable=True)
    units = Column(String(255), nullable=True)

    def __init__(self, id, name, tags=None, units=None):
        """
        Create a ListStringDataMaster entry with the given args.

        :param id: The record id associated with this value.
        :param name: The name of the datum associated with this value.
        :param tags: A list of tags to store.
        :param units: The associated units of the value.
        """
        self.id = id
        self.name = name
        # Arguably, string-based values don't need units. But because the
        # value vs. scalar implementation is hidden from the user, we need
        # to guarantee their availability in any "value"
        self.units = units
        self.tags = tags

    def __repr__(self):
        """Return a string repr. of a sql schema ListStringDataMaster entry."""
        return ('SQL Schema ListStringDataMaster: <id={}, name={}, tags={}, '
                'units={}>'
                .format(self.id,
                        self.name,
                        self.tags,
                        self.units))


class ListStringDataEntry(Base):
    """
    Implementation of a table to store list entries of string-type data.

    This table contains string-data list entries related to a list from the
    ListStringDataMaster table.

    These tables are not exposed to the user. It's decided based on type
    which table should be accessed.
    """

    __tablename__ = 'ListStringDataEntry'
    id = Column(String(255),
                ForeignKey(Record.id, ondelete='CASCADE',
                           deferrable=True, initially='DEFERRED'),
                nullable=False,
                primary_key=True)
    name = Column(String(255), nullable=False, primary_key=True)
    index = Column(Integer(), nullable=False, primary_key=True)
    value = Column(String(255), nullable=False)

    def __init__(self, id, name, index, value):
        """
        Create a ListStringDataEntry entry with the given args.

        :param id: The record id associated with this value.
        :param name: The name of the datum associated with this value.
        :param index: The location in the scalar list of the value.
        :param value: The value to store.
        """
        self.id = id
        self.name = name
        self.index = index
        self.value = value

    def __repr__(self):
        """Return a string repr. of a sql schema ListStringDataEntry entry."""
        return ('SQL Schema ListStringDataEntry: <id={}, name={}, index={}, '
                'value={}>'
                .format(self.id,
                        self.name,
                        self.index,
                        self.value))


class Document(Base):
    """
    Implementation of document table.

    The document table relates record ids to involved documents. Documents are
    information belonging to records, and are not directly exposed by the
    DAO. Rather, they belong to/are identified by records.
    """

    __tablename__ = 'Document'
    id = Column(String(255),
                ForeignKey(Record.id),
                nullable=False,
                primary_key=True)
    uri = Column(String(255), nullable=False, primary_key=True)
    # TODO: What does a file that doesn't have a mimetype look like? Should
    # this be required? Should we fallback to getting file extension
    # from the uri if a mimetype isn't provided?
    mimetype = Column(String(255), nullable=True)
    tags = Column(Text(), nullable=True)

    def __init__(self, id, uri, contents=None, mimetype=None, tags=None):
        """Create from id, uri, and optionally contents and mimetype."""
        self.id = id
        self.uri = uri
        self.contents = contents
        self.mimetype = mimetype
        self.tags = tags

    def __repr__(self):
        """Return a string representation of a sql schema Document."""
        return ('SQL Schema Document: <id={}, uri={}, mimetype={}, tags={}>'
                .format(self.id, self.uri, self.mimetype, self.tags))


class Run(Base):
    """
    Implementation of Run table.

    Stores run metadata. Links to Record table.
    """

    __tablename__ = 'Run'
    id = Column(String(255),
                ForeignKey(Record.id),
                primary_key=True)
    application = Column(String(255), nullable=False)
    user = Column(String(255), nullable=True)
    version = Column(String(255), nullable=True)

    def __init__(self, id, application, user=None, version=None):
        """Create Run table entry with id, metadata."""
        self.id = id
        self.application = application
        self.user = user
        self.version = version

    def __repr__(self):
        """Return a string representation of a sql schema Run."""
        return ('SQL Schema Run: <id={}, application={}, user={},'
                'version={}>'.format(self.id,
                                     self.application,
                                     self.user,
                                     self.version))
