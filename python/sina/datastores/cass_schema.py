"""
Cqlengine implementation of the minimal schema used in Cassandra imports.

Based on Mnoda
"""
import numbers
import logging

from cassandra.cqlengine.management import sync_table

try:
    from cassandra.cqlengine.models import Model
    from cassandra.cqlengine import columns, connection
except ImportError:
    # Sphinx autodoc will import this file regardless of whether Cassandra is
    # installed. Ordinarily it can mock imports, but the type of usage
    # seen by "columns" exceeds what it's able to mock. This set of definitions
    # represents a "fixed" mock. Note that trying to use this without Cassandra
    # installed outside of autodocs will still raise the expected ImportError,
    # due to importing sync_table (which autodocs CAN mock).

    # This should be revisited if we drop support for Python 2, as Python 3
    # includes more flexible mocking.
    Model = object

    class _AutodocFakeColumn:
        """Mock column members that can't be mocked by Sphinx's autodoc."""

        def __init__(self, **kwargs):
            """Create a simple object that can take arbitrary attributes."""
            self.__dict__.update(kwargs)

        def _freeze_db_type(self):
            """Mock the freezing method, itself a workaround."""
            pass
    columns = _AutodocFakeColumn()
    columns.Text = lambda primary_key=True, required=False: 0
    columns.Set = lambda a, primary_key=True, required=False: a
    columns.Double = lambda primary_key=True, required=False: 0
    columns.List = lambda a, primary_key=True, required=False: _AutodocFakeColumn()

LOGGER = logging.getLogger(__name__)


class Record(Model):
    """
    Toplevel object in the Mnoda schema.

    Stores the raw form of the record.
    """

    id = columns.Text(primary_key=True)
    type = columns.Text()
    raw = columns.Text()


class DocumentFromRecord(Model):
    """Query table for finding documents given records."""

    id = columns.Text(primary_key=True)
    uri = columns.Text(primary_key=True)
    mimetype = columns.Text()
    tags = columns.Set(columns.Text())


class RecordFromScalarData(Model):
    """Query table for finding records given scalar criteria."""

    name = columns.Text(primary_key=True)
    value = columns.Double(primary_key=True)
    id = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class ScalarDataFromRecord(Model):
    """Query table for finding a scalar-valued Record.data entry given record ID."""

    id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    value = columns.Double(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class RecordFromScalarListData(Model):
    """
    Query table for finding records given scalar list criteria.

    Each entry in a scalar list is given its own row in the database in this
    table (not in its partner table) to facilitate the specific case of
    "find Records where x contains (y, a value < y, etc.)" This is more efficient
    for querying, but does mean that the arrangement of list members, as well as
    any duplication within a list (rows overwrite) is lost. The partner table
    is in charge of maintaining this order.

    We store neither units nor tags since they're not required for this type of
    query. Those are more for 'find me everything tagged "output" in "record_1"'
    (tags) or simple retrieval (units), both of which use the partner table.
    """

    name = columns.Text(primary_key=True)
    value = columns.Double(primary_key=True)
    id = columns.Text(primary_key=True)


class ScalarListDataFromRecord(Model):
    """Query table for finding a scalar list-valued Record.data entry given record ID."""

    id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    # CQLEngine support for frozen collections isn't part of their API.
    # Currently, _freeze_db_type() *is* the least hacky option.
    value = columns.List(columns.Double(), primary_key=True)
    value._freeze_db_type()
    units = columns.Text()
    tags = columns.Set(columns.Text())


class RecordFromStringData(Model):
    """
    Query table for finding records given string criteria (ex, "version"="1.2.3").

    String data are any Record.data entry provided by the user that doesn't have a
    number for a value (ex: "machine":"merl", "version":"1.2").
    """

    name = columns.Text(primary_key=True)
    value = columns.Text(primary_key=True)
    id = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class StringDataFromRecord(Model):
    """Query table for finding a string-valued Record.data entry given record ID."""

    id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    value = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class RecordFromStringListData(Model):
    """
    Query table for finding records given string list criteria.

    Differs from its partner in the same ways as RecordFromScalarListData.
    """

    name = columns.Text(primary_key=True)
    value = columns.Text(primary_key=True)
    id = columns.Text(primary_key=True)


class StringListDataFromRecord(Model):
    """Query table for finding a scalar list-valued Record.data entry given record ID."""

    id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    value = columns.List(columns.Text(), primary_key=True)
    value._freeze_db_type()
    units = columns.Text()
    tags = columns.Set(columns.Text())


class Run(Model):
    """Query table for finding runs based on special, supported metadata."""

    id = columns.Text(primary_key=True)
    application = columns.Text(required=True)
    user = columns.Text()
    version = columns.Text()


class ObjectFromSubject(Model):
    """
    Query table for finding object given subject (plus optionally predicate).

    Subject/Object is triples terminology. Example:
    <subject> <predicate> <object>
    Task contains run

    Example question: What subjects are related to object_foo?
    Example question: What are all the subjects 'contained by' object_foo?
    """

    subject_id = columns.Text(primary_key=True)
    predicate = columns.Text(primary_key=True)
    object_id = columns.Text(primary_key=True)


class SubjectFromObject(Model):
    """Query table for finding subject given object (plus optionally predicate)."""

    object_id = columns.Text(primary_key=True)
    predicate = columns.Text(primary_key=True)
    subject_id = columns.Text(primary_key=True)


def cross_populate_object_and_subject(subject_id,
                                      predicate,
                                      object_id):
    """
    Add entries to both the Subject_from_Object and Object_from_Subject tables.

    These tables have the same data (but are organized differently) to allow
    for various queries.

    :param subject_id: The id of the subject
    :param predicate: The relationship between the subject and the object
    :param object_id: The id of the object
    """
    LOGGER.debug('Cross populating: %s %s %s.', subject_id, predicate, object_id)
    SubjectFromObject.create(subject_id=subject_id,
                             predicate=predicate,
                             object_id=object_id,
                             )
    ObjectFromSubject.create(subject_id=subject_id,
                             predicate=predicate,
                             object_id=object_id,
                             )


def _discover_tables_from_value(value):
    """
    Given a value, tell what pair of query tables it's associated with based on type.

    :param value: The value to evaluate

    :returns: A tuple containing the two query tables: (XFromRecord, RecordFromX)
    """
    # Check if it's a list
    if isinstance(value, list):
        # Check if it's a scalar or empty
        x_from_rec, rec_from_x = ((ScalarListDataFromRecord, RecordFromScalarListData)
                                  if not value or isinstance(value[0], numbers.Real)
                                  else (StringListDataFromRecord, RecordFromStringListData))
    else:
        x_from_rec, rec_from_x = ((ScalarDataFromRecord, RecordFromScalarData)
                                  if isinstance(value, numbers.Real)
                                  else (StringDataFromRecord, RecordFromStringData))
    return (x_from_rec, rec_from_x)


def cross_populate_data_tables(name,
                               value,
                               id,
                               tags=None,
                               units=None,
                               force_overwrite=False):
    """
    Simultaneously add data entries to a pair of tables.

    The schema includes 4 pairs of tables for each of the 4 types of data
    accepted: scalars, strings, scalar lists, and string lists. Each partner in
    a pair holds the same data in a different arrangement to support
    different types of queries. The pair to insert into is determined based
    on the value arg's type.

    Includes additional logic for handling the case of list data, where the
    rearrangement is a bit more involved than swapping column order (splitting
    a list into overwriting rows or keeping it intact)

    Each call handles one entry from one Record's "data" attribute. For mass
    (batch) insertion, see RecordDAO.insert_many().

    :param name: The name of the entry
    :param value: The entry's value
    :param id: The id of the record containing the entry
    :param tags: Tags to be applied to this entry
    :param units: Units of the entry.
    :param force_overwrite: Whether to forcibly overwrite an extant entry in
                            the same "slot" in the database
    """
    x_from_rec, rec_from_x = _discover_tables_from_value(value)

    # Now that we know which tables to use, determine how to insert
    x_from_rec_create = (x_from_rec.create if force_overwrite
                         else x_from_rec.if_not_exists().create)
    x_from_rec_create(id=id,
                      name=name,
                      value=value,
                      tags=tags,
                      units=units)

    if rec_from_x in (RecordFromStringListData, RecordFromScalarListData):
        # We allow overwriting in the list tables, because we want only one
        # entry per value (no duplicates tracking). So we rely on the partner
        # table to detect that first if not force_overwrite (hence the early
        # insert). Also, since we only want one value per entry, we loop.
        for entry in value:
            rec_from_x.create(id=id,
                              name=name,
                              value=entry)
    else:
        rec_from_x_create = (rec_from_x.create if force_overwrite
                             else rec_from_x.if_not_exists().create)
        rec_from_x_create(id=id,
                          name=name,
                          value=value,
                          tags=tags,
                          units=units)


def cross_batch_delete_data_tables(name,
                                   value,
                                   id,
                                   batch):
    """
    Simultaneously create batch deletion statements for a pair of tables.

    Each call handles one entry from one Record's "data" attribute and adds
    the deletion statements to the provided batch. Tables are decided based
    on the type of the value arg.

    :param name: The name of the entry
    :parm value: The entry's value
    :param id: The id of the record containing the entry
    :param batch: The batch object to add the statements to.
    """
    x_from_rec, rec_from_x = _discover_tables_from_value(value)

    x_from_rec.objects(id=id, name=name, value=value).batch(batch).delete()

    if rec_from_x in (RecordFromStringListData, RecordFromScalarListData):
        for entry in value:
            rec_from_x.objects(id=id, name=name, value=entry).batch(batch).delete()
    else:
        rec_from_x.objects(id=id, name=name, value=value).batch(batch).delete()


def form_connection(keyspace, node_ip_list=None):
    """
    Set up our connection info and prep our tables.

    Note the lack of a "session" object. Looks like each cqlengine
    create-statement lightly builds its own.

    :param keyspace: The keyspace to connect to.
    :param node_ip_list: A list of ips belonging to nodes on the target
                         Cassandra instance. If None, connects to localhost.
    """
    if not node_ip_list:
        node_ip_list = ['127.0.0.1']
    LOGGER.info('Forming cassandra connection to ip_list=%s with keyspace=%s.',
                node_ip_list, keyspace)
    connection.setup(node_ip_list, keyspace)

    sync_table(Record)
    sync_table(Run)
    sync_table(ObjectFromSubject)
    sync_table(SubjectFromObject)
    sync_table(DocumentFromRecord)
    sync_table(RecordFromScalarData)
    sync_table(ScalarDataFromRecord)
    sync_table(StringDataFromRecord)
    sync_table(RecordFromStringData)
    sync_table(RecordFromScalarListData)
    sync_table(RecordFromStringListData)
    sync_table(ScalarListDataFromRecord)
    sync_table(StringListDataFromRecord)
