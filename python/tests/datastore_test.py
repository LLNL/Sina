"""
Tests for using the Datastore, a more user-friendly access for DAOs.

Like backend_test, these tests are run by each backend rather than here
as a file.

No operations are performed--this file makes heavy use of mocking.
"""
import unittest
from abc import ABCMeta, abstractmethod

import six
# Disable pylint checks due to its issue with virtual environments
from mock import patch  # pylint: disable=import-error

from sina.model import Record, Relationship
from sina.datastore import create_datastore, DataStore


class UniversalDatastoreTests(unittest.TestCase):
    """
    Tests for datastore functionality.

    These tests are (spiritually)) independent of backend due to reliance on
    mock and dao.py. For dao's abstract methods, such as insert(), delete(),
    and data_query(), the Sqlite implementation will be used, but only to check
    that something by the expected name was called. The Datastore calls "a"
    DAO without knowledge of its type. so if anything here would fail on ex:
    a Cassandra DAO instead of SQLite, that's an error on the DAO's side,
    and should be caught by backend_test.

    Make sure to order expected args based on the mocked method's signature,
    unless of course the DataStore intentionally rearranges them.
    """

    @classmethod
    def setUpClass(cls):
        """
        Create the datastore.

        We need a DB connection to do so, but we won't interact with it, so we
        set up the "default" of a SQLite in-memory db.
        """
        cls.datastore = create_datastore()

    @classmethod
    def tearDownClass(cls):
        """Shut down our datastore resources."""
        if cls.datastore:
            cls.datastore.close()

    # This is a testing method; we're not worried about arg count.
    # Also, we don't modify the kwargs dict, so it's not unsafe.
    # pylint: disable=too-many-arguments, dangerous-default-value
    def check_args(self, method, mock, args=tuple(), kwargs={},
                   expected_args=None):
        """
        Assert a mocked function was called with the correct args/kwargs.

        :param method_to_call: The datastore method being tested.
        :param mock: The mocked call
        :param args: The args (if any) to be passed, as an iterable. Will be
                     unpacked.
        :param kwargs: The kwargs (if any) to be passed, as a dictionary. Will
                       be unpacked.
        :param expected_args: The expected order if it differs from <args>'.
                              Used for, ex: default args, intentionally altered
                              order.
        """
        method(*args, **kwargs)
        self.assertTrue(mock.called)
        mock_args, mock_kwargs = mock.call_args
        if expected_args is None:
            expected_args = args
        self.assertEqual(mock_args, expected_args)
        self.assertEqual(mock_kwargs, kwargs)

    # #############  RecordOperations  ############# #
    @patch('sina.dao.RecordDAO.get')
    def test_get_record(self, mock):
        """Test the RecordOperation get()."""
        self.check_args(self.datastore.records.get, mock, args=("spam_rec_1",))

    @patch('sina.datastores.sql.RecordDAO.insert')
    def test_insert_record(self, mock):
        """Test the RecordOperation insert()."""
        self.check_args(self.datastore.records.insert,
                        mock, args=(Record(id="hello", type="_"),))

    @patch('sina.datastores.sql.RecordDAO.delete')
    def test_delete_record(self, mock):
        """Test the RecordOperation delete()."""
        unique_ids = ["something_even_more_unique", "the_most_unique_id"]
        self.check_args(self.datastore.records.delete, mock, args=(unique_ids,))

    @patch('sina.datastores.sql.RecordDAO.get_all_of_type')
    def test_find_with_type(self, mock):
        """Test the RecordOperation find_with_type()."""
        self.check_args(self.datastore.records.find_with_type, mock, args=("foo",),
                        expected_args=("foo", False))

    @patch('sina.datastores.sql.RecordDAO.get_available_types')
    def test_get_types(self, mock):
        """Test the RecordOperation get_types()."""
        self.check_args(self.datastore.records.get_types, mock)

    @patch('sina.datastores.sql.RecordDAO.data_query')
    def test_find_with_data(self, mock):
        """Test the RecordOperation find_with_data()."""
        self.check_args(self.datastore.records.find_with_data, mock,
                        kwargs={"bleepbloop": 2, "eggs": "fried"})

    @patch('sina.datastores.sql.RecordDAO.get_data_for_records')
    def test_get_data(self, mock):
        """Test the RecordOperation get_data()."""
        self.check_args(self.datastore.records.get_data, mock,
                        args=(("volume", "density"),
                              ("cool_rec", "less_cool_rec")))
        self.check_args(self.datastore.records.get_data, mock,
                        args=(("volume",),), expected_args=(("volume",), None))

    @patch('sina.datastores.sql.RecordDAO.get_with_max')
    def test_find_with_max(self, mock):
        """Test the RecordOperation find_with_max()."""
        self.check_args(self.datastore.records.find_with_max, mock,
                        args=("coolness",),
                        expected_args=("coolness", 1, False))

    @patch('sina.datastores.sql.RecordDAO.get_with_min')
    def test_find_with_min(self, mock):
        """Test the RecordOperation find_with_min()."""
        self.check_args(self.datastore.records.find_with_min, mock,
                        args=("sadness",),
                        expected_args=("sadness", 1, False))

    @patch('sina.datastores.sql.RecordDAO.get_given_document_uri')
    def test_find_with_file_uri(self, mock):
        """Test the RecordOperation find_with_file_uri()."""
        self.check_args(self.datastore.records.find_with_file_uri, mock,
                        args=("birdsong.mp3",),
                        expected_args=("birdsong.mp3", None, False))

    @patch('sina.datastores.sql.RecordDAO.get_with_mime_type')
    def test_find_with_file_mimetype(self, mock):
        """Test the RecordOperation find_with_file_mimetype()."""
        self.check_args(self.datastore.records.find_with_file_mimetype, mock,
                        args=("png",),
                        expected_args=("png", False))

    # #############  RelationshipOperations  ############# #
    @patch('sina.datastores.sql.RelationshipDAO.get')
    def test_find(self, mock):
        """Test the RelationshipOperation find()."""
        # Args were intentionally re-ordered, so we need to check kwargs.
        self.datastore.relationships.find("subj", "pred", "obj")
        mock_args, mock_kwargs = mock.call_args
        self.assertEqual(mock_kwargs, {"subject_id": "subj",
                                       "predicate": "pred",
                                       "object_id": "obj"})
        self.assertFalse(mock_args)

        self.datastore.relationships.find(object_id="obj")
        mock_args, mock_kwargs = mock.call_args
        self.assertEqual(mock_kwargs, {"subject_id": None,
                                       "predicate": None,
                                       "object_id": "obj"})
        self.assertFalse(mock_args)

    @patch('sina.datastores.sql.RelationshipDAO.insert')
    def test_insert_relationship(self, mock):
        """Test the RelationshipOperation insert()."""
        self.check_args(self.datastore.relationships.insert, mock,
                        args=(Relationship("human", "throws", "ball"),))

    # #############  DataStore Operations  ############# #
    @patch('sina.datastores.sql.DAOFactory.close')
    def test_close(self, mock):
        """Test the DataStore's close() method."""
        self.check_args(self.datastore.close, mock)

    @patch('sina.datastores.sql.DAOFactory.close')
    @patch('sina.datastores.sql.RecordDAO.get_with_min')
    def test_context_management(self, mock_query, mock_close):
        """Test that the DataStore acts as a context manager."""
        with create_datastore() as self.datastore:
            # Make sure the datastore itself is passed back
            self.assertIsInstance(self.datastore, DataStore)
            # Make sure queries are working
            self.check_args(self.datastore.records.find_with_min, mock_query,
                            args=("cool_rocks",),
                            expected_args=("cool_rocks", 1, False))
        # Make sure we called the close method.
        self.check_args(self.datastore.close, mock_close)
        # We now go out of scope without close() being called, but it's an
        # in-memory db.


@six.add_metaclass(ABCMeta)
class BackendSpecificTests(unittest.TestCase):
    """
    These tests can't be separated from backend.

    Each requires the creation of a Datastore and potentially the use of a
    specific backend. We mock some inits, but specific backends are required.
    """

    __test__ = False
    backend = None  # Set by child

    @staticmethod
    @abstractmethod
    def create_backend_datastore():
        """Create a datastore appropriate to the backend."""
        raise NotImplementedError

    @abstractmethod
    def test_create_datastore(self, mock_dao, mock_ds):
        """Make sure create_datastore() targets the backend when appropriate."""
        raise NotImplementedError

    def test_datastore_init(self):
        """Make sure DataStore's got all the proper DAOs available."""
        data = self.create_backend_datastore()
        self.assertIsInstance(data.dao_factory, self.backend.DAOFactory)
        self.assertIsInstance(data.records.record_dao, self.backend.RecordDAO)
        self.assertIsInstance(data.relationships.relationship_dao,
                              self.backend.RelationshipDAO)
