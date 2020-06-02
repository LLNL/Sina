#!/bin/python
"""Runs the tests contained in backend_test.py on the SQL backend."""

import os
import uuid
import unittest

# Disable pylint checks due to its issue with virtual environments
from nose.plugins.attrib import attr  # pylint: disable=import-error
import sqlalchemy  # pylint: disable=import-error

import sina.datastores.sql as backend
import sina.datastore
import tests.backend_test
import tests.datastore_test


class DBManager(object):
    """
    Manages the creation and deletion of databases.

    Note: The environment variable SINA_MYSQL_TEST_CONNECTION must be
    set to a string which can be passed to sqlalchemy to create a connection
    to the database.
    """

    def __init__(self):
        """
        Create a new DBManager.
        """
        self.db_name = None

    @staticmethod
    def _create_connection():
        """
        Create a connection to the database server.
        """
        connection_string = os.environ['SINA_MYSQL_TEST_CONNECTION']
        engine = sqlalchemy.create_engine(connection_string)
        return engine.connect()

    def create_db(self):
        """
        Create a test database.
        """
        self.db_name = 'test_db_' + uuid.uuid1().hex
        with DBManager._create_connection() as connection:
            connection.execute(sqlalchemy.sql.text('create database {};'.format(self.db_name)))

    def delete_db(self):
        """
        Delete the test database created by create_db().
        """
        with DBManager._create_connection() as connection:
            connection.execute(sqlalchemy.sql.text('drop database {};'.format(self.db_name)))
        self.db_name = None

    def create_dao_factory(self):
        """
        Create a DAO for the SQL backend.
        """
        connection_string = os.environ['SINA_MYSQL_TEST_CONNECTION']
        if '?' not in connection_string:
            connection_string += '?'
        connection_string += '&database=' + self.db_name
        return backend.DAOFactory(connection_string)


# Disable pylint no-init check just on the Mixin class, since it has no use
# for an __init__ and there is no expectation of adding more public methods.
@attr('mysql')
class StaticSQLMixin(unittest.TestCase):  # pylint: disable=no-init,too-few-public-methods
    """
    Contains setUpClass() and tearDownClass() methods for creating and populating a test
    database. Should be used by test classes which only need a single database.
    """

    __test__ = False
    # Ensure the selected backend is passed to child tests.
    backend = backend
    db_manager = None

    @classmethod
    def setUpClass(cls):
        cls.db_manager = DBManager()
        cls.db_manager.create_db()
        super(StaticSQLMixin, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        super(StaticSQLMixin, cls).tearDownClass()
        cls.db_manager.delete_db()

    @classmethod
    def create_dao_factory(cls):
        """
        Create a DAO factory. The caller is responsible for closing it.

        :return: the newly-created factory
        """
        return cls.db_manager.create_dao_factory()


@attr('mysql')
class InstanceSQLMixin(unittest.TestCase):  # pylint: disable=no-init,too-few-public-methods
    """
    Contains setUp() and tearDown() methods for creating and populating a test
    database. Should be used by test classes which need a database per test method.
    """

    __test__ = False
    # Ensure the selected backend is passed to child tests.
    backend = backend

    def setUp(self):
        self.db_manager = DBManager()
        self.db_manager.create_db()
        super(InstanceSQLMixin, self).setUp()

    def tearDown(self):
        super(InstanceSQLMixin, self).tearDown()
        self.db_manager.delete_db()

    def create_dao_factory(self):
        """
        Create a DAO factory. The caller is responsible for closing it.

        :return: the newly-created factory
        """
        return self.db_manager.create_dao_factory()


@attr('mysql')
class TestModify(InstanceSQLMixin, tests.backend_test.TestModify):
    """
    Provides methods needed for modify-type tests on the SQL backend.

    Also runs any modify-type tests that are unique to SQL.
    """

    __test__ = True


@attr('mysql')
class TestQuery(StaticSQLMixin, tests.backend_test.TestQuery):
    """
    Provides methods needed for query-type tests on the SQL backend.

    Also runs any query-type tests that are unique to SQL.
    """

    __test__ = True


@attr('mysql')
class TestImportExport(InstanceSQLMixin, tests.backend_test.TestImportExport):
    """
    Provides methods needed for import/export-type tests on the SQL backend.

    Also runs any import/export-type tests that are unique to SQL.
    """
    __test__ = True


@attr('mysql')
class TestDatastore(InstanceSQLMixin, tests.datastore_test.TestDatastore):
    """Provides methods needed for datastore tests on the MySQL backend."""

    __test__ = True

    def test_identity(self):
        """Test that the DataStore is of the expected type."""
        self.assertIsInstance(self.datastore, sina.datastore.SQLDataStore)
