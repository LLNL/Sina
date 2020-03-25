"""Tests for the CLI."""
import unittest
import os
import sys
import json
import argparse

from six.moves import cStringIO as StringIO

# Disable pylint checks due to its issue with virtual environments
from mock import patch, MagicMock  # pylint: disable=import-error
from nose.plugins.attrib import attr  # pylint: disable=import-error
from sqlalchemy.orm.exc import NoResultFound  # pylint: disable=import-error

from sina.cli import driver
from sina.datastores import sql as sina_sql
from sina.utils import DataRange, import_json, _process_relationship_entry

try:
    from sina.datastores import cass as sina_cass
except ImportError:
    # Not having Cassandra or cli_tools for tests is a valid case and should be
    # coupled with (an) appropriate flag(s) for Nose. If not, another error will
    # be raised, and this case is addressed there.
    pass

TEMP_DB_NAME = "temp_sqlite_testfile.sqlite"

# Accessing "private" methods is necessary for testing them.
# pylint: disable=protected-access


class TestCLI(unittest.TestCase):
    """Tests for the CLI correctly interpreting args."""

    def setUp(self):
        """Prepare for each test by initializing parser and preparing args."""
        self.parser = driver.setup_arg_parser()
        # We need to provide initial minimal args, but will change per test
        self.args = self.parser.parse_args(['ingest', '-d', 'null.sqlite',
                                            'null.json'])
        self.created_db = "fake.sqlite"
        self.temp_parser = argparse.ArgumentParser(prog='sina_tester',
                                                   description='A software package to process '
                                                   'data stored in the sina_model format.',
                                                   formatter_class=argparse.RawTextHelpFormatter)
        self.subparsers = self.temp_parser.add_subparsers(
            title='subcommands', help='Available sub-commands.', dest='subparser_name')
        self.temp_subparser = self.subparsers.add_parser('eat', help='eat some food.')

    @patch('sina.cli.driver.import_json', return_value=True)
    def test_ingest_json_sql(self, mock_import):
        """Verify CLI fetches and feeds json to the importer (sql)."""
        self.args.source = "fake.json"
        self.args.database_type = 'sql'
        self.args.database = self.created_db
        driver.ingest(self.args)
        mock_import.assert_called_once()
        mock_args = mock_import.call_args[1]  # Named args
        self.assertIsInstance(mock_args['factory'], sina_sql.DAOFactory)
        self.assertEqual(mock_args['factory'].db_path, self.created_db)
        self.assertEqual(mock_args['json_paths'], [self.args.source])

    @attr('cassandra')
    @patch('sina.cli.driver.import_json', return_value=True)
    @patch('sina.datastores.cass.schema.form_connection', return_value=True)
    def test_ingest_json_cass(self, mock_connect, mock_import):
        """Verify CLI fetches and feeds json to the importer (cass)."""
        self.args.source = "fake.json"
        self.args.database_type = 'cass'
        self.args.cass_keyspace = 'fake'
        self.args.database = 'not.a.i.p'
        driver.ingest(self.args)
        mock_import.assert_called_once()
        mock_connect.assert_called_once()
        mock_args = mock_import.call_args[1]  # Named args
        self.assertIsInstance(mock_args['factory'], sina_cass.DAOFactory)
        self.assertEqual(mock_args['factory'].keyspace,
                         self.args.cass_keyspace)
        self.assertEqual(mock_args['json_paths'], [self.args.source])
        self.args.cass_keyspace = None
        # Ingesting without keyspace shouldn't result in another call
        with self.assertRaises(ValueError) as context:
            driver.ingest(self.args)
        self.assertIn("not provided. In the future", str(context.exception))
        mock_import.assert_called_once()

    def test_ingest_local_ids(self):
        """Verify importer is correctly substituting local IDs for globals."""
        test_json = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 "../test_files/sample_doc_1.json")
        factory = sina_sql.DAOFactory()
        import_json(factory=factory, json_paths=test_json)
        local_rec = list(factory.create_record_dao().get_all_of_type("eggs"))
        global_id = local_rec[0].id
        relationship = (factory.create_relationship_dao().get(object_id=global_id))
        self.assertEqual(len(relationship), 1)
        # Tested relationship: (local_id is local_id). makes sure local
        # subjects and objects are both replaced correctly
        self.assertEqual(relationship[0].subject_id, global_id)

    def test_ingest_local_id_errors(self):
        """Verify that issues with local_ids raise the correct errors."""
        no_subject = ('{"relationships":[{"object":"foo","predicate":"bar"}]}')
        local_ids = {"foo": "global_foo"}
        with self.assertRaises(ValueError) as context:
            _process_relationship_entry(
                entry=json.loads(no_subject)['relationships'][0],
                local_ids=local_ids)
        self.assertIn("requires one of: subject", str(context.exception))
        no_object = ('{"relationships":[{"subject":"foo","predicate":"bar"}]}')
        with self.assertRaises(ValueError) as context:
            _process_relationship_entry(
                entry=json.loads(no_object)['relationships'][0],
                local_ids=local_ids)
        self.assertIn("requires one of: object", str(context.exception))
        no_global = ('{"relationships":[{"local_subject":"foo"'
                     ',"predicate":"bar","local_object":"spam"}]}')
        with self.assertRaises(ValueError) as context:
            _process_relationship_entry(
                entry=json.loads(no_global)['relationships'][0],
                local_ids=local_ids)
        self.assertIn("Local_subject and/or local_object must be",
                      str(context.exception))

    @patch('sina.cli.driver.import_json', return_value=True)
    def test_ingest_error_messages(self, mock_import):
        """Verify that the ingest subcommand prints the right errors."""
        self.args.source = "fake.null"
        self.args.database = "also_fake.null"
        with self.assertRaises(ValueError) as context:
            driver.ingest(self.args)
        self.assertIn("--source-type not provided", str(context.exception))
        self.assertIn("not provided and unable", str(context.exception))
        self.args.source = "fake.cass"
        self.args.database = "also_fake.cass"
        with self.assertRaises(ValueError) as context:
            driver.ingest(self.args)
        self.assertIn("only json is supported", str(context.exception))
        self.assertIn("only cass and sql are supported for ingesting",
                      str(context.exception))
        mock_import.assert_not_called()

    @patch('sina.cli.driver.sql.RecordDAO.get_given_document_uri',
           return_value=[MagicMock(raw='hello')])
    @patch('sina.cli.driver.sql.RecordDAO.get_given_data',
           return_value=["hello_there"])
    @patch('sina.cli.driver.sql.RecordDAO.get',
           return_value=[MagicMock(raw='greetings', id='hello_there')])
    def test_query_sql(self, mock_get, mock_get_given_data, mock_uri):
        """Verify CLI fetches and feeds query info to the DAO (sql)."""
        self.args.database_type = 'sql'
        self.args.raw = ""
        self.args.uri = ""
        self.args.id = False
        self.args.database = 'fake.sqlite'
        self.args.scalar = 'somescalar=[1,2]'
        driver.query(self.args)
        # As long as this is called, we know we correctly used sql
        mock_get_given_data.assert_called_once()
        mock_args = mock_get_given_data.call_args[1]  # Named args
        self.assertIsInstance(mock_args['somescalar'], DataRange)
        self.assertEqual(len(mock_args), 1)
        mock_get.assert_called_once()
        positional_args = mock_get.call_args[0][0]
        self.assertEqual(positional_args,
                         mock_get_given_data.return_value)
        self.args.uri = 'somedoc.png'
        driver.query(self.args)
        mock_uri.assert_called_once()
        mock_uri_args = mock_uri.call_args[1]  # Named args
        self.assertEqual(mock_uri_args['uri'], self.args.uri)
        self.assertEqual(mock_uri_args['accepted_ids_list'][0],
                         mock_get_given_data.return_value[0])

    @attr('cassandra')
    @patch('sina.cli.driver.cass.RecordDAO.get_given_document_uri',
           return_value=[MagicMock(raw='hello')])
    @patch('sina.cli.driver.cass.RecordDAO.get_given_data',
           return_value=[MagicMock(raw='hello', id='general')])
    @patch('sina.datastores.cass.schema.form_connection', return_value=True)
    @patch('sina.cli.driver.cass.RecordDAO.get',
           return_value=[MagicMock(raw='greetings', id='hello_there')])
    def test_query_cass(self, mock_get, mock_connect, mock_data, mock_uri):
        """Verify CLI fetches and feeds query info to the DAO (cass)."""
        self.args.database_type = 'cass'
        self.args.raw = ""
        self.args.uri = ""
        self.args.id = False
        self.args.database = 'not.an.i.p'
        self.args.cass_keyspace = 'fake'
        self.args.scalar = 'somescalar=[1,2]'
        driver.query(self.args)
        # As long as these are called, we know we correctly used cass
        mock_connect.assert_called_once()
        mock_data.assert_called_once()
        mock_get.assert_called_once()
        mock_args = mock_data.call_args[1]  # Named args
        self.assertIsInstance(mock_args['somescalar'], DataRange)
        self.assertEqual(len(mock_args.keys()), 1)
        self.args.uri = 'somedoc.png'
        driver.query(self.args)
        mock_uri.assert_called_once()
        mock_uri_args = mock_uri.call_args[1]  # Named args
        self.assertEqual(mock_uri_args['uri'], self.args.uri)
        self.assertEqual(mock_uri_args['accepted_ids_list'][0],
                         mock_data.return_value[0])

    @attr('cassandra')
    @patch('sina.cli.driver.cass.RecordDAO.get_given_document_uri')
    @patch('sina.cli.driver.sql.RecordDAO.get_given_document_uri')
    def test_query_error_messages(self, mock_sql_query, mock_cass_query):
        """Verify that the query subcommand prints the right errors."""
        self.args.source = "fake.null"
        self.args.database = "also_fake.null"
        self.args.raw = ""
        self.args.uri = ""
        self.args.id = False
        self.args.scalar = ""
        with self.assertRaises(ValueError) as context:
            driver.query(self.args)
        self.assertIn("not provided and unable", str(context.exception))
        self.assertIn("You must specify a query type!", str(context.exception))
        mock_sql_query.assert_not_called()
        self.args.source = "fake.cass"
        self.args.database = "also_fake.cass"
        self.args.raw = "hello there"
        self.args.scalar = "somescalar=[1,2]"
        with self.assertRaises(ValueError) as context:
            driver.query(self.args)
        self.assertIn("Raw queries don't support additional query",
                      str(context.exception))
        mock_cass_query.assert_not_called()

    @patch('sina.cli.driver.sql.RecordDAO.get')
    @patch('sina.cli.driver.sina.cli.diff.print_diff_records')
    @attr('cli_tools')
    def test_compare_records_good(self, mock_model_print, mock_get):
        """Verify compare subcommand prints the correct output."""
        self.args.database = "fake.sqlite"
        self.args.id_one = "some_id"
        self.args.id_two = "another_id"
        driver.compare_records(self.args)

        self.assertEqual(mock_get.call_count, 2)

        mock_model_print.assert_called_once()

    @patch('sina.cli.driver.sql.RecordDAO.get')
    @patch('sina.cli.driver.sina.cli.diff.print_diff_records')
    @attr('cli_tools')
    def test_compare_records_bad(self, mock_model_print, mock_get):
        """Verify compare subcommand prints useful error if given a bad id."""
        self.args.database = "fake.sqlite"
        self.args.id_one = "bad_id"
        self.args.id_two = "another_id"
        error_msg = 'Could not find record with id <{}>. Check id and '\
                    'database.'.format(self.args.id_one)
        mock_get.side_effect = NoResultFound(error_msg)

        try:
            # Grab stdout and send to string io
            sys.stdout = StringIO()
            driver.compare_records(self.args)
            std_output = sys.stdout.getvalue().strip()

        finally:
            # Reset stdout
            sys.stdout = sys.__stdout__
        self.assertEqual(mock_model_print.call_count, 0)
        self.assertEqual(std_output, error_msg)

    def test_add_common_args_with_group(self):
        """Given a parser and a group, we add common args to it."""
        # Add a requirement group to a different parser that we pass in to make sure we will use
        # the required group passed in.
        temp_subparser_2 = self.subparsers.add_parser('eat2', help='eat some food again.')
        required_group = temp_subparser_2.add_argument_group("required arguments")
        driver._add_common_args(parser=self.temp_subparser, required_group=required_group)
        actions = self.temp_subparser.__dict__['_option_string_actions']
        temp_subparser_2_actions = temp_subparser_2.__dict__['_option_string_actions']
        self.assertIn('--database', temp_subparser_2_actions.keys())
        self.assertIn('-d', temp_subparser_2_actions.keys())

        self.assertIn('--database-type', actions.keys())
        self.assertIn('--keyspace', actions.keys())
        self.assertTrue(len(actions), 2)

    def test_add_common_args_no_group(self):
        """Given a parser and no group, we add common args to it."""
        # If not given a required group, we create one.
        driver._add_common_args(parser=self.temp_subparser)
        actions = self.temp_subparser.__dict__['_option_string_actions']
        self.assertIn('--database', actions.keys())
        self.assertIn('--database-type', actions.keys())
        self.assertIn('--keyspace', actions.keys())
        self.assertIn('-d', actions.keys())
        self.assertTrue(len(actions), 3)
