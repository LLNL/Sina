"""Test the SQL portion of the DAO structure."""

import os
import unittest
import tempfile
import time
import json
import csv
import logging
from collections import OrderedDict
from mock import MagicMock, patch
import six

import sina.datastores.sql as sina_sql
import sina.datastores.sql_schema as schema
from sina.utils import ScalarRange, import_json, export, _export_csv
from sina.model import Run, Record

LOGGER = logging.getLogger(__name__)


def _populate_database_with_scalars(session):
    """Add test scalars to a database."""
    session.add(schema.ScalarData(id="spam",
                                  name="spam_scal",
                                  value=10,
                                  units="pigs",
                                  tags='["hammy"]'))
    session.add(schema.ScalarData(id="eggs",
                                  name="eggs_scal",
                                  value=0))
    session.add(schema.ScalarData(id="spam",
                                  name="spam_scal_2",
                                  value=200))
    session.add(schema.ScalarData(id="spam2",
                                  name="spam_scal",
                                  value=10.99999))
    session.add(schema.ScalarData(id="spam3",
                                  name="spam_scal",
                                  value=10.5))
    session.add(schema.ScalarData(id="spam3",
                                  name="spam_scal_2",
                                  value=10.5))
    session.commit()


def _populate_database_with_files(session):
    """Add test documents to a database."""
    session.add(schema.Document(id="spam", uri="beep.wav"))
    session.add(schema.Document(id="spam1", uri="beep.wav", tags='["output", "eggs"]'))
    session.add(schema.Document(id="spam2", uri="beep/png"))
    session.add(schema.Document(id="spam3", uri="beeq.png"))
    session.add(schema.Document(id="spam4", uri="beep.png"))
    session.add(schema.Document(id="spam", uri="beep.pong"))
    session.commit()


class TestSQL(unittest.TestCase):
    """Unit tests for the SQL portion of the DAO."""

    def setUp(self):
        """Define a few shared variables, such as temp files."""
        self.test_db_path = './test_{}_file.temp'.format(time.time())
        self.test_file_path = tempfile.NamedTemporaryFile(
            suffix='.csv',
            delete=False,
            mode='w+b')

    def tearDown(self):
        """Remove temp files left over from test."""
        os.remove(self.test_file_path.name)

    # DAOFactory
    def test_factory_instantiate(self):
        """
        Test to ensure DAOFactories can be created.

        Builds two factories: one in memory, one as a file. Test passes if no
        errors are thrown and database file is created.
        """
        sina_sql.DAOFactory()
        self.assertFalse(os.path.isfile(self.test_db_path))
        sina_sql.DAOFactory(self.test_db_path)
        self.assertTrue(os.path.isfile(self.test_db_path))
        os.remove(self.test_db_path)

    def test_factory_production(self):
        """
        Test to ensure DAOFactory can create all required DAOs.

        Tests passes if all required DAOs are created and are of the right
        type.

        Note that, due to use of the abc module in DAOs, this test will fail
        if any of the required DAOs do not implement all required methods.
        """
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        self.assertIsInstance(record_dao, sina_sql.RecordDAO)
        relationship_dao = factory.createRelationshipDAO()
        self.assertIsInstance(relationship_dao, sina_sql.RelationshipDAO)
        run_dao = factory.createRunDAO()
        self.assertIsInstance(run_dao, sina_sql.RunDAO)

    # Importing
    def test_full_import(self):
        """
        Do an import using the utils importer (temporary).

        Acts as a sanity check on all DAOs, though again, should be temporary.
        """
        factory = sina_sql.DAOFactory()
        json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 "test_files/mnoda_1.json")
        import_json(factory=factory, json_path=json_path)
        parent = factory.createRecordDAO().get("parent_1")
        relation = factory.createRelationshipDAO().get(object_id="child_1")
        run_factory = factory.createRunDAO()
        child = run_factory.get("child_1")
        canonical = json.load(open(json_path))
        self.assertEquals(canonical['records'][0]['type'], parent.type)
        self.assertEquals(canonical['records'][1]['application'],
                          child.application)
        child_from_uri = run_factory.get_given_document_uri("foo.png")
        child_scalar = ScalarRange(name="scalar-1", min=387.6,
                                   min_inclusive=True, max=387.6,
                                   max_inclusive=True)
        child_from_scalar = run_factory.get_given_scalar(child_scalar)
        self.assertEquals(canonical['records'][1]['application'],
                          child.application)
        self.assertEquals(child.id, child_from_uri[0].id)
        self.assertEquals(child.id, child_from_scalar[0].id)
        self.assertEquals(canonical['relationships'][0]['predicate'],
                          relation[0].predicate)

    # Exporting
    @patch('sina.utils._export_csv')
    def test_export_csv_good_input_mocked(self, mock):
        """
        Test export with mocked _csv_export() and good input.

        Test export with of one scalar from sql database to a csv file. Mock
        _export_csv() so we don't actually write to file.
        """
        factory = sina_sql.DAOFactory()
        _populate_database_with_scalars(factory.session)
        scalars = ['spam_scal']
        export(
            factory=factory,
            id_list=['spam_scal'],
            scalar_names=scalars,
            output_type='csv',
            output_file=self.test_file_path.name)
        self.assertTrue(mock.called)
        self.assertEqual(mock.call_count, 1)
        args, kwargs = mock.call_args
        self.assertEqual(kwargs['scalar_names'][0], scalars[0])

    @patch('sina.utils._export_csv')
    def test_export_csv_bad_input_mocked(self, mock):
        """
        Test export with mocked _csv_export() and bad input.

        Test export with of one scalar from sql database to a csv file. Mock
        _export_csv() so we don't actually write to file. Bad input in this
        case is an output_type that is not supported.
        """
        factory = sina_sql.DAOFactory()
        _populate_database_with_scalars(factory.session)
        scalars = ['spam_scal']
        with self.assertRaises(ValueError) as context:
            export(
                factory=factory,
                id_list=['spam'],
                scalar_names=scalars,
                output_type='joes_output_type',
                output_file=self.test_file_path.name)
        self.assertIn('Given "joes_output_type" for output_type and it must '
                      'be one of the following: csv',
                      str(context.exception))
        self.assertEqual(mock.call_count, 0)

    def test_export_one_scalar_csv_good_input(self):
        """Test export one scalar correctly to csv from a sql database."""
        factory = sina_sql.DAOFactory()
        _populate_database_with_scalars(factory.session)
        export(
            factory=factory,
            id_list=['spam'],
            scalar_names=['spam_scal'],
            output_type='csv',
            output_file=self.test_file_path.name)

        with open(self.test_file_path.name, 'r') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader]
            self.assertEqual(rows[0], ['id', 'spam_scal'])
            # 10 is stored but 10.0 is retrieved due to SQL column types
            self.assertAlmostEqual(float(rows[1][1]), 10)

    def test_export_two_scalar_csv_good_input(self):
        """Test exporting two scalars & runs correctly to csv from sql."""
        factory = sina_sql.DAOFactory()
        _populate_database_with_scalars(factory.session)
        export(
            factory=factory,
            id_list=['spam3', 'spam'],
            scalar_names=['spam_scal', 'spam_scal_2'],
            output_type='csv',
            output_file=self.test_file_path.name)

        with open(self.test_file_path.name, 'r') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader]
            self.assertEqual(rows[0], ['id',
                                       'spam_scal',
                                       'spam_scal_2'])
            self.assertEqual(rows[1], ['spam3',
                                       '10.5',
                                       '10.5'])
            # AlmostEqual doesn't work with lists, but we expect floats from
            # SQL, hence this workaround
            self.assertEqual(rows[2], ['spam',
                                       '10.0',
                                       '200.0'])

    def test_export_non_existent_scalar_csv(self):
        """Test export for a non existent scalar returns no scalars."""
        export(
            factory=sina_sql.DAOFactory(),
            id_list=['child_1'],
            scalar_names=['bad-scalar'],
            output_type='csv',
            output_file=self.test_file_path.name)

        with open(self.test_file_path.name, 'r') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0], ['id', 'bad-scalar'])

    def test__export_csv(self):
        """Test we can write out data to csv."""
        # Create temp data
        scalar_names = ['fake_scalar_1', 'fake_scalar_2']
        ids = ['a_fake_id_1', 'a_fake_id_2']
        data = OrderedDict()
        data[ids[0]] = [{'name': scalar_names[0], 'value': 123},
                        {'name': scalar_names[1], 'value': 456}]
        data[ids[1]] = [{'name': scalar_names[0], 'value': 0.1},
                        {'name': scalar_names[1], 'value': -12}]
        # Write to csv file
        _export_csv(data=data,
                    scalar_names=scalar_names,
                    output_file=self.test_file_path.name)

        # Validate csv file
        with open(self.test_file_path.name, 'r') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader]
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0], ['id'] + scalar_names)
            self.assertEqual(rows[1], ['a_fake_id_1', '123', '456'])
            self.assertEqual(rows[2], ['a_fake_id_2', '0.1', '-12'])

    # RecordDAO
    def test_recorddao_basic(self):
        """Test that RecordDAO is inserting and getting correctly."""
        record_dao = sina_sql.DAOFactory().createRecordDAO()
        mock_record = MagicMock(id="spam", type="eggs",
                                data=[{"name": "eggs",
                                       "value": 12,
                                       "units": None,
                                       "tags": ["runny"]}],
                                files=[{"uri": "eggs.brek",
                                        "mimetype": "egg",
                                        "tags": ["fried"]}],
                                user_defined={},
                                raw={
                                     "id": "spam",
                                     "type": "eggs",
                                     "user_defined": {},
                                     "data": [{
                                                 "name": "eggs",
                                                 "value": 12,
                                                 "units": "None",
                                                 "tags": ["runny"]
                                                }
                                              ],
                                     "files": [{
                                                 "uri": "eggs.brek",
                                                 "mimetype": "egg",
                                                 "tags": ["fried"]
                                               }
                                               ]
                                })
        record_dao.insert(mock_record)
        returned_record = record_dao.get("spam")
        self.assertEquals(returned_record.id, mock_record.id)
        self.assertEquals(returned_record.type, mock_record.type)
        returned_scalars = record_dao.get_scalars("spam", ["eggs"])
        self.assertEquals(returned_scalars, mock_record.data)
        returned_files = record_dao.get_files("spam")
        self.assertEquals(returned_files, mock_record.files)

        # First test the minimal, JSON-free Record
        pure_obj_record = Record("hello", "there")
        record_dao.insert(pure_obj_record)
        returned_record = record_dao.get("hello")
        self.assertEquals(returned_record.id, pure_obj_record.id)
        self.assertEquals(returned_record.type, pure_obj_record.type)

    def test_recorddao_insert_extras(self):
        """
        Test that RecordDAO is inserting and retrieving files and scalars.

        Doesn't do much testing of functionality, see later tests for that.
        """
        record_dao = sina_sql.DAOFactory().createRecordDAO()
        vals_files = MagicMock(id="spam",
                               type="new_eggs",
                               data=[{"name": "foo", "value": 12},
                                     {"name": "bar", "value": "1",
                                      "tags": ("in")}],
                               files=[{"uri": "ham.png", "mimetype": "png"},
                                      {"uri": "ham.curve", "tags": ["hammy"]}],
                               user_defined={},
                               raw={
                                    "id": "spam",
                                    "type": "new_eggs",
                                    "user_defined": {},
                                    "data": [{
                                                "name": "foo",
                                                "value": 12
                                               },
                                             {
                                                "name": "bar",
                                                "value": "1",
                                                "tags": ["in"]
                                               }
                                             ],
                                    "files": [{
                                                "uri": "ham.png",
                                                "mimetype": "png"
                                              },
                                              {
                                                "uri": "ham.curve",
                                                "tags": ["hammy"]
                                              }
                                              ]
                               })
        record_dao.insert(vals_files)
        scal = ScalarRange(name="foo", min=12, min_inclusive=True,
                           max=12, max_inclusive=True)
        returned_record = record_dao.get_given_scalar(scal)[0]
        self.assertEquals(returned_record.id, vals_files.id)
        no_scal = ScalarRange(name="bar", min=1, min_inclusive=True)
        self.assertFalse(record_dao.get_given_scalar(no_scal))
        file_match = record_dao.get_given_document_uri(uri="ham.png")[0]
        self.assertEquals(file_match.id, vals_files.id)

    @patch(__name__+'.sina_sql.RecordDAO.get')
    def test_recorddao_uri(self, mock_get):
        """Test that RecordDAO is retrieving based on uris correctly."""
        mock_get.return_value = True
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_files(factory.session)
        exact_match = record_dao.get_given_document_uri(uri="beep.png")
        self.assertEqual(len(exact_match), 1)
        end_wildcard = record_dao.get_given_document_uri(uri="beep.%")
        # Note that we're expecting 3 even though there's 4 matches.
        # That's because id "beep" matches twice. So 3 unique.
        # Similar unique-match logic is present in the other asserts
        self.assertEqual(len(end_wildcard), 3)
        mid_wildcard = record_dao.get_given_document_uri(uri="beep%png")
        self.assertEqual(len(mid_wildcard), 2)
        first_wildcard = record_dao.get_given_document_uri(uri="%png")
        self.assertEqual(len(first_wildcard), 3)
        multi_wildcard = record_dao.get_given_document_uri(uri="%.%")
        self.assertEqual(len(multi_wildcard), 4)
        all_wildcard = record_dao.get_given_document_uri(uri="%")
        self.assertEqual(len(all_wildcard), 5)
        ids_only = record_dao.get_given_document_uri(uri="%.%", ids_only=True)
        self.assertEqual(len(ids_only), 4)
        self.assertIsInstance(ids_only, list)
        self.assertIsInstance(ids_only[0], six.string_types)
        six.assertCountEqual(self, ids_only, ["spam", "spam1", "spam3", "spam4"])

    @patch(__name__+'.sina_sql.RecordDAO.get')
    def test_recorddao_scalar(self, mock_get):
        """Test that RecordDAO is retrieving based on scalars correctly."""
        mock_get.return_value = True
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_scalars(factory.session)
        too_big_range = ScalarRange(name="spam_scal", max=9,
                                    max_inclusive=True)
        too_big = record_dao.get_given_scalar(too_big_range)
        self.assertFalse(too_big)
        too_small_range = ScalarRange(name="spam_scal", min=10.99999,
                                      min_inclusive=False)
        too_small = record_dao.get_given_scalar(too_small_range)
        self.assertFalse(too_small)
        just_right_range = ScalarRange(name="spam_scal", min=0,
                                       min_inclusive=True, max=300,
                                       max_inclusive=True)
        just_right = record_dao.get_given_scalar(just_right_range)
        self.assertEqual(len(just_right), 3)
        nonexistant_range = ScalarRange(name="not_here", min=0,
                                        min_inclusive=True, max=300,
                                        max_inclusive=True)
        no_scalar = record_dao.get_given_scalar(nonexistant_range)
        self.assertFalse(no_scalar)
        multi_range = ScalarRange(name="spam_scal")
        multi = record_dao.get_given_scalar(multi_range)
        self.assertEqual(len(multi), 3)
        self.assertEqual(mock_get.call_count, 6)
        ids_only = record_dao.get_given_scalar(multi_range, ids_only=True)
        self.assertEqual(len(ids_only), 3)
        self.assertIsInstance(ids_only, list)
        self.assertIsInstance(ids_only[0], six.string_types)
        six.assertCountEqual(self, ids_only, ["spam", "spam2", "spam3"])

    @patch(__name__+'.sina_sql.RecordDAO.get')
    def test_recorddao_many_scalar(self, mock_get):
        """Test that RecordDAO's retrieving on multiple scalars correctly."""
        mock_get.return_value = True
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_scalars(factory.session)
        spam_and_spam_3 = ScalarRange(name="spam_scal", min=10,
                                      min_inclusive=True)
        spam_3_only = ScalarRange(name="spam_scal_2", max=100)
        one = record_dao.get_given_scalars([spam_and_spam_3,
                                            spam_3_only])
        self.assertEqual(len(one), 1)
        none_fulfill = ScalarRange(name="nonexistant", max=100)
        none = record_dao.get_given_scalars([spam_and_spam_3,
                                             spam_3_only,
                                             none_fulfill])
        self.assertFalse(none)
        id_only = record_dao.get_given_scalars([spam_and_spam_3,
                                                spam_3_only],
                                               ids_only=True)
        self.assertEqual(len(id_only), 1)
        self.assertIsInstance(id_only, list)
        self.assertEqual(id_only[0], "spam3")

    def test_recorddao_type(self):
        """Test the RecordDAO is retrieving based on type correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        mock_rec = MagicMock(id="spam", type="run",
                             application="skillet",
                             raw={
                                    "id": "spam",
                                    "type": "run",
                                    "application": "skillet"
                              })
        mock_rec2 = MagicMock(id="spam2", type="run",
                              application="skillet",
                              raw={
                                    "id": "spam2",
                                    "type": "run",
                                    "application": "skillet"
                               })
        mock_rec3 = MagicMock(id="spam3", type="foo",
                              raw={
                                    "id": "spam3",
                                    "type": "foo",
                              })
        mock_rec4 = MagicMock(id="spam4", type="bar",
                              raw={
                                    "id": "spam4",
                                    "type": "bar",
                              })
        mock_rec5 = MagicMock(id="spam1", type="run",
                              application="skillet",
                              raw={
                                    "id": "spam1",
                                    "type": "run",
                                    "application": "skillet"
                              })
        record_dao.insert(mock_rec)
        record_dao.insert(mock_rec2)
        record_dao.insert(mock_rec3)
        record_dao.insert(mock_rec4)
        record_dao.insert(mock_rec5)
        get_one = record_dao.get_all_of_type("bar")
        self.assertEqual(len(get_one), 1)
        self.assertIsInstance(get_one[0], Record)
        get_many = record_dao.get_all_of_type("run")
        self.assertEqual(len(get_many), 3)
        get_none = record_dao.get_all_of_type("butterscotch")
        self.assertFalse(get_none)
        ids_only = record_dao.get_all_of_type("run", ids_only=True)
        self.assertEqual(len(ids_only), 3)
        self.assertIsInstance(ids_only, list)
        self.assertIsInstance(ids_only[0], six.string_types)
        six.assertCountEqual(self, ids_only, ["spam", "spam1", "spam2"])

    def test_recorddao_get_files(self):
        """Test that the RecordDAO is getting files for records correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_files(factory.session)
        get_one = record_dao.get_files(id="spam1")
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one[0]["uri"], "beep.wav")
        self.assertEqual(get_one[0]["tags"], ["output", "eggs"])
        self.assertFalse(get_one[0]["mimetype"])
        get_more = record_dao.get_files(id="spam")
        self.assertEqual(len(get_more), 2)
        self.assertEqual(get_more[0]["uri"], "beep.pong")

    def test_recorddao_get_scalars(self):
        """
        Test that the RecordDAO is getting scalars for records correctly.

        While covered (mostly) by other tests, it's included for explicity.
        """
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_scalars(factory.session)
        get_one = record_dao.get_scalars(id="spam",
                                         scalar_names=["spam_scal"])
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one[0]["name"], "spam_scal")
        self.assertEqual(get_one[0]["units"], "pigs")
        get_more = record_dao.get_scalars(id="spam",
                                          scalar_names=["spam_scal_2",
                                                        "spam_scal"])
        self.assertEqual(len(get_more), 2)
        self.assertEqual(get_more[0]["name"], "spam_scal")
        self.assertEqual(get_more[0]["tags"], ["hammy"])
        self.assertFalse(get_more[1]["units"])
        self.assertFalse(get_more[1]["tags"])
        get_gone = record_dao.get_scalars(id="spam",
                                          scalar_names=["value-1"])
        self.assertFalse(get_gone)
        get_norec = record_dao.get_scalars(id="wheeee",
                                           scalar_names=["value-1"])
        self.assertFalse(get_norec)

    # RelationshipDAO
    def test_relationshipdao_basic(self):
        """Test that RelationshipDAO is inserting and getting correctly."""
        relationship_dao = sina_sql.DAOFactory().createRelationshipDAO()
        mock_relationship = MagicMock(subject_id="spam",
                                      object_id="eggs",
                                      predicate="loves")
        relationship_dao.insert(mock_relationship)
        subj = relationship_dao.get(subject_id=mock_relationship.subject_id)
        pred = relationship_dao.get(predicate=mock_relationship.predicate)
        obj_pred = relationship_dao.get(object_id=mock_relationship.object_id,
                                        predicate=mock_relationship.predicate)
        full = relationship_dao.get(subject_id=mock_relationship.subject_id,
                                    object_id=mock_relationship.object_id,
                                    predicate=mock_relationship.predicate)
        for relationship_list in (subj, pred, obj_pred, full):
            result = relationship_list[0]
            self.assertEquals(result.subject_id,
                              mock_relationship.subject_id)
            self.assertEquals(result.object_id,
                              mock_relationship.object_id)
            self.assertEquals(result.predicate,
                              mock_relationship.predicate)
        with self.assertRaises(ValueError) as context:
            relationship_dao.insert(subject_id="spam", object_id="eggs")
        self.assertIn('Must supply either', str(context.exception))

    # RunDAO
    def test_runddao_basic(self):
        """Test that RunDAO is inserting and getting correnctly."""
        run_dao = sina_sql.DAOFactory().createRunDAO()
        mock_run = MagicMock(id="spam", application="bar",
                             type="run", user="bep",
                             user_defined={"eggs": "scrambled"}, version=None,
                             raw={
                                    "id": "spam",
                                    "application": "bar",
                                    "type": "run",
                                    "user": "bep",
                                    "user_defined": {
                                        "eggs": "scrambled"
                                    },
                                    "version": None
                                })
        run_dao.insert(mock_run)
        returned_run = run_dao.get("spam")
        self.assertEquals(returned_run.id, mock_run.id)
        self.assertEquals(returned_run.application, mock_run.application)
        self.assertEquals(returned_run.user, mock_run.user)
        self.assertEquals(returned_run.user_defined, mock_run.user_defined)
        self.assertEquals(returned_run.version, mock_run.version)

    def test_rundao_get_scalars(self):
        """
        Test ability to find Runs by scalars.

        The current version inherits from RecordDAO and does only a little
        extra processing, and most of that in _convert_record_to_run. We're
        really just making sure nothing gets lost between those two.
        """
        # TODO: Test raises question of whether type should be tracked in
        # the scalars table.
        factory = sina_sql.DAOFactory()
        _populate_database_with_scalars(factory.session)
        run_dao = factory.createRunDAO()
        mock_rec = MagicMock(id="spam2", type="task",
                             user_defined=None,
                             raw={
                                    "id": "spam2",
                                    "type": "task",
                                    "user_defined": {}
                                })
        run = Run(id="spam", user="bep", application="foo",
                  version="1.2", user_defined={"spam": "eggs"})
        run2 = Run(id="spam3", user="egg", application="foo",
                   version="0.4", user_defined={"eggs": "spam"})
        run_dao.record_DAO.insert(mock_rec)
        run_dao.insert_many([run, run2])
        multi_range = ScalarRange(name="spam_scal")
        multi_scalar = run_dao.get_given_scalar(multi_range)
        self.assertEqual(len(multi_scalar), 2)
        # They're returned in primary key order
        spam_run = multi_scalar[0]
        self.assertEquals(spam_run.user, run.user)
        self.assertEquals(spam_run.raw, run.raw)

    def test_convert_record_to_run_good(self):
        """Test we return a Run when given a Record with valid input."""
        mock_rec = MagicMock(id="spam", type="run",
                             user_defined={},
                             application="skillet",
                             user="bob",
                             version="1.0",
                             raw={
                                    "id": "spam",
                                    "type": "run",
                                    "application": "skillet",
                                    "user": "bob",
                                    "user_defined": {},
                                    "version": "1.0",
                                    "files": [],
                                    "data": []
                                })
        factory = sina_sql.DAOFactory()
        run_dao = factory.createRunDAO()
        converted_run = run_dao._convert_record_to_run(record=mock_rec)
        self.assertEqual(converted_run.raw, mock_rec.raw)
        self.assertEqual(type(converted_run), Run)

    def test_convert_record_to_run_bad(self):
        """Test we raise a ValueError when given a Record with bad input."""
        mock_rec = MagicMock(id="spam", type="task",
                             user_defined={},
                             application="skillet",
                             user="bob",
                             version="1.0",
                             raw={
                                    "id": "spam",
                                    "type": "run",
                                    "application": "skillet",
                                    "user": "bob",
                                    "user_defined": {},
                                    "version": "1.0",
                                    "files": [],
                                    "data": []
                                })
        factory = sina_sql.DAOFactory()
        run_dao = factory.createRunDAO()
        with self.assertRaises(ValueError) as context:
            run_dao._convert_record_to_run(record=mock_rec)
        self.assertIn('Record must be of subtype Run to convert to Run. Given',
                      str(context.exception))
