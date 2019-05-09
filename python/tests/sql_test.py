#!/bin/python
"""Runs the tests contained in backend_test.py on the SQL backend."""

import os
import time
import tempfile

import tests.backend_test
import sina.datastores.sql as backend


# Disable pylint no-init check just on the Mixin class, since it has no use
# for an __init__, and too-few-public-methods.
# Also disable pylint
class SQLMixin(object):  # pylint: disable=W0232,R0903
    """Contains the methods shared between all test classes."""

    __test__ = False
    # Ensure the selected backend is passed to child tests.
    backend = backend

    # This has to be a classmethod because it's called before instantiation
    # (See TestQuery)
    @classmethod
    def create_dao_factory(cls, test_db_dest=None):
        """
        Create a DAO for the SQL backend.

        This is None (in-memory db) by default, but due to issues cascading
        deletes on in-memory dbs, a filepath can be provided.

        :param test_db_dest: The database that the DAOFactory should target.
        """
        return backend.DAOFactory(test_db_dest)


class TestSetup(SQLMixin, tests.backend_test.TestSetup):
    """
    Provides methods needed for setup-type tests on the SQL backend.

    Also runs any setup-type tests that are unique to SQL.
    """

    __test__ = True

    def setUp(self):
        """Define a few shared variables, such as temp files."""
        self.test_db_dest = './test_{}_file.temp'.format(time.time())

    def tearDown(self):
        """Remove any temp files created during test."""
        try:
            os.remove(self.test_db_dest)
        except OSError:
            pass

    def test_factory_instantiate_file(self):
        """Test to ensure SQL DAOFactory is able to create files."""
        self.create_dao_factory(self.test_db_dest)
        self.assertTrue(os.path.isfile(self.test_db_dest))


class TestModify(SQLMixin, tests.backend_test.TestModify):
    """
    Provides methods needed for modify-type tests on the SQL backend.

    Also runs any modify-type tests that are unique to SQL.
    """

    __test__ = True

    def setUp(self):
        """Define a few shared variables, such as temp files."""
        # Paths are needed for SQL because cascading on an in-memory db always fails.
        # Found no documentation on workarounds.
        self.test_db_dest = './test_{}_file.temp'.format(time.time())

    def tearDown(self):
        """Remove any temp files created during test."""
        try:
            os.remove(self.test_db_dest)
        except OSError:
            pass


class TestQuery(SQLMixin, tests.backend_test.TestQuery):
    """
    Provides methods needed for query-type tests on the SQL backend.

    Also runs any query-type tests that are unique to SQL.
    """

    __test__ = True

    @classmethod
    def setUpClass(cls):
        """Create the connection and populate it."""
        cls.factory = cls.create_dao_factory()
        cls.record_dao = cls.factory.create_record_dao()
        cls.run_dao = cls.factory.create_run_dao()
        cls.relationship_dao = cls.factory.create_relationship_dao()
        tests.backend_test.populate_database_with_data(cls.record_dao)


class TestImportExport(SQLMixin, tests.backend_test.TestImportExport):
    """
    Provides methods needed for import/export-type tests on the SQL backend.

    Also runs any import/export-type tests that are unique to SQL.
    """

    __test__ = True

    def setUp(self):
        """Define a few shared variables, such as temp files."""
        self.test_file_path = tempfile.NamedTemporaryFile(suffix='.csv',
                                                          delete=False,
                                                          mode='w+b')

    def tearDown(self):
        """Remove any temp files created during test."""
        try:
            os.remove(self.test_file_path.name)
        except OSError:
            pass
