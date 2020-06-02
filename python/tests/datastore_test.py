"""
Tests for using the Datastore, a more user-friendly access for DAOs.

Like backend_test, these tests are run by each backend rather than here
as a file.
"""
import unittest
from abc import ABCMeta, abstractmethod

import six

from sina.model import Record, Relationship
from sina.datastore import create_datastore

TEMP_DB_NAME = "temp_sqlite_testfile.sqlite"
# CQLEngine needs a keyspace to start. Will not be edited.
INITIAL_KEYSPACE_NAME = "system_traces"
# Name of keyspace to create and then delete.
TEMP_KEYSPACE_NAME = "temp_keyspace_testing_sina"


def populate_database(datastore):
    """
    Add basic objects to use in tests.

    Note that this is itself and alone a test, given that the "real"
    functionality of insertion is tested elsewhere.
    """
    test_rec = Record(id="spam_rec_1", type="spam_rec")
    test_rec_2 = Record(id="spam_rec_2", type="spam_rec")
    test_rec_3 = Record(id="egg_rec_1", type="egg_rec")
    # Two inserts to test both single and multi-inserts.
    datastore.insert([test_rec, test_rec_2])
    datastore.insert(test_rec_3)
    test_rel = Relationship(subject_id="spam_rec_1", object_id="spam_rec_2",
                            predicate="mimics")
    test_rel_2 = Relationship(subject_id="egg_rec_1", object_id="spam_rec_1",
                              predicate="compliments")
    test_rel_3 = Relationship(subject_id="egg_rec_1", object_id="spam_rec_2",
                              predicate="compliments")
    datastore.insert([test_rel, test_rel_2])
    datastore.insert(test_rel_3)


@six.add_metaclass(ABCMeta)
class TestDatastore(unittest.TestCase):
    """
    Tests for datastore functionality.

    Note that all we're testing here is that objects and methods are created
    and called as expected. All testing of the methods themselves is carried
    out in backend_test; the datastore's just an abstraction to make that
    functionality easier for an end-user.
    """

    # Prevent nosetest from running this
    __test__ = False

    @classmethod
    @abstractmethod
    def create_dao_factory(cls):
        """
        Create the DAO to run DataStore tests.

        Must be implemented by child, likely via its mixin class (ex: SQLMixin).
        """
        raise NotImplementedError

    @classmethod
    def setUpClass(cls):
        """Do whatever setup's necessary to run all tests."""
        cls.datastore = create_datastore(cls.create_dao_factory())
        populate_database(cls.datastore)

    @classmethod
    def tearDownClass(cls):
        """Do whatever teardown's necessary to clean up after all tests."""
        if cls.datastore:
            cls.datastore.close()

    @abstractmethod
    def test_identity(self):
        """Test that the DataStore is of the expected type."""
        raise NotImplementedError

    def test_overloaded_insert(self):
        """Make sure we can insert Records and Relationships without error."""
        # The act of setting up for this test covers all the functionality
        # needed, namely that we don't raise errors.
        pass

    def test_get_record(self):
        """Test getting a record."""
        rec = self.datastore.get_records("spam_rec_1")
        self.assertIsInstance(rec, Record)
        self.assertEqual(rec.type, "spam_rec")

    def test_get_relationship(self):
        """Test getting a relationship."""
        rels = self.datastore.get_relationships(subject_id="egg_rec_1",
                                                predicate="compliments")
        self.assertEqual(len(rels), 2)
        self.assertIsInstance(rels[1], Relationship)
        self.assertEqual(rels[1].subject_id, "egg_rec_1")

    def test_recorddao_inherited(self):
        """Test our ability to call an inherited RecordDAO method."""
        recs_by_type = list(self.datastore.get_all_of_type("spam_rec",
                                                           ids_only=True))
        self.assertEqual(len(recs_by_type), 2)

    # There are currently no functions for RelationshipDAO besides get() and
    # insert(), so we can't test an inherited function.

    def test_get_is_disabled(self):
        """Test that get() can't be called."""
        with self.assertRaises(AttributeError) as context:
            self.datastore.get("spam_rec_1")
        self.assertIn("get() is ambiguous for DataStore and is not implement",
                      str(context.exception))
