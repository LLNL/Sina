#!/bin/python
"""Test a Sina backend."""

import logging
import unittest

# Disable pylint checks due to its issue with virtual environments
from nose.plugins.attrib import attr  # pylint: disable=import-error
from mock import patch  # pylint: disable=import-error

try:
    import cassandra.cqlengine.connection as connection
    import cassandra.cqlengine.management as management

    import sina.datastores.cass as backend

except ImportError:
    # Not having Cassandra for tests is a valid case and should be coupled with
    # an "-a '!cassandra'" flag for Nose. If not, another error will be raised.
    # Even though none of the tests in this file are run with the above flag,
    # Nose doesn't know that initially, and thus tries these imports anyways.
    pass

import tests.backend_test
import tests.datastore_test

# Cassandra's logger is natively Debug, and it's very verbose,
# even at WARNING.
TERSIFY_CASSANDRA_LOGGER = True
# CQLEngine needs a keyspace to start. Will not be edited.
INITIAL_KEYSPACE_NAME = "system_traces"
# Name of keyspace to create and then delete.
TEMP_KEYSPACE_NAME = "temp_keyspace_testing_sina"

# Provided in case tests need to be run on a specific machine. Normally localhost is used.
TESTING_IPS = ('127.0.0.1',)


if TERSIFY_CASSANDRA_LOGGER:
    logging.getLogger("cassandra").setLevel(logging.ERROR)


@attr('cassandra')
# Mixin class, has no use for an __init__.
# pylint: disable=no-init
class CassandraMixin(object):
    """Contains the methods shared between all test classes."""

    __test__ = False
    # Ensure the selected backend is passed to child tests.
    try:
        # Nose will still hit this line even when not running Cassandra tests. If
        # Cassanda isn't installed (see imports block), this will raise a NameError
        backend = backend
    except NameError:
        pass

    # These have to be classmethods because they're called before instantiation
    # (See TestQuery)
    @classmethod
    def create_dao_factory(cls, keyspace=TEMP_KEYSPACE_NAME, test_db_dest=TESTING_IPS):
        """Create a DAO for the Cassandra backend."""
        return backend.DAOFactory(keyspace=keyspace, node_ip_list=test_db_dest)

    @classmethod
    def create_cass_keyspace(cls):
        """
        Create Cassandra's testing keyspace.

        CE Cassandra doesn't currently have in-memory DBs, so we can't just use
        the factory like we do in SQL.
        """
        connection.setup(TESTING_IPS, INITIAL_KEYSPACE_NAME)
        # Make sure the keyspace is empty
        cls.teardown_cass_keyspace()
        management.create_keyspace_simple(TEMP_KEYSPACE_NAME, 1)

    @classmethod
    def teardown_cass_keyspace(cls):
        """Drop the keyspace to start fresh."""
        management.drop_keyspace(TEMP_KEYSPACE_NAME)


@attr('cassandra')
class TestSetup(CassandraMixin, unittest.TestCase):
    """
    Provides methods needed for setup-type tests on the Cassandra backend.
    """

    def setUp(self):
        self.create_cass_keyspace()

    def tearDown(self):
        self.teardown_cass_keyspace()

    @patch('sina.datastores.cass_schema.form_connection', autospec=True)
    def test_factory_production(self, mock_form_conn):
        """Test to ensure Cassandra DAO can connect to non-local IPs."""
        ip_list = ['192.168.1.2:9042']
        with self.create_dao_factory(test_db_dest=ip_list) as factory:
            args, kwargs = mock_form_conn.call_args
            self.assertEqual(args[0], TEMP_KEYSPACE_NAME)
            self.assertEqual(kwargs['node_ip_list'], ip_list)
            self.assertIsInstance(factory, self.backend.DAOFactory)


@attr('cassandra')
class TestModify(CassandraMixin, tests.backend_test.TestModify):
    """
    Provides methods needed for modify-type tests on the Cassandra backend.

    Also runs any modify-type tests that are unique to Cassandra.
    """

    __test__ = True

    def setUp(self):
        """Create a keyspace to modify."""
        self.create_cass_keyspace()
        super(TestModify, self).setUp()

    def tearDown(self):
        """Tear down the keyspace so we can start fresh."""
        self.teardown_cass_keyspace()
        super(TestModify, self).tearDown()


@attr('cassandra')
class TestQuery(CassandraMixin, tests.backend_test.TestQuery):
    """
    Unit tests that specifically deal with queries.

    These tests do not modify the database.
    """

    __test__ = True

    @classmethod
    def setUpClass(cls):
        """Create the connection and populate it."""
        cls.create_cass_keyspace()
        super(TestQuery, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        """Remove connections and keyspaces as needed."""
        super(TestQuery, cls).tearDownClass()
        cls.teardown_cass_keyspace()


@attr('cassandra')
class TestImportExport(CassandraMixin, tests.backend_test.TestImportExport):
    """
    Provides methods needed for import/export-type tests on the Cassandra backend.

    Also runs any import/export-type tests that are unique to Cassandra.
    """

    __test__ = True

    def setUp(self):
        self.create_cass_keyspace()
        super(TestImportExport, self).setUp()

    def tearDown(self):
        self.teardown_cass_keyspace()
        super(TestImportExport, self).tearDown()
