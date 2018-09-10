"""Tests for the CLI."""
import unittest
import os
import json
from mock import patch, MagicMock
from nose.plugins.attrib import attr

from sina import launcher
from sina.datastores import sql as sina_sql
from sina.datastores import cass as sina_cass
from sina.utils import ScalarRange, import_json, _process_relationship_entry

TEMP_DB_NAME = "temp_sqlite_testfile.sqlite"


class TestCLI(unittest.TestCase):
    """Tests for the CLI correctly interpreting args."""

    def setUp(self):
        """Prepare for each test by initializing parser and preparing args."""
        self.parser = launcher.setup_arg_parser()
        # We need to provide initial minimal args, but will change per test
        self.args = self.parser.parse_args(['ingest', '-d', 'null.sqlite',
                                            'null.json'])
        self.created_db = "fake.sqlite"

    @patch('sina.launcher.import_json', return_value=True)
    def test_ingest_json_sql(self, mock_import):
        """Verify CLI fetches and feeds json to the importer (sql)."""
        self.args.source = "fake.json"
        self.args.database_type = 'sql'
        self.args.database = self.created_db
        launcher.ingest(self.args)
        mock_import.assert_called_once()
        mock_args = mock_import.call_args[1]  # Named args
        self.assertIsInstance(mock_args['factory'], sina_sql.DAOFactory)
        self.assertEqual(mock_args['factory'].db_path, self.created_db)
        self.assertEqual(mock_args['json_path'], self.args.source)

    @attr('cassandra')
    @patch('sina.launcher.import_json', return_value=True)
    @patch('sina.datastores.cass.schema.form_connection', return_value=True)
    def test_ingest_json_cass(self, mock_connect, mock_import):
        """Verify CLI fetches and feeds json to the importer (cass)."""
        self.args.source = "fake.json"
        self.args.database_type = 'cass'
        self.args.cass_keyspace = 'fake'
        self.args.database = 'not.a.i.p'
        launcher.ingest(self.args)
        mock_import.assert_called_once()
        mock_args = mock_import.call_args[1]  # Named args
        self.assertIsInstance(mock_args['factory'], sina_cass.DAOFactory)
        self.assertEqual(mock_args['factory'].keyspace,
                         self.args.cass_keyspace)
        self.assertEqual(mock_args['json_path'], self.args.source)
        self.args.cass_keyspace = None
        # Ingesting without keyspace shouldn't result in another call
        with self.assertRaises(ValueError) as context:
            launcher.ingest(self.args)
        self.assertIn("not provided. In the future", str(context.exception))
        mock_import.assert_called_once()

    def test_ingest_local_ids(self):
        """Verify importer is correctly substituting local IDs for globals."""
        test_json = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 "test_files/mnoda_1.json")
        factory = sina_sql.DAOFactory()
        import_json(factory=factory, json_path=test_json)
        local_rec = factory.createRecordDAO().get_all_of_type("eggs")
        global_id = local_rec[0].record_id
        relationship = (factory.createRelationshipDAO()
                               ._get_given_object_id(global_id))
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

    @patch('sina.launcher.import_json', return_value=True)
    def test_ingest_error_messages(self, mock_import):
        """Verify that the ingest subcommand prints the right errors."""
        self.args.source = "fake.null"
        self.args.database = "also_fake.null"
        with self.assertRaises(ValueError) as context:
            launcher.ingest(self.args)
        self.assertIn("--source-type not provided", str(context.exception))
        self.assertIn("not provided and unable", str(context.exception))
        self.args.source = "fake.cass"
        self.args.database = "also_fake.cass"
        with self.assertRaises(ValueError) as context:
            launcher.ingest(self.args)
        self.assertIn("only json is supported", str(context.exception))
        self.assertIn("only cass and sql are supported for ingesting",
                      str(context.exception))
        mock_import.assert_not_called()

    @patch('sina.launcher.sql.RecordDAO.get_given_document_uri',
           return_value=[MagicMock(raw='hello')])
    @patch('sina.launcher.sql.RecordDAO.get_given_scalars',
           return_value=[MagicMock(raw='hello', record_id='general')])
    def test_query_sql(self, mock_scalars, mock_uri):
        """Verify CLI fetches and feeds query info to the DAO (sql)."""
        self.args.database_type = 'sql'
        self.args.raw = ""
        self.args.uri = ""
        self.args.id = False
        self.args.database = 'fake.sqlite'
        self.args.scalar = 'somescalar=[1,2]'
        launcher.query(self.args)
        # As long as this is called, we know we correctly used sql
        mock_scalars.assert_called_once()
        mock_args = mock_scalars.call_args[1]  # Named args
        self.assertIsInstance(mock_args['scalar_range_list'][0], ScalarRange)
        self.assertEqual(len(mock_args['scalar_range_list']), 1)
        self.args.uri = 'somedoc.png'
        launcher.query(self.args)
        mock_uri.assert_called_once()
        mock_uri_args = mock_uri.call_args[1]  # Named args
        self.assertEqual(mock_uri_args['uri'], self.args.uri)
        self.assertEqual(mock_uri_args['accepted_ids_list'][0],
                         mock_scalars.return_value[0].record_id)

    @attr('cassandra')
    @patch('sina.launcher.cass.RecordDAO.get_given_document_uri',
           return_value=[MagicMock(raw='hello')])
    @patch('sina.launcher.cass.RecordDAO.get_given_scalars',
           return_value=[MagicMock(raw='hello', record_id='general')])
    @patch('sina.datastores.cass.schema.form_connection', return_value=True)
    def test_query_cass(self, mock_connect, mock_scalars, mock_uri):
        """Verify CLI fetches and feeds query info to the DAO (cass)."""
        self.args.database_type = 'cass'
        self.args.raw = ""
        self.args.uri = ""
        self.args.id = False
        self.args.database = 'not.an.i.p'
        self.args.cass_keyspace = 'fake'
        self.args.scalar = 'somescalar=[1,2]'
        launcher.query(self.args)
        # As long as these are called, we know we correctly used cass
        mock_connect.assert_called_once()
        mock_scalars.assert_called_once()
        mock_args = mock_scalars.call_args[1]  # Named args
        self.assertIsInstance(mock_args['scalar_range_list'][0], ScalarRange)
        self.assertEqual(len(mock_args['scalar_range_list']), 1)
        self.args.uri = 'somedoc.png'
        launcher.query(self.args)
        mock_uri.assert_called_once()
        mock_uri_args = mock_uri.call_args[1]  # Named args
        self.assertEqual(mock_uri_args['uri'], self.args.uri)
        self.assertEqual(mock_uri_args['accepted_ids_list'][0],
                         mock_scalars.return_value[0].record_id)

    @patch('sina.launcher.cass.RecordDAO.get_given_document_uri')
    @patch('sina.launcher.sql.RecordDAO.get_given_document_uri')
    def test_query_error_messages(self, mock_sql_query, mock_cass_query):
        """Verify that the query subcommand prints the right errors."""
        self.args.source = "fake.null"
        self.args.database = "also_fake.null"
        self.args.raw = ""
        self.args.uri = ""
        self.args.id = False
        self.args.scalar = ""
        with self.assertRaises(ValueError) as context:
            launcher.query(self.args)
        self.assertIn("not provided and unable", str(context.exception))
        self.assertIn("You must specify a query type!", str(context.exception))
        mock_sql_query.assert_not_called()
        self.args.source = "fake.cass"
        self.args.database = "also_fake.cass"
        self.args.raw = "hello there"
        self.args.scalar = "somescalar=[1,2]"
        with self.assertRaises(ValueError) as context:
            launcher.query(self.args)
        self.assertIn("Raw queries don't support additional query",
                      str(context.exception))
        mock_cass_query.assert_not_called()
