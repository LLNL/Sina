"""
Tests for using the Datastore, a more user-friendly access for DAOs.

Few operations are performed--this file makes heavy use of mocking.
"""
# Disable checks that aren't as applicable for unit tests
# pylint: disable=too-many-public-methods, too-many-arguments

import unittest

# Disable pylint checks due to its issue with virtual environments
from mock import Mock, patch  # pylint: disable=import-error
import pytest  # pylint: disable=import-error

import sina
import sina.datastore

from sina.datastore import connect, create_datastore, DataStore, ReadOnlyDataStore


class AbstractDataStoreTest(unittest.TestCase):
    """Base class for testing data stores"""

    __test__ = False

    # Set to the DataStore class in sub tests
    data_store_class = None

    def setUp(self):
        """Assemble all our mock objects."""
        self.dao_factory = Mock()
        self.record_dao = Mock()
        self.relationship_dao = Mock()
        self.dao_factory.create_record_dao = Mock(return_value=self.record_dao)
        self.dao_factory.create_relationship_dao = Mock(return_value=self.relationship_dao)
        self.datastore = self.data_store_class(self.dao_factory)  # pylint: disable=not-callable

    def assert_method_is_passthrough(self, method_name, method_owner,
                                     delegate_method_name,
                                     delegate_method_owner, num_args=0,
                                     opt_args=tuple(), has_result=True):
        """
        Check args are passed correctly and return is unmodified.

        :param method_name: The name of the method to call.
        :param method_owner: The owner of the method to call.
        :param delegate_method_name: The name of the method it passes through
                                     to.
        :param delegate_method_owner: The owner of the method to pass through to
        :param num_args: How many args are expected. If testing optional args,
                         use the opt_args param.
        :param opt_args: A tuple of exact optional arguments the passthrough is
                         expected to provide.
        :param has_result: Whether or not the test method returns a value
        """
        expected_result = "test return" if has_result else None
        setattr(delegate_method_owner,
                delegate_method_name,
                Mock(return_value=expected_result))
        args = list(range(0, num_args))
        actual_result = getattr(method_owner, method_name)(*args)
        if opt_args:
            args += opt_args
        self.assertIs(actual_result, expected_result)
        getattr(delegate_method_owner,
                delegate_method_name).assert_called_with(*args)

    def assert_record_method_is_passthrough(self, method_name,
                                            delegate_method_name, num_args=0,
                                            opt_args=tuple(), has_result=False):
        """Provide passthrough tests on record methods."""
        self.assert_method_is_passthrough(method_name, self.datastore.records,
                                          delegate_method_name, self.record_dao,
                                          num_args, opt_args, has_result)

    def assert_relationship_method_is_passthrough(self, method_name,
                                                  delegate_method_name,
                                                  num_args=0, opt_args=tuple(),
                                                  has_result=False):
        """Provide passthrough tests on relationship methods."""
        self.assert_method_is_passthrough(method_name,
                                          self.datastore.relationships,
                                          delegate_method_name,
                                          self.relationship_dao,
                                          num_args, opt_args, has_result)

    def assert_datastore_method_is_passthrough(self, method_name,
                                               delegate_method_name,
                                               num_args=0, opt_args=tuple(),
                                               has_result=False):
        """Provide passthrough tests on datastore methods."""
        self.assert_method_is_passthrough(method_name, self.datastore,
                                          delegate_method_name,
                                          self.dao_factory, num_args, opt_args,
                                          has_result)


class ReadOnlyDatastoreTests(AbstractDataStoreTest):
    """
    Tests for datastore functionality.

    These don't test the functionality of the methods (see instead
    backend_test), they just make sure that the datastore is wrapping methods
    correctly.
    """

    __test__ = True

    data_store_class = ReadOnlyDataStore

    # #############  RecordOperations  ############# #
    def test_get_record(self):
        """Test the RecordOperation get()."""
        # We need to test that args are properly kwarg'd to reorder
        expected_result = "test return"
        self.record_dao.get = Mock(return_value=expected_result)
        args = ("ids", "chunk_size")
        expected_args = ['ids']
        expected_kwargs = {"chunk_size": "chunk_size"}
        actual_result = self.datastore.records.get(*args)
        self.assertIs(actual_result, expected_result)
        self.record_dao.get.assert_called_with(*expected_args, **expected_kwargs)

        # ...and that default args are properly kwarg'd as well.
        args = ("ids",)
        expected_args = ['ids']
        expected_kwargs = {"chunk_size": 999}
        actual_result = self.datastore.records.get(*args)
        self.assertIs(actual_result, expected_result)
        self.record_dao.get.assert_called_with(*expected_args, **expected_kwargs)

    def test_find_with_type(self):
        """Test the RecordOperation find_with_type()."""
        self.assert_record_method_is_passthrough("find_with_types",
                                                 "get_all_of_type", 3)
        self.assert_record_method_is_passthrough("find_with_types",
                                                 "get_all_of_type", 1,
                                                 opt_args=(False, None))

    def test_get_all(self):
        """Test the RecordOperation get_all()."""
        self.assert_record_method_is_passthrough("get_all",
                                                 "get_all", 1)
        self.assert_record_method_is_passthrough("get_all",
                                                 "get_all", 0,
                                                 opt_args=(False,))

    def test_get_types(self):
        """Test the RecordOperation get_types()."""
        self.assert_record_method_is_passthrough("get_types",
                                                 "get_available_types")

    def test_get_curve_set_names(self):
        """Test the RecordOperation get_curve_set_names()."""
        self.assert_record_method_is_passthrough("get_curve_set_names",
                                                 "get_curve_set_names")

    def test_exist(self):
        """Test the RecordOperation exist()."""
        self.assert_record_method_is_passthrough("exist", "exist", 1)

    def test_get_raw(self):
        """Test the RecordOperation get_raw()."""
        self.assert_record_method_is_passthrough("get_raw", "get_raw", 1)

    def test_data_names(self):
        """Test the RecordOperation data_names()."""
        self.assert_record_method_is_passthrough("data_names", "data_names", 3)
        self.assert_record_method_is_passthrough("data_names", "data_names", 1,
                                                 opt_args=(None, False))

    def test_find_with_data(self):
        """Test the RecordOperation find_with_data()."""
        # Here, we need to test kwargs and only kwargs.
        expected_result = "test return"
        self.record_dao.data_query = Mock(return_value=expected_result)
        kwargs = {"some_string": "foo", "some_scalar": 3}
        actual_result = self.datastore.records.find_with_data(**kwargs)
        self.assertIs(actual_result, expected_result)
        self.record_dao.data_query.assert_called_with(**kwargs)

    def test_get_data(self):
        """Test the RecordOperation get_data()."""
        self.assert_record_method_is_passthrough("get_data",
                                                 "get_data_for_records", 2)
        self.assert_record_method_is_passthrough("get_data",
                                                 "get_data_for_records", 1,
                                                 opt_args=(None,))

    def test_find_with_max(self):
        """Test the RecordOperation find_with_max()."""
        self.assert_record_method_is_passthrough("find_with_max",
                                                 "get_with_max", 3)
        self.assert_record_method_is_passthrough("find_with_max",
                                                 "get_with_max", 1,
                                                 opt_args=(1, False))

    def test_find_with_min(self):
        """Test the RecordOperation find_with_min()."""
        self.assert_record_method_is_passthrough("find_with_min",
                                                 "get_with_min", 3)
        self.assert_record_method_is_passthrough("find_with_min",
                                                 "get_with_min", 1,
                                                 opt_args=(1, False))

    def test_find_with_file_uri(self):
        """Test the RecordOperation find_with_file_uri()."""
        # We need to test whether kwargs are properly provided and reordered.
        expected_result = "test return"
        self.record_dao.get_given_document_uri = Mock(return_value=expected_result)
        arg = "*.png"
        expected_kwargs = {"uri": "*.png",
                           "ids_only": False,
                           "accepted_ids_list": None}
        actual_result = self.datastore.records.find_with_file_uri(arg)
        self.assertIs(actual_result, expected_result)
        self.record_dao.get_given_document_uri.assert_called_with(**expected_kwargs)

        args = ("*.png", True, ["test_rec", "other_test_rec"])
        expected_kwargs = {"uri": "*.png",
                           "ids_only": True,
                           "accepted_ids_list": ["test_rec", "other_test_rec"]}
        actual_result = self.datastore.records.find_with_file_uri(*args)
        self.assertIs(actual_result, expected_result)
        self.record_dao.get_given_document_uri.assert_called_with(**expected_kwargs)

    def test_find_with_file_mimetype(self):
        """Test the RecordOperation find_with_file_mimetype()."""
        self.assert_record_method_is_passthrough("find_with_file_mimetype",
                                                 "get_with_mime_type", 2)
        self.assert_record_method_is_passthrough("find_with_file_mimetype",
                                                 "get_with_mime_type", 1,
                                                 opt_args=(False,))

    def test_record_find(self):
        """Test the RecordOperation find()."""
        self.assert_record_method_is_passthrough("find",
                                                 "_find", 7)
        self.assert_record_method_is_passthrough("find",
                                                 "_find", 0,
                                                 opt_args=(None, None, None, None, None,
                                                           False, ("data", "file_uri",
                                                                   "mimetype", "types")))

    # #############  RelationshipOperations  ############# #
    def test_find(self):
        """Test the RelationshipOperation find()."""
        # We need to test that args are properly kwarg'd to reorder
        expected_result = "test return"
        self.relationship_dao.get = Mock(return_value=expected_result)
        args = ("subject_id", "predicate", "object_id")
        expected_kwargs = {"subject_id": "subject_id",
                           "object_id": "object_id",
                           "predicate": "predicate"}
        actual_result = self.datastore.relationships.find(*args)
        self.assertIs(actual_result, expected_result)
        self.relationship_dao.get.assert_called_with(**expected_kwargs)

        # ...and that default args are properly kwarg'd as well.
        args = ("subject_id",)
        expected_kwargs = {"subject_id": "subject_id",
                           "object_id": None,
                           "predicate": None}
        actual_result = self.datastore.relationships.find(*args)
        self.assertIs(actual_result, expected_result)
        self.relationship_dao.get.assert_called_with(**expected_kwargs)

    # #############  DataStore Operations  ############# #
    def test_close(self):
        """Test the DataStore's close() method."""
        self.assert_datastore_method_is_passthrough("close", "close")

    def test_exit(self):
        """Test the DataStore's __exit__() method."""
        # This is mostly a passthrough, but we drop exit's 3 args to call close
        self.dao_factory.close = Mock()
        self.datastore.__exit__(1, 2, 3)  # all args dropped
        self.dao_factory.close.assert_called_with()

    def test_enter(self):
        """Test the DataStore's __enter__() method."""
        self.assertEqual(self.datastore.__enter__(), self.datastore)

    def test_init(self):
        """Test that DataStore initializes its Operation objects correctly."""
        rec_dao, rel_dao = ("fake record dao", "fake relationship dao")
        expected_factory = Mock()
        expected_factory.create_record_dao = Mock(return_value=rec_dao)
        expected_factory.create_relationship_dao = Mock(return_value=rel_dao)
        test_ds = DataStore(expected_factory)
        self.assertEqual(test_ds.records._record_dao, rec_dao)  # pylint: disable=protected-access
        self.assertEqual(
            test_ds.relationships._relationship_dao,  # pylint: disable=protected-access
            rel_dao)

    def test_read_only_attribute(self):
        """Verify that read_only is True on mutable data stores."""
        self.assertTrue(self.datastore.read_only)


class DataStoreTest(AbstractDataStoreTest):
    """
    Tests for datastore functionality.

    These don't test the functionality of the methods (see instead
    backend_test), they just make sure that the datastore is wrapping methods
    correctly.
    """

    __test__ = True

    data_store_class = DataStore

    def test_insert_record(self):
        """Test the RecordOperation insert()."""
        self.assert_record_method_is_passthrough("insert", "insert", 1,
                                                 opt_args=(None, None),
                                                 has_result=False)

    def test_delete_record(self):
        """Test the RecordOperation delete()."""
        self.assert_record_method_is_passthrough("delete", "delete", 1,
                                                 has_result=False)

    def test_update_record(self):
        """Test the RecordOperation update()."""
        self.assert_record_method_is_passthrough("update", "update", 1,
                                                 has_result=False)

    def test_delete_relationship(self):
        """Test the RelationshipOperation delete()."""
        # We need to test that args are properly kwarg'd to reorder
        # Same reorder that happens for .get() but no return value
        self.relationship_dao.delete = Mock(return_value=None)
        args = ("some_msub", "submits", "some_run")
        expected_kwargs = {"subject_id": "some_msub",
                           "object_id": "some_run",
                           "predicate": "submits"}
        actual_result = self.datastore.relationships.delete(*args)
        self.assertIs(actual_result, None)
        self.relationship_dao.delete.assert_called_with(**expected_kwargs)
        args = ("some_msub",)
        expected_kwargs = {"subject_id": "some_msub",
                           "object_id": None,
                           "predicate": None}
        actual_result = self.datastore.relationships.delete(*args)
        self.assertIs(actual_result, None)
        self.relationship_dao.delete.assert_called_with(**expected_kwargs)

    def test_insert_relationship(self):
        """Test the RelationshipOperation insert()."""
        self.assert_relationship_method_is_passthrough("insert", "insert",
                                                       num_args=1)

    def test_delete_all_contents(self):
        """Test that DataStore calls the expected delete method."""
        fake_factory = Mock()
        fake_record_dao = Mock()
        fake_factory.create_record_dao = Mock(return_value=fake_record_dao)
        test_ds = DataStore(fake_factory)
        # The function is protected to disincentivize using it from the DAOs.
        # The _record_dao is truly protected, but needed for mocking.
        # pylint: disable=protected-access
        self.assertEqual(test_ds._record_dao, fake_record_dao)
        # keyword-only args will be a nice safety feature when we're Py3 only.
        did_delete = test_ds.delete_all_contents("SKIP PROMPT")
        fake_record_dao._do_delete_all_records.assert_called_once()
        self.assertTrue(did_delete)

    @patch('six.moves.input')
    def test_delete_all_contents_confirmation(self, patched_input):
        """Test that DataStore respects the confirmation "dialog"."""
        expected_factory = Mock()
        fake_record_dao = Mock()
        # Same protected-access reasoning as in the other test of test_delete_all_data_completely
        # pylint: disable=protected-access
        expected_factory.create_record_dao = Mock(return_value=fake_record_dao)
        test_ds = DataStore(expected_factory)
        self.assertEqual(test_ds._record_dao, fake_record_dao)
        # An empty "confirmation" should not result in a deletion.
        patched_input.return_value = ""
        did_delete = test_ds.delete_all_contents()
        fake_record_dao._do_delete_all_records.assert_not_called()
        self.assertFalse(did_delete)
        # An incorrect "confirmation" should not result in a deletion.
        patched_input.return_value = "delete all data"
        did_delete = test_ds.delete_all_contents()
        fake_record_dao._do_delete_all_records.assert_not_called()
        self.assertFalse(did_delete)
        # Only the correct phrase should result in a deletion.
        patched_input.return_value = "DELETE ALL DATA"
        did_delete = test_ds.delete_all_contents()
        fake_record_dao._do_delete_all_records.assert_called_once()
        self.assertTrue(did_delete)

    def test_read_only_attribute(self):
        """Verify that read_only is False on read-only data stores."""
        self.assertFalse(self.datastore.read_only)


class CreateDatastore(unittest.TestCase):
    """
    These tests can't be separated from the concept of a backend.

    Basically, we test that a specific DAOFactory method is called under the
    expected conditions.
    """

    @patch('sina.datastore.ReadOnlyDataStore.__init__')
    @patch('sina.datastore.DataStore.__init__')
    @patch('sina.datastores.sql.DAOFactory.__init__')
    def test_connect_sql_datastore(self, mock_factory_init, mock_datastore_init,
                                   mock_read_only_store_init):
        """Make sure connect() targets the backend when appropriate."""
        # Python gets confused if __init__ returns a MagicMock
        mock_factory_init.return_value = None
        # Because of that, we have to short-circuit the other init, too.
        mock_datastore_init.return_value = None
        mock_read_only_store_init.return_value = None
        connect()
        self.assertEqual(mock_factory_init.call_count, 1)
        self.assertEqual(mock_datastore_init.call_count, 1)
        self.assertEqual(mock_read_only_store_init.call_count, 0)
        connect("127.0.0.1")
        self.assertEqual(mock_factory_init.call_count, 2)
        self.assertEqual(mock_datastore_init.call_count, 2)
        self.assertEqual(mock_read_only_store_init.call_count, 0)
        connect(database_type="sql")
        self.assertEqual(mock_factory_init.call_count, 3)
        self.assertEqual(mock_datastore_init.call_count, 3)
        self.assertEqual(mock_read_only_store_init.call_count, 0)
        connect(read_only=True)
        self.assertEqual(mock_factory_init.call_count, 4)
        self.assertEqual(mock_datastore_init.call_count, 3)
        self.assertEqual(mock_read_only_store_init.call_count, 1)

    @pytest.mark.cassandra
    @patch('sina.datastore.DataStore.__init__')
    @patch('sina.datastores.cass.DAOFactory.__init__')
    def test_connect_cass_datastore(self, mock_factory_init,
                                    mock_datastore_init):
        """Make sure connect() targets the backend when appropriate."""
        mock_factory_init.return_value = None
        mock_datastore_init.return_value = None
        connect()
        connect("127.0.0.1")
        self.assertEqual(mock_factory_init.call_count, 0)
        connect(keyspace="my cool keyspace")
        self.assertEqual(mock_factory_init.call_count, 1)
        connect(database_type="cassandra",
                keyspace="my other cool keyspace")
        self.assertEqual(mock_factory_init.call_count, 2)
        with self.assertRaises(ValueError) as context:
            connect(database_type="cassandra")
        self.assertIn('keyspace must be provided', str(context.exception))
        self.assertEqual(mock_factory_init.call_count, 2)

    @patch('sina.datastore.connect')
    def test_create_datastore_sql_datastore(self, mock_connect):
        """Verify create_datastore() delegates to connect()."""
        expected_result = object()
        mock_connect.return_value = expected_result
        result = create_datastore(database='my_db', keyspace='my_keyspace',
                                  database_type='my_type',
                                  allow_connection_pooling=True)
        mock_connect.assert_called_with(
            database='my_db', keyspace='my_keyspace', database_type='my_type',
            allow_connection_pooling=True)
        self.assertEqual(expected_result, result)

    def test_connect_defined_at_sina(self):
        """Verify sina.connect() is defined and the same as sina.datastore.connect()"""
        self.assertEqual(sina.connect, sina.datastore.connect)
