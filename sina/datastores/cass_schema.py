"""
Cqlengine implementation of the minimal schema used in Cassandra imports.

Based on Mnoda
"""

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

    record_id = columns.Text(primary_key=True)
    record_type = columns.Text()
    raw = columns.Text()
    user_defined = columns.Text()


class DocumentFromRecord(Model):
    """Query table for finding documents given records."""

    record_id = columns.Text(primary_key=True)
    uri = columns.Text(primary_key=True)
    mimetype = columns.Text()
    tags = columns.Set(columns.Text())


class RecordFromScalar(Model):
    """Query table for finding records given scalar criteria."""

    name = columns.Text(primary_key=True)
    value = columns.Double(primary_key=True)
    record_id = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class ScalarFromRecord(Model):
    """Query table for finding scalars given record ID."""

    record_id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    value = columns.Double(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class RecordFromValue(Model):
    """
    Query table for finding records given value criteria.

    Values are any Record.value provided by the user that doesn't have a
    number for a value (ex: "machine":"merl", "version":"1.2").
    """

    name = columns.Text(primary_key=True)
    value = columns.Text(primary_key=True)
    record_id = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class ValueFromRecord(Model):
    """Query table for finding value given record ID."""

    record_id = columns.Text(primary_key=True)
    name = columns.Text(primary_key=True)
    value = columns.Text(primary_key=True)
    units = columns.Text()
    tags = columns.Set(columns.Text())


class Run(Model):
    """Query table for finding runs based on special, supported metadata."""

    record_id = columns.Text(primary_key=True)
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


def cross_populate_scalar_and_record(name,
                                     value,
                                     record_id,
                                     tags=None,
                                     units=None,
                                     force_overwrite=False):
    """
    Add entries to both the Scalar_from_Record and Record_from_Scalar tables.

    These tables have the same data (but are organized differently) to allow
    for various queries.

    This works on only a single scalar and record at a time. For inserting
    multiple scalars or records, see do_general_batch_insert().

    :param name: The name of the scalar
    :param value: The scalar's value
    :param record_id: The id of the record containing the scalar
    :param tags: Tags to be applied to this scalar
    :param units: Units of the scalar
    :param force_overwrite: Whether to forcibly overwrite an extant entry in
                            the same "slot" in the database
    """
    LOGGER.debug('Cross populating scalar and record with: name={}, value={}, '
                 'record_id={}, tags={}, units={}, and force_overwrite={}.'
                 .format(name, value, record_id, tags, units, force_overwrite))
    scalar_from_record_create = (ScalarFromRecord.create if force_overwrite
                                 else ScalarFromRecord.if_not_exists()
                                 .create)
    record_from_scalar_create = (RecordFromScalar.create if force_overwrite
                                 else RecordFromScalar.if_not_exists()
                                 .create)

    scalar_from_record_create(record_id=record_id,
                              name=name,
                              value=value,
                              tags=tags,
                              units=units,
                              )
    record_from_scalar_create(record_id=record_id,
                              name=name,
                              value=value,
                              tags=tags,
                              units=units,
                              )


def cross_populate_value_and_record(name,
                                    value,
                                    record_id,
                                    tags=None,
                                    units=None,
                                    force_overwrite=False):
    """
    Add entries to both the Value_from_Record and Record_from_Value tables.

    These tables have the same data (but are organized differently) to allow
    for various queries.

    :param name: The name of the value (non-scalar)
    :param value: The value's value
    :param record_id: The id of the record containing the value
    :param tags: Tags to be applied to this value
    :param units: Units of the value.
    :param force_overwrite: Whether to forcibly overwrite an extant entry in
                            the same "slot" in the database
    """
    LOGGER.debug('Cross populating value and record with: name={}, value={}, '
                 'record_id={}, tags={}, units={}, and force_overwrite={}.'
                 .format(name, value, record_id, tags, units, force_overwrite))
    value_from_record_create = (ValueFromRecord.create if force_overwrite
                                else ValueFromRecord.if_not_exists()
                                .create)
    record_from_value_create = (RecordFromValue.create if force_overwrite
                                else RecordFromValue.if_not_exists()
                                .create)

    value_from_record_create(record_id=record_id,
                             name=name,
                             value=value,
                             tags=tags,
                             units=units,
                             )
    record_from_value_create(record_id=record_id,
                             name=name,
                             value=value,
                             tags=tags,
                             units=units,
                             )


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
    sync_table(RecordFromScalar)
    sync_table(ScalarFromRecord)
    sync_table(ValueFromRecord)
    sync_table(RecordFromValue)
