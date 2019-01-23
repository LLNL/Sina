"""
Cqlengine implementation of the minimal schema used in Cassandra imports.

Based on Mnoda
"""
import numbers
import logging

from cassandra.cqlengine.models import Model
from cassandra.cqlengine.management import sync_table
from cassandra.cqlengine import columns, connection

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
    """Query table for finding records given scalar list criteria."""

    name = columns.Text(primary_key=True)
    # CQLEngine support for frozen collections isn't part of their API.
    # Currently, _freeze_db_type() *is* the least hacky option.
    value = columns.List(columns.Double(), primary_key=True)
    value._freeze_db_type()
    id = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class ScalarListDataFromRecord(Model):
    """Query table for finding a scalar list-valued Record.data entry given record ID."""

    id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
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
    """Query table for finding records given scalar list criteria."""

    name = columns.Text(primary_key=True)
    value = columns.List(columns.Text(), primary_key=True)
    value._freeze_db_type()
    id = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


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
    Query table for finding object given subject (and/or predicate).

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
    """Query table for finding subject given object (and/or predicate)."""

    subject_id = columns.Text(primary_key=True)
    object_id = columns.Text(primary_key=True)
    predicate = columns.Text(primary_key=True)


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
    LOGGER.debug('Cross populating: {} {} {}.'
                 .format(subject_id, predicate, object_id))
    SubjectFromObject.create(subject_id=subject_id,
                             predicate=predicate,
                             object_id=object_id,
                             )
    ObjectFromSubject.create(subject_id=subject_id,
                             predicate=predicate,
                             object_id=object_id,
                             )


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

    Each call handles one entry from one Record's "data" attribute. For mass
    (batch) insertion, see RecordDAO.insert_many().

    :param name: The name of the entry
    :param value: The entry's value (must be the type of value the pair handles)
    :param id: The id of the record containing the entry
    :param tags: Tags to be applied to this entry
    :param units: Units of the entry.
    :param force_overwrite: Whether to forcibly overwrite an extant entry in
                            the same "slot" in the database
    """
    # Check if it's a list
    if isinstance(value, list):
        # Check if it's a scalar or empty
        table_1, table_2 = ((ScalarListDataFromRecord, RecordFromScalarListData)
                            if not value or isinstance(value[0], numbers.Real)
                            else (StringListDataFromRecord, RecordFromStringListData))
    else:
        table_1, table_2 = ((ScalarDataFromRecord, RecordFromScalarData)
                            if isinstance(value, numbers.Real)
                            else (StringDataFromRecord, RecordFromStringData))

    # Now that we know which tables to use, determine how to insert
    first_table_create = (table_1.create if force_overwrite
                          else table_1.if_not_exists().create)
    second_table_create = (table_2.create if force_overwrite
                           else table_2.if_not_exists().create)

    # Perform the insertion
    first_table_create(id=id,
                       name=name,
                       value=value,
                       tags=tags,
                       units=units)
    second_table_create(id=id,
                        name=name,
                        value=value,
                        tags=tags,
                        units=units)


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
    LOGGER.info('Forming cassandra connection to ip_list={} with keyspace={}.'
                .format(node_ip_list, keyspace))
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
