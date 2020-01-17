#!/bin/python
"""Runs the tests contained in backend_test.py on the SQL backend."""

import os
import time
import unittest
import mock  # pylint: disable=import-error

import tests.backend_test
import sina.datastores.sql as backend


def test_close():
    """Test that closing the factory closes the connection"""
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
    """
    Provides methods needed for setup-type tests on the SQL backend.
    """

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
