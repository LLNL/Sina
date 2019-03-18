"""Test the Cassandra portion of the DAO structure."""
import unittest
import os
import json
import logging
from mock import MagicMock, patch
import types
import six

import cassandra.cqlengine.connection as connection
import cassandra.cqlengine.management as management
from nose.plugins.attrib import attr

import sina.datastores.cass as sina_cass
import sina.datastores.cass_schema as schema
from sina.utils import DataRange, import_json, has_all, has_any, has_only

from sina.model import Run, Record

# CQLEngine needs a keyspace to start. Will not be edited.
INITIAL_KEYSPACE_NAME = "system_traces"
# Name of keyspace to create and then delete.
TEMP_KEYSPACE_NAME = "temp_keyspace_testing_sina"
TESTING_IPS = None  # None for localhost, else a list of node ips.
LOGGER = logging.getLogger(__name__)


def _populate_database_with_data():
    """Build a database to test against."""
    schema.cross_populate_data_tables(id="spam",
                                      name="spam_scal",
                                      value=10,
                                      units="pigs",
                                      tags=["hammy"])
    schema.cross_populate_data_tables(id="eggs",
                                      name="eggs_scal",
                                      value=0)
    schema.cross_populate_data_tables(id="spam",
                                      name="spam_scal_2",
                                      value=200)
    schema.cross_populate_data_tables(id="spam2",
                                      name="spam_scal",
                                      value=10.99999)
    schema.cross_populate_data_tables(id="spam3",
                                      name="spam_scal",
                                      value=10.5)
    schema.cross_populate_data_tables(id="spam3",
                                      name="spam_scal_2",
                                      value=10.5)
    schema.cross_populate_data_tables(id="spam1",
                                      name="val_data",
                                      value="runny",
                                      tags=["edible"])
    schema.cross_populate_data_tables(id="spam1",
                                      name="val_data_2",
                                      value="double yolks")
    schema.cross_populate_data_tables(id="spam3",
                                      name="val_data",
                                      value="chewy",
                                      tags=["edible"])
    schema.cross_populate_data_tables(id="spam3",
                                      name="val_data_2",
                                      value="double yolks")
    schema.cross_populate_data_tables(id="spam4",
                                      name="val_data_2",
                                      value="double yolks")
    schema.cross_populate_data_tables(id="spam",
                                      name="toppings",
                                      value=["onion", "cheese"])
    schema.cross_populate_data_tables(id="spam2",
                                      name="toppings",
                                      value=["cheese", "mushrooms"])
    schema.cross_populate_data_tables(id="spam3",
                                      name="toppings",
                                      value=["onion"])
    schema.cross_populate_data_tables(id="spam",
                                      name="egg_count",
                                      value=[22, 12, 18, 4])
    schema.cross_populate_data_tables(id="spam2",
                                      name="egg_count",
                                      value=[12])
    schema.cross_populate_data_tables(id="spam",
                                      name="spices",
                                      value=["cayenne", "paprika"])
    schema.cross_populate_data_tables(id="spam2",
                                      name="spices",
                                      value=["paprika", "cayenne", "cayenne"])
    schema.cross_populate_data_tables(id="spam3",
                                      name="spices",
                                      value=["paprika", "garlic salt", "cayenne"])
    schema.cross_populate_data_tables(id="spam4",
                                      name="spices",
                                      value=["paprika", "garlic salt", "cayenne", "saffron"])


def _populate_database_with_files():
    """Add test documents to a database."""
    schema.DocumentFromRecord.create(id="spam", uri="beep.wav")
    schema.DocumentFromRecord.create(id="spam1",
                                     uri="beep.wav",
                                     tags=["output", "eggs"])
    schema.DocumentFromRecord.create(id="spam2", uri="beep/png")
    schema.DocumentFromRecord.create(id="spam3", uri="beeq.png")
    schema.DocumentFromRecord.create(id="spam4", uri="beep.png")
    schema.DocumentFromRecord.create(id="spam", uri="beep.pong")


@attr('cassandra')
class TestSearch(unittest.TestCase):
    """Unit tests for the Cassandra portion of the DAO."""

    # TODO: There is currently some enterprise-only functionality for in-memory
    # Cassandra DBs. Worth revisiting in future, should it make it to open.
    def setUp(self):
        """Create test keyspace."""
        if TESTING_IPS:
            connection.setup(TESTING_IPS, INITIAL_KEYSPACE_NAME)
        else:
            connection.setup(['127.0.0.1'], INITIAL_KEYSPACE_NAME)
        management.create_keyspace_simple(TEMP_KEYSPACE_NAME, 1)

    def tearDown(self):
        """Remove test keyspace."""
        management.drop_keyspace(TEMP_KEYSPACE_NAME)

    @patch('sina.datastores.cass_schema.form_connection', autospec=True)
    def test_factory_production(self, mock_form_conn):
        """
        Test to ensure DAOFactory can create all required DAOs.

        Tests passes if all required DAOs are created and are of the right
        type.

        Note that, due to use of the abc module in DAOs, this test will fail
        if any of the required DAOs do not implement all required methods.
        """
        ip = '192.168.1.2:9042'
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME, node_ip_list=ip)
        args, kwargs = mock_form_conn.call_args
        self.assertEqual(args[0], TEMP_KEYSPACE_NAME)
        self.assertEqual(kwargs['node_ip_list'], ip)
        record_dao = factory.createRecordDAO()
        self.assertIsInstance(record_dao, sina_cass.RecordDAO)
        rel_dao = factory.createRelationshipDAO()
        self.assertIsInstance(rel_dao, sina_cass.RelationshipDAO)
        run_dao = factory.createRunDAO()
        self.assertIsInstance(run_dao, sina_cass.RunDAO)

    def test_full_import(self):
        """
        Do an import using the utils importer (temporary).

        Acts as a sanity check on all DAOs, though again, should be temporary.
        """
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 "test_files/mnoda_1.json")
        import_json(factory=factory, json_path=json_path)
        parent = factory.createRecordDAO().get("parent_1")
        relation = factory.createRelationshipDAO().get(object_id="child_1")
        run_factory = factory.createRunDAO()
        child = run_factory.get("child_1")
        canonical = json.load(open(json_path))
        self.assertEquals(canonical['records'][0]['type'], parent.type)
        self.assertEquals(canonical['records'][0]['id'], parent.id)

        # We must go to record.raw for version/application because records
        # don't save them to attributes. This is testing that we don't drop
        # information that is outside the mnoda schema.
        self.assertEquals(canonical['records'][0]['version'],
                          parent.raw['version'])
        self.assertEquals(canonical['records'][0]['application'],
                          parent.raw['application'])

        self.assertEquals(canonical['records'][1]['type'], child.type)
        self.assertEquals(canonical['records'][1]['id'], child.id)
        self.assertEquals(canonical['records'][1]['version'], child.version)
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

    # RecordDAO
    def test_recorddao_basic(self):
        """Test that RecordDAO is inserting and getting correctly."""
        record_dao = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME).createRecordDAO()

        # First test the minimal, JSON-free Record
        pure_obj_record = Record("hello", "there")
        record_dao.insert(pure_obj_record)
        returned_record = record_dao.get("hello")
        self.assertEquals(returned_record.id, pure_obj_record.id)
        self.assertEquals(returned_record.type, pure_obj_record.type)

        rec = Record(id="spam", type="eggs",
                     user_defined={},
                     data={"eggs": {"value": 12,
                                    "units": None,
                                    "tags": ["runny"]},
                           "spam": {"value": [12, 24]},
                           "flavors": {"value": ["original", "bbq"]}},
                     files=[{"uri": "eggs.brek",
                             "mimetype": "egg",
                             "tags": ["fried"]}])
        record_dao.insert(rec)
        returned_record = record_dao.get("spam")
        self.assertEquals(returned_record.id, rec.id)
        self.assertEquals(returned_record.type, rec.type)
        self.assertEquals(returned_record.user_defined, rec.user_defined)
        self.assertEquals(returned_record.raw, rec.raw)

        # TODO: Replace when queries are supported on these tables
        scal_list = (schema.ScalarListDataFromRecord.objects.filter(id=rec.id))
        self.assertEquals(scal_list.get()['value'], rec['data']['spam']['value'])
        str_list = (schema.StringListDataFromRecord.objects.filter(id=rec.id))
        self.assertEquals(str_list.get()['value'], rec['data']['flavors']['value'])

        returned_scalars = record_dao.get_scalars("spam", ["eggs"])
        del rec.data["spam"]
        del rec.data["flavors"]
        self.assertEquals(returned_scalars, rec.data)

        returned_files = record_dao.get_files("spam")
        self.assertEquals(returned_files, rec.files)
        overwrite = Record(id="spam",
                              type="new_eggs",
                              user_defined={"water": "bread",
                                            "flour": "bread"})
        record_dao.insert(overwrite, force_overwrite=True)
        returned_record = record_dao.get("spam")
        self.assertEquals(returned_record.id, rec.id)
        self.assertEquals(returned_record.type, overwrite.type)
        self.assertEquals(returned_record.user_defined, overwrite.user_defined)

    def test_recorddao_insert_extras(self):
        """
        Test that RecordDAO is inserting and retrieving files and scalars.

        Doesn't do much testing of functionality, see later tests for that.
        """
        record_dao = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME).createRecordDAO()
        rec = Record(id="spam",
                     type="new_eggs",
                     user_defined={},
                     data={"foo": {"value": 12,
                                   "units": None,
                                   "tags": ["in", "on"]},
                           "bar": {"value": "1",
                                   "units": None}},
                     files=[{"uri": "ham.png", "mimetype": "png"},
                            {"uri": "ham.curve",
                             "contents": "eggs"}])
        record_dao.insert(rec)
        returned_record_id = next(record_dao.data_query(foo=12))
        self.assertEquals(returned_record_id, rec.id)
        no_scal = DataRange(min=1, min_inclusive=False)
        self.assertFalse(list(record_dao.data_query(bar=no_scal)))
        file_match = list(record_dao.get_given_document_uri(uri="ham.png"))[0]
        self.assertEquals(file_match.id, rec.id)

    def test_recorddao_delete(self):
        """Test that RecordDAO is deleting correctly."""
        # Cascading on an in-memory db always fails. Found no documentation on it.
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
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
        six.assertCountEqual(self, remaining_records, ["rec_2", "rec_3", "rec_4"])

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

    @patch(__name__+'.sina_cass.RecordDAO.get')
    def test_recorddao_uri(self, mock_get):
        """Test that RecordDAO is retrieving based on uris correctly."""
        mock_get.return_value = True
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_files()
        end_wildcard = list(record_dao.get_given_document_uri(uri="beep.%"))
        # The id "spam" matches twice. So we get 4 with 3 unique.
        self.assertEqual(len(end_wildcard), 4)
        mid_wildcard = list(record_dao.get_given_document_uri(uri="beep%png"))
        self.assertEqual(len(mid_wildcard), 2)
        first_wildcard = record_dao.get_given_document_uri(uri="%png")
        self.assertEqual(len(list(first_wildcard)), 3)
        multi_wildcard = record_dao.get_given_document_uri(uri="%.%")
        self.assertEqual(len(list(multi_wildcard)), 5)
        all_wildcard = record_dao.get_given_document_uri(uri="%")
        self.assertEqual(len(list(all_wildcard)), 6)
        ids_only = record_dao.get_given_document_uri(uri="%.%", ids_only=True)
        self.assertIsInstance(ids_only, types.GeneratorType,
                              "Method must return a generator.")
        ids_only = list(ids_only)
        self.assertEqual(len(ids_only), 5)
        self.assertIsInstance(ids_only[0], six.string_types)
        six.assertCountEqual(self, ids_only, ["spam", "spam1", "spam3", "spam4", "spam"])

    @patch(__name__+'.sina_cass.RecordDAO.get')
    def test_recorddao_scalar_data_query(self, mock_get):
        """
        Test that RecordDAO is retrieving based on scalars correctly.

        Uses multiple records, ranges, etcs.
        """
        mock_get.return_value = True
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()
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
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()
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
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

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

    def test_recorddao_data_query_mixed(self):
        """Test that the RecordDAO is retrieving mixed criteria types correctly."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

        just_3 = record_dao.data_query(spam_scal=DataRange(10.1, 400),  # 2 and 3
                                       val_data_2="double yolks",  # 1, 3, and 4
                                       toppings=has_all("onion"))  # 1 and 3
        just_3_list = list(just_3)
        self.assertEqual(len(just_3_list), 1)
        self.assertEqual(just_3_list[0], "spam3")

    def test_recorddao_type(self):
        """Test the RecordDAO is retrieving based on type correctly."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
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

    def test_recorddao_list_data_query_all(self):
        """Test that we're correctly retrieving Records on has_all list criteria."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()
        record_dao.insert(Record(id="spam", type="run"))

        get_one = list(record_dao.data_query(toppings=has_all("cheese", "onion")))
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one[0], "spam")

        get_many = record_dao.data_query(toppings=has_all("cheese"))
        self.assertIsInstance(get_many, types.GeneratorType)
        six.assertCountEqual(self, list(get_many), ["spam", "spam2"])
        get_scalar = record_dao.data_query(egg_count=has_all(4, 12))
        self.assertEqual(list(get_scalar), ["spam"])
        get_with_datarange = record_dao.data_query(egg_count=has_all(DataRange(0, 5)))
        self.assertEqual(list(get_with_datarange), ["spam"])
        get_with_mix = record_dao.data_query(toppings=has_all(DataRange("oniom", "onioo"),
                                                              "cheese"))
        self.assertEqual(list(get_with_mix), ["spam"])

    def test_recorddao_list_data_query_any_one(self):
        """Test that we're correctly retrieving a Record on has_any list criteria."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

        get_one = list(record_dao.data_query(toppings=has_any("mushrooms")))
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one[0], "spam2")

    def test_recorddao_list_data_query_any_many(self):
        """Test that we're correctly retrieving Records on has_any list criteria."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

        get_many = record_dao.data_query(toppings=has_any("onion", "mushrooms"))
        self.assertIsInstance(get_many, types.GeneratorType)
        six.assertCountEqual(self, list(get_many), ["spam", "spam2", "spam3"])

    def test_recorddao_list_data_query_any_none(self):
        """Test that we're correctly retrieving no Records on unmatched has_any list criteria."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

        get_none = record_dao.data_query(toppings=has_any("capsicum", "anchovy"))
        self.assertFalse(list(get_none))

    def test_recorddao_list_data_query_any_scalar(self):
        """Test that has_any works with scalars."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

        get_scalar = record_dao.data_query(egg_count=has_any(4, 12, 22))
        six.assertCountEqual(self, list(get_scalar), ["spam", "spam2"])

    def test_recorddao_list_data_query_any_mixed(self):
        """Test that has_any works with scalars."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

        get_with_mix = record_dao.data_query(toppings=has_any(DataRange("oniom", "onioo"),
                                                              "capsicum"))
        six.assertCountEqual(self, list(get_with_mix), ["spam", "spam3"])

    def test_recorddao_list_data_query_any_ranges(self):
        """Test that has_any works with DataRanges."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()

        get_with_datarange = record_dao.data_query(egg_count=has_any(DataRange(0, 5)))
        six.assertCountEqual(self, list(get_with_datarange), ["spam"])

    def test_recorddao_list_data_query_only_one(self):
        """Test that we're correctly retrieving Records on a has_only list criterion."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()
        get_one = list(record_dao.data_query(toppings=has_only("onion")))
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one[0], "spam3")

    def test_recorddao_list_data_query_only_many(self):
        """Test that we're correctly retrieving Records on has_only list criteria."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()
        get_many = record_dao.data_query(spices=has_only("cayenne", "paprika"))
        self.assertIsInstance(get_many, types.GeneratorType)
        six.assertCountEqual(self, list(get_many), ["spam", "spam2"])

    def test_recorddao_list_data_query_only_scalar(self):
        """Test that we're correctly retrieving Records on scalar has_only list criteria."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()
        get_scalar = record_dao.data_query(egg_count=has_only(12))
        self.assertEqual(list(get_scalar), ["spam2"])
        get_none = record_dao.data_query(toppings=has_only("cheese"))
        self.assertFalse(list(get_none))

    def test_recorddao_list_data_query_only_ranges(self):
        """Test that we're correctly retrieving Records on has_only with DataRanges."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_data()
        get_range = record_dao.data_query(spices=has_only(DataRange("cayenne",
                                                                    "paprika",
                                                                    max_inclusive=True)))
        six.assertCountEqual(self, list(get_range), ["spam", "spam2", "spam3"])

    def test_recorddao_get_files(self):
        """Test that the RecordDAO is getting files for records correctly."""
        record_dao = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME).createRecordDAO()
        _populate_database_with_files()
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
        record_dao = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME).createRecordDAO()
        _populate_database_with_data()
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
        no_tags = record_dao.get_data_for_records(id_list=["spam"],
                                                  data_list=all_scalars,
                                                  omit_tags=True)
        self.assertEqual(no_tags["spam"]["spam_scal"],
                         {"value": 10, "units": "pigs"})

    def test_recorddao_get_scalars(self):
        """Test the RecordDAO is getting specific scalars correctly."""
        record_dao = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME).createRecordDAO()
        _populate_database_with_data()
        get_one = record_dao.get_scalars(id="spam",
                                         scalar_names=["spam_scal"])
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one["spam_scal"]["units"], "pigs")
        get_more = record_dao.get_scalars(id="spam",
                                          scalar_names=["spam_scal_2",
                                                        "spam_scal"])
        self.assertEqual(len(get_more), 2)
        self.assertEqual(get_one["spam_scal"]["tags"], ["hammy"])
        self.assertFalse(get_more["spam_scal_2"]["units"])
        self.assertFalse(get_more["spam_scal_2"]["tags"])
        # Value is not a scalar
        # TODO: Maybe we should return values as well as scalars for this?
        # Seems more in line with what customers might expect.
        get_gone = record_dao.get_scalars(id="spam",
                                          scalar_names=["value-1"])
        self.assertFalse(get_gone)
        get_norec = record_dao.get_scalars(id="wheeee",
                                           scalar_names=["value-1"])
        self.assertFalse(get_norec)

    # RelationshipDAO
    def test_relationshipdao_basic(self):
        """Test that RelationshipDAO is inserting and getting correctly."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        relationship_dao = factory.createRelationshipDAO()
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
    def test_rundao_basic(self):
        """Test that RunDAO is inserting and getting correnctly."""
        run_dao = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME).createRunDAO()
        run = Run(id="spam", version="1.2.3",
                  application="bar", user="bep",
                  user_defined={"boop": "bep"})
        run_dao.insert(run)
        returned_run = run_dao.get("spam")
        self.assertEquals(returned_run.id, run.id)
        self.assertEquals(returned_run.raw, run.raw)
        self.assertEquals(returned_run.application, run.application)
        self.assertEquals(returned_run.user, run.user)
        self.assertEquals(returned_run.user_defined, run.user_defined)
        self.assertEquals(returned_run.version, run.version)

    def test_rundao_delete(self):
        """Test that RunDAO is deleting correctly."""
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        run_dao = factory.createRunDAO()
        relationship_dao = factory.createRelationshipDAO()

        data = {"eggs": {"value": [12, 13], "tags": ["breakfast"]}}
        files = [{"uri": "justheretoexist.png"}]
        run_1 = Run(id="run_1", application="eggs", data=data, files=files)
        run_2 = Run(id="run_2", application="spam", data=data, files=files)
        run_dao.insert_many([run_1, run_2])
        relationship_dao.insert(subject_id="run_1", object_id="run_2", predicate="dupes")

        # Ensure there's two entries in the Run table
        self.assertEquals(len(schema.Run.objects.all()), 2)
        # Delete one
        run_dao.delete("run_1")
        # Now there should only be one Run left
        self.assertEquals(len(schema.Run.objects.all()), 1)
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
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        _populate_database_with_data()
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
        # No guaranteed order per docs, but likely partition order
        # We know that order here.
        spam_run = run_dao.get(multi_scalar[1])
        self.assertEquals(spam_run.user, run.user)
        self.assertEquals(spam_run.raw, run.raw)

    def test_convert_record_to_run_good(self):
        """Test we return a Run when given a Record with valid input."""
        rec = Record(id="spam", type="run")
        rec["user"] = "bob"
        rec["application"] = "skillet"
        rec["version"] = "1.0"
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        run_dao = factory.createRunDAO()
        converted_run = run_dao._convert_record_to_run(record=rec)
        self.assertEqual(converted_run.raw, rec.raw)
        self.assertEqual(type(converted_run), Run)

    def test_convert_record_to_run_bad(self):
        """Test we raise a ValueError when given a Record with bad input."""
        rec = Record(id="spam", type="task")
        rec["user"] = "bob"
        rec["application"] = "skillet"
        rec["version"] = "1.0"
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        run_dao = factory.createRunDAO()
        with self.assertRaises(ValueError) as context:
            run_dao._convert_record_to_run(record=rec)
        self.assertIn('Record must be of subtype Run to convert to Run. Given',
                      str(context.exception))
