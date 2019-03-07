"""Test the SQL portion of the DAO structure."""

import os
import unittest
import tempfile
import time
import json
import csv
import logging
import six
from collections import OrderedDict
from mock import MagicMock, patch
import types

import sina.datastores.sql as sina_sql
import sina.datastores.sql_schema as schema
from sina.utils import (DataRange, import_json, export, _export_csv, has_all,
                        has_any, ListQueryOperation)
from sina.model import Run, Record

LOGGER = logging.getLogger(__name__)


def _populate_database_with_data(session):
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
    session.add(schema.ScalarData(id="spam5",
                                  name="spam_scal_3",
                                  value=46))
    session.add(schema.StringData(id="spam1",
                                  name="val_data",
                                  value="runny",
                                  tags='["edible"]'))
    session.add(schema.StringData(id="spam1",
                                  name="val_data_2",
                                  value="double yolks"))
    session.add(schema.StringData(id="spam3",
                                  name="val_data",
                                  value="chewy",
                                  tags='["edible"]'))
    session.add(schema.StringData(id="spam3",
                                  name="val_data_2",
                                  value="double yolks"))
    session.add(schema.StringData(id="spam4",
                                  name="val_data_2",
                                  value="double yolks"))
    session.add(schema.StringData(id="spam5",
                                  name="val_data_3",
                                  value="sugar"))
    session.add(schema.StringData(id="spam6",
                                  name="val_data_3",
                                  value="syrup"))
    # Add some lists
    session.add(schema.ListScalarDataEntry(id="spam5",
                                           name="val_data_list_1",
                                           index=0,
                                           value=0))
    session.add(schema.ListScalarDataEntry(id="spam5",
                                           name="val_data_list_1",
                                           index=1,
                                           value=9.3))
    session.add(schema.ListScalarDataEntry(id="spam6",
                                           name="val_data_list_1",
                                           index=0,
                                           value=8))
    session.add(schema.ListScalarDataEntry(id="spam6",
                                           name="val_data_list_1",
                                           index=1,
                                           value=20))
    session.add(schema.ListStringDataEntry(id="spam5",
                                           name="val_data_list_2",
                                           index=0,
                                           value='eggs'))
    session.add(schema.ListStringDataEntry(id="spam5",
                                           name="val_data_list_2",
                                           index=1,
                                           value='pancake'))
    session.add(schema.ListStringDataEntry(id="spam6",
                                           name="val_data_list_2",
                                           index=0,
                                           value='eggs'))
    session.add(schema.ListStringDataEntry(id="spam6",
                                           name="val_data_list_2",
                                           index=1,
                                           value='yellow'))
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
        """Remove any temp files created during test."""
        try:
            os.remove(self.test_file_path.name)
            os.remove(self.test_db_path)
        except OSError:
            pass

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
        child_from_uri = list(run_factory.get_given_document_uri("foo.png"))
        child_scalar = DataRange(min=387.6,
                                 min_inclusive=True, max=387.6,
                                 max_inclusive=True)
        child_from_scalar_id = list(run_factory.data_query(scalar_1=child_scalar))
        full_record = run_factory.get(child_from_scalar_id[0])
        self.assertEquals(canonical['records'][1]['application'],
                          full_record.application)
        self.assertEquals(child.id, child_from_uri[0].id)
        self.assertEquals(child.id, full_record.id)
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
        _populate_database_with_data(factory.session)
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
        _populate_database_with_data(factory.session)
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
        _populate_database_with_data(factory.session)
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
        _populate_database_with_data(factory.session)
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
        data[ids[0]] = {scalar_names[0]: {'value': 123},
                        scalar_names[1]: {'value': 456}}
        data[ids[1]] = {scalar_names[0]: {'value': 0.1},
                        scalar_names[1]: {'value': -12}}
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
        rec = Record(id="spam", type="eggs",
                     data={"eggs": {"value": 12,
                                    "units": None,
                                    "tags": ["runny"]}},
                     files=[{"uri": "eggs.brek",
                             "mimetype": "egg",
                             "tags": ["fried"]}],
                     user_defined={})
        record_dao.insert(rec)
        returned_record = record_dao.get("spam")
        self.assertEquals(returned_record.id, rec.id)
        self.assertEquals(returned_record.type, rec.type)
        returned_scalars = record_dao.get_scalars("spam", ["eggs"])
        self.assertEquals(returned_scalars, rec.data)
        returned_files = record_dao.get_files("spam")
        self.assertEquals(returned_files, rec.files)

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
        rec = Record(id="spam",
                     type="new_eggs",
                     data={"foo": {"value": 12},
                           "bar": {"value": "1",
                                   "tags": ["in"]}},
                     files=[{"uri": "ham.png", "mimetype": "png"},
                            {"uri": "ham.curve", "tags": ["hammy"]}],
                     user_defined={})
        record_dao.insert(rec)
        returned_record_id = next(record_dao.data_query(foo=12))
        self.assertEquals(returned_record_id, rec.id)
        no_scal = DataRange(min=1, min_inclusive=False)
        self.assertFalse(list(record_dao.data_query(bar=no_scal)))
        file_match = next(record_dao.get_given_document_uri(uri="ham.png"))
        self.assertEquals(file_match.id, rec.id)

    def test_recorddao_delete(self):
        """Test that RecordDAO is deleting correctly."""
        # Cascading on an in-memory db always fails. Found no documentation on it.
        factory = sina_sql.DAOFactory(self.test_db_path)
        record_dao = factory.createRecordDAO()
        relationship_dao = factory.createRelationshipDAO()
        data = {"eggs": {"value": 12, "tags": ["breakfast"]},
                "flavor": {"value": "tasty"}}
        files = [{"uri": "justheretoexist.png"}]

        record_1 = Record(id="rec_1", type="sample", data=data, files=files)
        record_2 = Record(id="rec_2", type="sample", data=data, files=files)
        record_3 = Record(id="rec_3", type="sample", data=data, files=files)
        record_4 = Record(id="rec_4", type="sample", data=data, files=files)
        all_ids = ["rec_1", "rec_2", "rec_3", "rec_4"]
        record_dao.insert_many([record_1, record_2, record_3, record_4])
        relationship_dao.insert(subject_id="rec_1", object_id="rec_2", predicate="dupes")
        relationship_dao.insert(subject_id="rec_2", object_id="rec_2", predicate="is")
        relationship_dao.insert(subject_id="rec_3", object_id="rec_4", predicate="dupes")
        relationship_dao.insert(subject_id="rec_4", object_id="rec_4", predicate="is")

        # Delete one
        record_dao.delete("rec_1")
        remaining_records = list(record_dao.get_all_of_type("sample", ids_only=True))
        self.assertEquals(remaining_records, ["rec_2", "rec_3", "rec_4"])

        # Make sure the relationship was deleted
        self.assertFalse(relationship_dao.get(subject_id="rec_1"))

        # Delete several
        record_dao.delete_many(["rec_2", "rec_3"])
        remaining_records = list(record_dao.get_all_of_type("sample", ids_only=True))
        self.assertEquals(remaining_records, ["rec_4"])

        # Make sure the data, raw, files, and relationships were deleted as well
        for_all = record_dao.get_data_for_records(id_list=all_ids,
                                                  data_list=["eggs", "flavor"])
        for_one = record_dao.get_data_for_records(id_list=["rec_4"],
                                                  data_list=["eggs", "flavor"])
        self.assertEquals(for_all, for_one)
        have_files = list(record_dao.get_given_document_uri("justheretoexist.png",
                                                            ids_only=True))
        self.assertEquals(have_files, ["rec_4"])
        self.assertFalse(relationship_dao.get(object_id="rec_2"))
        self.assertFalse(relationship_dao.get(subject_id="rec_3"))
        self.assertEquals(len(relationship_dao.get(object_id="rec_4")), 1)

    @patch(__name__+'.sina_sql.RecordDAO.get')
    def test_recorddao_uri(self, mock_get):
        """Test that RecordDAO is retrieving based on uris correctly."""
        mock_get.return_value = True
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_files(factory.session)
        exact_match = record_dao.get_given_document_uri(uri="beep.png")
        self.assertEqual(len(list(exact_match)), 1)
        end_wildcard = record_dao.get_given_document_uri(uri="beep.%")
        # Note that we're expecting 3 even though there's 4 matches.
        # That's because id "beep" matches twice. So 3 unique.
        # Similar unique-match logic is present in the other asserts
        self.assertEqual(len(list(end_wildcard)), 3)
        mid_wildcard = record_dao.get_given_document_uri(uri="beep%png")
        self.assertEqual(len(list(mid_wildcard)), 2)
        first_wildcard = record_dao.get_given_document_uri(uri="%png")
        self.assertEqual(len(list(first_wildcard)), 3)
        multi_wildcard = record_dao.get_given_document_uri(uri="%.%")
        self.assertEqual(len(list(multi_wildcard)), 4)
        all_wildcard = record_dao.get_given_document_uri(uri="%")
        self.assertEqual(len(list(all_wildcard)), 5)
        ids_only = record_dao.get_given_document_uri(uri="%.%", ids_only=True)
        self.assertIsInstance(ids_only, types.GeneratorType,
                              "Method must return a generator.")
        ids_only = list(ids_only)
        self.assertEqual(len(ids_only), 4)
        self.assertIsInstance(ids_only[0], six.string_types)
        six.assertCountEqual(self, ids_only, ["spam", "spam1", "spam3", "spam4"])

    def test_recorddao_scalar_data_query(self):
        """Test that RecordDAO is retrieving based one scalar correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        too_big_range = DataRange(max=9, max_inclusive=True)
        too_big = record_dao.data_query(spam_scal=too_big_range)
        self.assertIsInstance(too_big, types.GeneratorType,
                              "Method must return generator.")
        self.assertFalse(list(too_big))
        too_small_range = DataRange(min=10.99999, min_inclusive=False)
        too_small = record_dao.data_query(spam_scal=too_small_range)
        self.assertFalse(list(too_small))
        just_right_range = DataRange(min=0, max=300, max_inclusive=True)
        just_right = record_dao.data_query(spam_scal=just_right_range)
        self.assertEqual(len(list(just_right)), 3)
        no_scalar = record_dao.data_query(nonexistant_scalar=just_right_range)
        self.assertFalse(list(no_scalar))
        multi_range = DataRange(min=-100, max=100)
        multi = record_dao.data_query(spam_scal=multi_range)
        multi_list = list(multi)
        self.assertEqual(len(multi_list), 3)
        six.assertCountEqual(self, multi_list, ["spam", "spam2", "spam3"])

    def test_recorddao_many_scalar_data_query(self):
        """Test that RecordDAO's retrieving on multiple scalars correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        spam_and_spam_3 = DataRange(min=10)
        one = record_dao.data_query(spam_scal=spam_and_spam_3,
                                    spam_scal_2=10.5)  # Matches spam_3 only
        self.assertIsInstance(one, types.GeneratorType,
                              "Method must return a generator.")
        self.assertEqual(len(list(one)), 1)
        none = record_dao.data_query(spam_scal=spam_and_spam_3,
                                     nonexistant=10101010)
        self.assertFalse(list(none))

    def test_recorddao_string_data_query(self):
        """Test that RecordDAO is retrieving based on string(s) correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)

        # With one arg
        too_big_range = DataRange(max="awesome", max_inclusive=True)
        too_big = record_dao.data_query(val_data=too_big_range)
        self.assertIsInstance(too_big, types.GeneratorType,
                              "Method must return generator.")
        self.assertFalse(list(too_big))

        too_small_range = DataRange(min="xtra_crunchy", min_inclusive=False)
        too_small = record_dao.data_query(val_data=too_small_range)
        self.assertFalse(list(too_small))

        just_right_range = DataRange(min="astounding", max="runny", max_inclusive=True)
        just_right = record_dao.data_query(val_data=just_right_range)
        just_right_list = list(just_right)
        self.assertEqual(len(just_right_list), 2)
        six.assertCountEqual(self, just_right_list, ["spam1", "spam3"])

        no_scalar = record_dao.data_query(nonexistant_scalar=just_right_range)
        self.assertFalse(list(no_scalar))

        # With multiple args
        one = record_dao.data_query(val_data=DataRange("runny"),  # Matches 1 only
                                    val_data_2="double yolks")  # Matches 1 and 3
        self.assertEqual(len(list(one)), 1)

    def test_recorddao_data_query_strings_and_records(self):
        """Test that the RecordDAO is retrieving on scalars and strings correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)

        just_3 = record_dao.data_query(spam_scal=DataRange(10.1, 400),  # 2 and 3
                                       val_data_2="double yolks")  # 1, 3, and 4
        just_3_list = list(just_3)
        self.assertEqual(len(just_3_list), 1)
        self.assertEqual(just_3_list[0], "spam3")

    def test_recorddao_data_query_scalar_list_has_all(self):
        """Test that the RecordDAO is retrieving on a list of scalars."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        just_5_and_6 = list(record_dao.data_query(
            val_data_list_1=has_all(DataRange(-10, 8.5), DataRange(8.9, 25))))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_data_query_scalar_list_has_any(self):
        """Test that the RecordDAO is retrieving on a list of scalars."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        just_5_and_6 = list(record_dao.data_query(
            val_data_list_1=has_any(DataRange(-1, 1), DataRange(7.5, 9))))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_data_query_has_all_mixed_1(self):
        """
        Test that the RecordDAO is retrieving on mixed data types.

        Test that we can mix searching on scalars and lists of scalars.
        """
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        just_5 = list(record_dao.data_query(
            val_data_list_1=has_all(DataRange(-10, 8.5), DataRange(8.9, 25)),  # 5 & 6
            spam_scal_3=DataRange(0, 50)))  # 5 only
        self.assertEqual(len(just_5), 1)
        self.assertEqual(just_5[0], "spam5")

    def test_recorddao_data_query_has_any_mixed_1(self):
        """
        Test that the RecordDAO is retrieving on mixed data types.

        Test that we can mix searching on scalars and lists of scalars.
        """
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        just_5 = list(record_dao.data_query(
            val_data_list_1=has_any(DataRange(-1, 1), DataRange(7.5, 9)),  # 5 & 6
            spam_scal_3=DataRange(0, 50)))  # 5 only
        self.assertEqual(len(just_5), 1)
        self.assertEqual(just_5[0], "spam5")

    def test_recorddao_data_query_string_list_has_all(self):
        """Test that the RecordDAO is retrieving on a list of strings."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        just_5_and_6 = list(record_dao.data_query(
            val_data_list_2=has_all('eggs', DataRange('o', 'z'))))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_data_query_string_list_has_any(self):
        """Test that the RecordDAO is retrieving on a list of strings."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        just_5_and_6 = list(record_dao.data_query(
            val_data_list_2=has_any('yellow', 'pancake')))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_data_query_has_all_mixed_2(self):
        """
        Test that the RecordDAO is retrieving on mixed data types.

        Test that we can mix searching on strings and lists of strings.
        """
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        just_6 = list(record_dao.data_query(
            val_data_list_2=has_all('eggs', DataRange('o', 'z')),  # 5 & 6
            val_data_3='syrup'))  # 6 only
        self.assertEqual(len(just_6), 1)
        self.assertEqual(just_6[0], "spam6")

    def test_recorddao_data_query_mixed_3(self):
        """
        Test that the RecordDAO is retrieving on mixed data types.

        Test that we can mix searching on strings, scalars, lists of strings,
        and lists of scalars.
        """
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        no_match = list(record_dao.data_query(
            val_data_list_1=has_all(DataRange(-10, 8.5), DataRange(8.9, 25)),  # 5 & 6
            spam_scal_3=DataRange(0, 50),  # 5 only
            val_data_list_2=has_all('eggs', DataRange('o', 'z')),  # 5 & 6
            val_data_3='syrup'))  # 6 only
        self.assertFalse(no_match)

        just_5 = list(record_dao.data_query(
            val_data_list_1=has_all(DataRange(-10, 8.5), DataRange(8.9, 25)),  # 5 & 6
            spam_scal_3=DataRange(0, 50),  # 5 only
            val_data_list_2=has_all('eggs', DataRange('o', 'z')),  # 5 & 6
            val_data_3='sugar'))  # 5 only

        self.assertEqual(len(just_5), 1)
        self.assertEqual(just_5[0], "spam5")

    def test_recorddao_type(self):
        """Test the RecordDAO is retrieving based on type correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        rec = Record(id="spam",
                     type="run",
                     user_defined={})
        rec2 = Record(id="spam2",
                      type="run",
                      user_defined={})
        rec3 = Record(id="spam3",
                      type="foo",
                      user_defined={})
        rec4 = Record(id="spam4",
                      type="bar",
                      user_defined={})
        rec5 = Record(id="spam1",
                      type="run",
                      user_defined={})
        record_dao.insert(rec)
        record_dao.insert(rec2)
        record_dao.insert(rec3)
        record_dao.insert(rec4)
        record_dao.insert(rec5)
        get_one = list(record_dao.get_all_of_type("bar"))
        self.assertEqual(len(get_one), 1)
        self.assertIsInstance(get_one[0], Record)
        self.assertEqual(get_one[0].id, rec4.id)
        self.assertEqual(get_one[0].type, rec4.type)
        self.assertEqual(get_one[0].user_defined, rec4.user_defined)
        get_many = list(record_dao.get_all_of_type("run"))
        self.assertEqual(len(get_many), 3)
        get_none = list(record_dao.get_all_of_type("butterscotch"))
        self.assertFalse(get_none)
        ids_only = record_dao.get_all_of_type("run", ids_only=True)
        self.assertIsInstance(ids_only, types.GeneratorType,
                              "Method must return a generator.")
        ids_only = list(ids_only)
        self.assertEqual(len(ids_only), 3)
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

    def test_recorddao_get_data_for_records(self):
        """Test that we're getting data for many records correctly."""
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        all_ids = ["spam", "spam2", "spam3", "eggs"]
        all_scalars = ["spam_scal", "eggs_scal", "spam_scal_2", "val_data"]

        for_one = record_dao.get_data_for_records(id_list=["spam"],
                                                  data_list=all_scalars)
        self.assertEqual(for_one["spam"]["spam_scal"],
                         {"value": 10, "units": "pigs", "tags": ["hammy"]})
        self.assertFalse("eggs_scal" in for_one["spam"].keys())

        for_many = record_dao.get_data_for_records(id_list=all_ids,
                                                   data_list=["spam_scal",
                                                              "spam_scal_2",
                                                              "val_data"])
        six.assertCountEqual(self, for_many.keys(), ["spam", "spam2", "spam3"])
        six.assertCountEqual(self, for_many["spam3"].keys(), ["spam_scal",
                                                              "spam_scal_2",
                                                              "val_data"])
        six.assertCountEqual(self, for_many["spam3"]["val_data"].keys(),
                                                    ["value", "tags"])
        self.assertEqual(for_many["spam3"]["val_data"]["value"], "chewy")
        self.assertEqual(for_many["spam3"]["val_data"]["tags"], ["edible"])

        for_none = record_dao.get_data_for_records(id_list=["nope", "nada"],
                                                   data_list=["gone", "away"])
        self.assertFalse(for_none)

    def test_recorddao_get_scalars(self):
        """
        Test that the RecordDAO is getting scalars for a record correctly.

        While covered (mostly) by other tests, it's included for explicity.
        """
        factory = sina_sql.DAOFactory()
        record_dao = factory.createRecordDAO()
        _populate_database_with_data(factory.session)
        get_one = record_dao.get_scalars(id="spam",
                                         scalar_names=["spam_scal"])
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one["spam_scal"]["units"], "pigs")
        get_more = record_dao.get_scalars(id="spam",
                                          scalar_names=["spam_scal_2",
                                                        "spam_scal"])
        self.assertEqual(len(get_more), 2)
        self.assertEqual(get_more["spam_scal"]["tags"], ["hammy"])
        self.assertFalse(get_more["spam_scal_2"]["units"])
        self.assertFalse(get_more["spam_scal_2"]["tags"])
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
        """Test that RunDAO is inserting and getting correctly."""
        run_dao = sina_sql.DAOFactory().createRunDAO()
        run = Run(id="spam", version="1.2.3",
                  application="bar", user="bep",
                  user_defined={"boop": "bep"},
                  data={"scalar-strings": {"value":
                                           ["red", "green", "blue"],
                                           "units": None},
                        "scalar-numbers": {"value": [1, 2, 3],
                                           "units": "m"},
                        "foo": {"value": 12,
                                "units": None,
                                "tags": ["in", "on"]},
                        "bar": {"value": "1",
                                "units": None}},)

        run_dao.insert(run)
        returned_run = run_dao.get("spam")
        self.assertEquals(returned_run.id, run.id)
        self.assertEquals(returned_run.raw, run.raw)
        self.assertEquals(returned_run.application, run.application)
        self.assertEquals(returned_run.user, run.user)
        self.assertEquals(returned_run.user_defined, run.user_defined)
        self.assertEquals(returned_run.version, run.version)
        self.assertEquals(returned_run.data, run.data)

    def test_rundao_delete(self):
        """Test that RunDAO is deleting correctly."""
        factory = sina_sql.DAOFactory(self.test_db_path)
        run_dao = factory.createRunDAO()
        relationship_dao = factory.createRelationshipDAO()

        data = {"eggs": {"value": 12, "tags": ["breakfast"]}}
        files = [{"uri": "justheretoexist.png"}]
        run_1 = Run(id="run_1", application="eggs", data=data, files=files)
        run_2 = Run(id="run_2", application="spam", data=data, files=files)
        run_dao.insert_many([run_1, run_2])
        relationship_dao.insert(subject_id="run_1", object_id="run_2", predicate="dupes")

        # Ensure there's two entries in the Run table
        self.assertEquals(run_dao.session.query(schema.Run).count(), 2)
        # Delete one
        run_dao.delete("run_1")
        # Now there should only be one Run left
        self.assertEquals(run_dao.session.query(schema.Run).count(), 1)
        remaining_runs = list(run_dao.get_all(ids_only=True))
        self.assertEquals(len(remaining_runs), 1)

        # Double check that relationship, data, and files got deleted as well
        self.assertFalse(relationship_dao.get(subject_id="run_1"))
        for_all = run_dao.record_DAO.get_data_for_records(id_list=["run_1", "run_2"],
                                                          data_list=["eggs"])
        for_one = run_dao.record_DAO.get_data_for_records(id_list=["run_2"],
                                                          data_list=["eggs"])
        self.assertEquals(for_all, for_one)
        have_files = list(x.id for x in run_dao.get_given_document_uri("justheretoexist.png"))
        self.assertEquals(have_files, ['run_2'])

    def test_rundao_get_by_scalars(self):
        """
        Test ability to find Runs by scalars.

        The current version inherits from RecordDAO and does only a little
        extra processing, and most of that in _convert_record_to_run. We're
        really just making sure nothing gets lost between those two.
        """
        factory = sina_sql.DAOFactory()
        _populate_database_with_data(factory.session)
        run_dao = factory.createRunDAO()
        rec = Record(id="spam2", type="task",
                     user_defined={})
        run = Run(id="spam", user="bep", application="foo",
                  version="1.2", user_defined={"spam": "eggs"})
        run2 = Run(id="spam3", user="egg", application="foo",
                   version="0.4", user_defined={"eggs": "spam"})
        run_dao.record_DAO.insert(rec)
        run_dao.insert_many([run, run2])
        multi_scalar = list(run_dao.data_query(spam_scal=DataRange(-500, 500)))
        self.assertEqual(len(multi_scalar), 2)
        # No guaranteed order per docs, but we get primary key order here
        spam_run = run_dao.get(multi_scalar[0])
        self.assertEquals(spam_run.user, run.user)
        self.assertEquals(spam_run.raw, run.raw)

    def test_convert_record_to_run_good(self):
        """Test we return a Run when given a Record with valid input."""
        rec = Record(id="spam", type="run")
        rec["user"] = "bob"
        rec["application"] = "skillet"
        rec["version"] = "1.0"
        factory = sina_sql.DAOFactory()
        run_dao = factory.createRunDAO()
        converted_run = run_dao._convert_record_to_run(record=rec)
        self.assertEqual(converted_run.raw, rec.raw)
        self.assertEqual(type(converted_run), Run)

    def test_convert_record_to_run_bad(self):
        """Test we raise a ValueError when given a Record with bad input."""
        rec = Record(id="spam", type="task ")
        rec["user"] = "bob"
        rec["application"] = "skillet"
        rec["version"] = "1.0"
        factory = sina_sql.DAOFactory()
        run_dao = factory.createRunDAO()
        with self.assertRaises(ValueError) as context:
            run_dao._convert_record_to_run(record=rec)
        self.assertIn('Record must be of subtype Run to convert to Run. Given',
                      str(context.exception))


class TestSQLRecordDAOGetList(unittest.TestCase):
    """Unit tests for the SQL.RecordDAO.get_list portion of the DAO."""

    def setUp(self):
        """Set up data for testing get_list."""
        factory = sina_sql.DAOFactory()
        self.record_dao = factory.createRecordDAO()
        data = {"eggs": {"value": [0, 1, 2, 3]}}
        data_2 = {"eggs": {"value": [1, 2, 3, 4, 5]}}
        data_3 = {"eggs": {"value": [4, 5, 6, 7]}}
        data_4 = {"spam": {"value": ["awesome", "canned", "zebra"]}}
        data_5 = {"spam": {"value": ["fried", "toasted", "zebra"]}}
        data_6 = {"spam": {"value": ["tree", "honey"]}}
        self.record_1 = Record(id="rec_1", type="sample", data=data)
        self.record_2 = Record(id="rec_2", type="sample", data=data_2)
        self.record_3 = Record(id="rec_3", type="sample", data=data_3)
        self.record_4 = Record(id="rec_4", type="sample", data=data_4)
        self.record_5 = Record(id="rec_5", type="sample", data=data_5)
        self.record_6 = Record(id="rec_6", type="sample", data=data_6)
        self.record_dao.insert_many(
            [self.record_1, self.record_2, self.record_3,
             self.record_4, self.record_5, self.record_6])

    def test_get_list_all_scal_dr(self):
        """
        Given a list of scalar DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of scalars DataRanges.
        """
        self.list_to_check = [DataRange(0, 2), DataRange(3, 6)]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_2.id in records)
        self.assertTrue(self.record_1.id in records)
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_1.id].raw, self.record_1.raw)
        self.assertEqual(records_to_check[self.record_2.id].raw, self.record_2.raw)

    def test_get_list_all_scalars_scal_dr(self):
        """
        Given a list of scalars/DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of scalars and DataRanges.
        """
        self.list_to_check = [DataRange(0, 3), 4]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 1)
        self.assertEqual(records, [self.record_2.id])
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        self.assertEqual(records[0].raw, self.record_2.raw)

    def test_get_list_all_string_dr(self):
        """
        Given a list of string DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of string DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="c", max_inclusive=True)]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 1)
        self.assertEqual(records, [self.record_4.id])
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        self.assertEqual(records[0].raw, self.record_4.raw)

    def test_get_list_all_string_str_dr_mixed(self):
        """
        Given a list of strings/DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of strings and DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="g", max_inclusive=True), "zebra"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_4.id in records)
        self.assertTrue(self.record_5.id in records)
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_4.id].raw, self.record_4.raw)
        self.assertEqual(records_to_check[self.record_5.id].raw, self.record_5.raw)

    def test_get_list_all_empty_list(self):
        """Given an empty list, we should raise a ValueError."""
        self.list_to_check = []
        with self.assertRaises(ValueError) as context:
            list(self.record_dao.get_list(
                datum_name="spam",
                list_of_contents=self.list_to_check,
                ids_only=True,
                operation=ListQueryOperation.ALL))
        self.assertIn('Must supply at least one entry in list_of_contents for',
                      str(context.exception))

    def test_get_list_all_no_results_string(self):
        """Given a list of data that match no Records, we return no Records."""
        self.list_to_check = ["rhino"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 0)

    def test_get_list_any_scal_dr(self):
        """
        Given a list of scalar DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of scalars DataRanges.
        """
        self.list_to_check = [DataRange(0, 2), DataRange(4, 6)]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 3)
        self.assertTrue(self.record_3.id in records)
        self.assertTrue(self.record_2.id in records)
        self.assertTrue(self.record_1.id in records)
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1],
                            records[2].id: records[2]}
        self.assertEqual(records_to_check[self.record_1.id].raw, self.record_1.raw)
        self.assertEqual(records_to_check[self.record_2.id].raw, self.record_2.raw)
        self.assertEqual(records_to_check[self.record_3.id].raw, self.record_3.raw)

    def test_get_list_any_scalars_scal_dr(self):
        """
        Given a list of scalars/DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of scalars and DataRanges.
        """
        self.list_to_check = [DataRange(4, 5), 7]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_2.id in records)
        self.assertTrue(self.record_3.id in records)
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_2.id].raw, self.record_2.raw)
        self.assertEqual(records_to_check[self.record_3.id].raw, self.record_3.raw)

    def test_get_list_any_string_dr(self):
        """
        Given a list of string DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of string DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="c", max_inclusive=True),
                              DataRange(min="d", max="g", max_inclusive=True)]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_4.id in records)
        self.assertTrue(self.record_5.id in records)
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_4.id].raw, self.record_4.raw)
        self.assertEqual(records_to_check[self.record_5.id].raw, self.record_5.raw)

    def test_get_list_any_string_str_dr_mixed(self):
        """
        Given a list of strings/DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of strings and DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="c", max_inclusive=True),
                              "honey"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_4.id in records)
        self.assertTrue(self.record_6.id in records)
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_4.id].raw, self.record_4.raw)
        self.assertEqual(records_to_check[self.record_6.id].raw, self.record_6.raw)

    def test_get_list_any_empty_list(self):
        """Given an empty list, we should raise a ValueError."""
        self.list_to_check = []
        with self.assertRaises(ValueError) as context:
            list(self.record_dao.get_list(
                datum_name="spam",
                list_of_contents=self.list_to_check,
                ids_only=True,
                operation=ListQueryOperation.ANY))
        self.assertIn('Must supply at least one entry in list_of_contents for',
                      str(context.exception))

    def test_get_list_any_no_results_string(self):
        """Given a list of data that match no Records, we return no Records."""
        self.list_to_check = ["rhino"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 0)
