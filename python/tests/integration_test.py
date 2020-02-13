"""Integration tests for the CLI and API working together."""
import ast
import os
import sys
import unittest
import warnings
import json
import io

from six.moves import cStringIO as StringIO

# Disable pylint checks due to its issue with virtual environments
from nose.plugins.attrib import attr  # pylint: disable=import-error
import jsonschema  # pylint: disable=import-error

from sina.cli import driver

try:
    import cassandra.cqlengine.connection as connection
    import cassandra.cqlengine.management as management
except ImportError:
    # Not having Cassandra for tests is a valid case and should be coupled with
    # an "-a '!cassandra'" flag for Nose. If not, another error will be raised,
    # and this case is addressed there.
    pass

TEMP_DB_NAME = "temp_sqlite_testfile.sqlite"
# CQLEngine needs a keyspace to start. Will not be edited.
INITIAL_KEYSPACE_NAME = "system_traces"
# Name of keyspace to create and then delete.
TEMP_KEYSPACE_NAME = "temp_keyspace_testing_sina"


class TestSQLIntegration(unittest.TestCase):
    """SQL tests for how the suite fits together that mimic a user's steps."""

    def setUp(self):
        """Prepare for each test by initializing parser and preparing args."""
        self.parser = driver.setup_arg_parser()
        # We need to provide initial minimal args, but will change per test
        self.args = self.parser.parse_args(['ingest', '-d', 'null.sqlite',
                                            'null.json'])
        self.location = os.path.dirname(os.path.realpath(__file__))
        self.created_db = os.path.join(self.location, TEMP_DB_NAME)
        self.test_files = [os.path.join(self.location,
                                        "test_files/sample_doc_1.json"),
                           os.path.join(self.location,
                                        "test_files/sample_doc_2.json")]

    def tearDown(self):
        """Clean up after each test by removing the created_db tempfile."""
        try:
            os.remove(self.created_db)
        except OSError:
            pass

    def test_file_validity(self):
        """Make sure the files we're importing follow the Sina schema."""
        schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   '../../sina_schema.json')
        with io.open(schema_file, 'r', encoding='utf-8') as schema:
            schema = json.load(schema)
            for test_file in self.test_files:
                with io.open(test_file, 'r', encoding='utf-8') as loaded_test:
                    file_json = json.load(loaded_test)
                    jsonschema.validate(file_json, schema)

    # Create a sql database and query it
    def test_sql_workflow(self):
        """Verify integration between CLI and API for SQL."""
        self.args.source = ",".join(self.test_files)
        self.args.subparser_name = 'ingest'
        self.args.database = self.created_db
        driver.ingest(self.args)
        self.args.subparser_name = 'query'
        self.args.scalar = 'scalar_1=387.6'
        self.args.uri = 'foo.png'
        self.args.raw = ''
        self.args.id = False

        try:
            # Grab stdout and send to string io
            sys.stdout = StringIO()
            driver.query(self.args)
            std_output = sys.stdout.getvalue()
            matches = list(ast.literal_eval(std_output))
            self.assertEqual(len(matches), 2)
            id_list = [matches[0]['id'], matches[1]['id']]
            self.assertIn("child_1", id_list)
            self.assertIn("subset_1", id_list)
        finally:
            # Reset stdout
            sys.stdout = sys.__stdout__

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                sys.stdout = StringIO()
                self.args.scalar = 'scalar-4=0'
                driver.query(self.args)
                std_output = sys.stdout.getvalue()
                matches = ast.literal_eval(std_output)
                self.assertEqual(matches, [])
            finally:
                sys.stdout = sys.__stdout__


@attr('cassandra')
class TestCassIntegration(unittest.TestCase):
    """Cass tests for how the suite fits together that mimic a user's steps."""

    def setUp(self):
        """Prepare for each test by initializing parser and preparing args."""
        self.parser = driver.setup_arg_parser()
        # We need to provide initial minimal args, but will change per test
        self.args = self.parser.parse_args(['ingest', '-d', '127.0.0.1',
                                            'null.json'])
        self.location = os.path.dirname(os.path.realpath(__file__))

    def tearDown(self):
        """Clean up after each test by removing the created_db tempfile."""
        try:
            management.drop_keyspace(TEMP_KEYSPACE_NAME)
        except OSError:
            pass

    # Create a cass database and query it
    def test_cass_workflow(self):
        """Verify integration between CLI and API for Cassandra."""
        # We have to create a keyspace first
        connection.setup(['127.0.0.1'], INITIAL_KEYSPACE_NAME)
        management.create_keyspace_simple(TEMP_KEYSPACE_NAME, 1)
        self.args.source = ",".join([os.path.join(self.location,
                                                  "test_files/sample_doc_1.json"),
                                     os.path.join(self.location,
                                                  "test_files/sample_doc_2.json")])
        self.args.subparser_name = 'ingest'
        self.args.database = '127.0.0.1'
        self.args.database_type = 'cass'
        self.args.cass_keyspace = TEMP_KEYSPACE_NAME
        driver.ingest(self.args)
        self.args.subparser_name = 'query'
        self.args.scalar = 'scalar_1=387.6'
        self.args.uri = 'foo.png'
        self.args.raw = ''
        self.args.id = False

        try:
            # Grab stdout and send to string io
            sys.stdout = StringIO()
            driver.query(self.args)
            std_output = sys.stdout.getvalue()
            matches = ast.literal_eval(std_output)
            self.assertEqual(len(matches), 2)
            id_list = [matches[0]['id'], matches[1]['id']]
            self.assertIn("child_1", id_list)
            self.assertIn("subset_1", id_list)
        finally:
            # Reset stdout
            sys.stdout = sys.__stdout__

        try:
            sys.stdout = StringIO()
            self.args.scalar = 'scalar-4=0'
            driver.query(self.args)
            std_output = sys.stdout.getvalue()
            matches = ast.literal_eval(std_output)
            self.assertEqual(matches, [])
        finally:
            sys.stdout = sys.__stdout__
