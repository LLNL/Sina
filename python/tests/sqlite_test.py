#!/bin/python
"""Runs the tests contained in backend_test.py on the SQL backend."""

import os
import time
import unittest
import mock  # pylint: disable=import-error

import sina.datastores.sql as backend
from sina.datastore import create_datastore

import tests.backend_test
import tests.datastore_test


def test_close():
    """Test that closing the factory closes the connection."""
    factory = backend.DAOFactory()
    with mock.patch.object(factory.session, 'close', wraps=factory.session.close) as close:
        factory.close()
        close.assert_called()


# Disable pylint no-init check just on the Mixin class, since it has no use
# for an __init__ and there is no expectation of adding more public methods.
class SQLMixin(object):  # pylint: disable=no-init,too-few-public-methods
    """Contains the methods shared between all test classes."""

    __test__ = False
    # Ensure the selected backend is passed to child tests.
    backend = backend

    @classmethod
    def create_dao_factory(cls, test_db_dest=None):
        """
        Create a DAO for the SQL backend.

        This is None (in-memory db) by default, but due to issues cascading
        deletes on in-memory dbs, a filepath can be provided.

        :param test_db_dest: The database that the DAOFactory should target.
        """
        return backend.DAOFactory(test_db_dest)


class TestSetup(SQLMixin, unittest.TestCase):
    """Provides methods needed for setup-type tests on the SQL backend."""

    def test_factory_instantiate_file(self):
        """Test to ensure SQL DAOFactory is able to create files."""
        test_db = './test_{}_file.temp'.format(time.time())
        try:
            self.create_dao_factory(test_db)
            self.assertTrue(os.path.isfile(test_db))
        finally:
            tests.backend_test.remove_file(test_db)


class TestModify(SQLMixin, tests.backend_test.TestModify):
    """
    Provides methods needed for modify-type tests on the SQL backend.

    Also runs any modify-type tests that are unique to SQL.
    """

    __test__ = True


class TestQuery(SQLMixin, tests.backend_test.TestQuery):
    """
    Provides methods needed for query-type tests on the SQL backend.

    Also runs any query-type tests that are unique to SQL.
    """

    __test__ = True


class TestImportExport(SQLMixin, tests.backend_test.TestImportExport):
    """
    Provides methods needed for import/export-type tests on the SQL backend.

    Also runs any import/export-type tests that are unique to SQL.
    """

    __test__ = True


class TestDataStore(SQLMixin, tests.datastore_test.BackendSpecificTests):
    """Tests that DataStores are using this backend correctly."""

    __test__ = True

    @staticmethod
    def create_backend_datastore():
        """Create an in-memory db for a datastore."""
        return create_datastore()

    @mock.patch('sina.datastore.DataStore.__init__')
    @mock.patch('sina.datastores.sql.DAOFactory.__init__')
    def test_create_datastore(self, mock_dao, mock_ds):
        """Test that SQL Datastores are created when expected."""
        # Python gets confused if __init__ returns a MagicMock
        mock_dao.return_value = None
        mock_ds.return_value = None
        # Empty args
        create_datastore()
        self.assertTrue(mock_dao.called)
        mock_args, mock_kwargs = mock_dao.call_args
        self.assertEqual(mock_args, (None,))
        self.assertFalse(mock_kwargs)
        # Backend specified
        create_datastore(database_type="sql")
        self.assertEqual(mock_dao.call_count, 2)
        mock_args, mock_kwargs = mock_dao.call_args
        self.assertEqual(mock_args, (None,))
        self.assertFalse(mock_kwargs)
        # destination specified but no keystore
        database = "mock_stops_me_from_being_created.sqlite"
        create_datastore(database)
        self.assertEqual(mock_dao.call_count, 3)
        mock_args, mock_kwargs = mock_dao.call_args
        self.assertEqual(mock_args, (database,))
        self.assertFalse(mock_kwargs)
