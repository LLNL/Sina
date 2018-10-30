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
from sina.utils import ScalarRange, import_json

from sina.model import Run, Record

# CQLEngine needs a keyspace to start. Will not be edited.
INITIAL_KEYSPACE_NAME = "system_traces"
# Name of keyspace to create and then delete.
TEMP_KEYSPACE_NAME = "temp_keyspace_testing_sina"
TESTING_IPS = None  # None for localhost, else a list of node ips.
LOGGER = logging.getLogger(__name__)


def _populate_database_with_scalars():
    """Build a database to test against."""
    schema.cross_populate_scalar_and_record(id="spam",
                                            name="spam_scal",
                                            value=10,
                                            units="pigs",
                                            tags=["hammy"])
    schema.cross_populate_scalar_and_record(id="eggs",
                                            name="eggs_scal",
                                            value=0)
    schema.cross_populate_scalar_and_record(id="spam",
                                            name="spam_scal_2",
                                            value=200)
    schema.cross_populate_scalar_and_record(id="spam2",
                                            name="spam_scal",
                                            value=10.99999)
    schema.cross_populate_scalar_and_record(id="spam3",
                                            name="spam_scal",
                                            value=10.5)
    schema.cross_populate_scalar_and_record(id="spam3",
                                            name="spam_scal_2",
                                            value=10.5)


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

    def test_factory_production(self):
        """
        Test to ensure DAOFactory can create all required DAOs.

        Tests passes if all required DAOs are created and are of the right
        type.

        Note that, due to use of the abc module in DAOs, this test will fail
        if any of the required DAOs do not implement all required methods.
        """
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
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
        child_scalar = ScalarRange(name="scalar-1", min=387.6,
                                   min_inclusive=True, max=387.6,
                                   max_inclusive=True)
        child_from_scalar = list(run_factory.get_given_scalar(child_scalar))

        self.assertEquals(child.id, child_from_uri[0].id)
        self.assertEquals(child.id, child_from_scalar[0].id)
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
                                    "tags": ["runny"]}},
                     files=[{"uri": "eggs.brek",
                             "mimetype": "egg",
                             "tags": ["fried"]}])
        record_dao.insert(rec)
        returned_record = record_dao.get("spam")
        self.assertEquals(returned_record.id, rec.id)
        self.assertEquals(returned_record.type, rec.type)
        self.assertEquals(returned_record.user_defined, rec.user_defined)
        self.assertEquals(returned_record.raw, rec.raw)
        returned_scalars = record_dao.get_scalars("spam", ["eggs"])
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
        scal = ScalarRange(name="foo", min=12, min_inclusive=True,
                           max=12, max_inclusive=True)
        returned_record = list(record_dao.get_given_scalar(scal))[0]
        self.assertEquals(returned_record.id, rec.id)
        no_scal = ScalarRange(name="bar", min=1, min_inclusive=True)
        self.assertFalse(list(record_dao.get_given_scalar(no_scal)))
        file_match = list(record_dao.get_given_document_uri(uri="ham.png"))[0]
        self.assertEquals(file_match.id, rec.id)

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
    def test_recorddao_scalar(self, mock_get):
        """
        Test that RecordDAO is retrieving based on scalars correctly.

        Uses multiple records, ranges, etcs.
        """
        mock_get.return_value = True
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_scalars()
        too_big_range = ScalarRange(name="spam_scal", max=9,
                                    max_inclusive=True)
        too_big = record_dao.get_given_scalar(too_big_range)
        self.assertFalse(list(too_big))
        too_small_range = ScalarRange(name="spam_scal", min=10.99999,
                                      min_inclusive=False)
        too_small = record_dao.get_given_scalar(too_small_range)
        self.assertFalse(list(too_small))
        just_right_range = ScalarRange(name="spam_scal", min=0,
                                       min_inclusive=True, max=300,
                                       max_inclusive=True)
        just_right = record_dao.get_given_scalar(just_right_range)
        self.assertEqual(len(list(just_right)), 3)
        nonexistant_range = ScalarRange(name="not_here", min=0,
                                        min_inclusive=True, max=300,
                                        max_inclusive=True)
        no_scalar = record_dao.get_given_scalar(nonexistant_range)
        self.assertFalse(list(no_scalar))
        multi_range = ScalarRange(name="spam_scal")
        multi = list(record_dao.get_given_scalar(multi_range))
        self.assertEqual(len(multi), 3)
        self.assertEqual(mock_get.call_count, 6)
        ids_only = record_dao.get_given_scalar(multi_range, ids_only=True)
        self.assertIsInstance(ids_only, types.GeneratorType,
                              "Method must return a generator.")
        ids_only = list(ids_only)
        self.assertEqual(len(ids_only), 3)
        self.assertIsInstance(ids_only[0], six.string_types)
        six.assertCountEqual(self, ids_only, ["spam", "spam2", "spam3"])

    @patch(__name__+'.sina_cass.RecordDAO.get')
    def test_recorddao_many_scalar(self, mock_get):
        """Test that RecordDAO's retrieving on multiple scalars correctly."""
        mock_get.return_value = True
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        record_dao = factory.createRecordDAO()
        _populate_database_with_scalars()
        spam_and_spam_3 = ScalarRange(name="spam_scal", min=10,
                                      min_inclusive=True)
        spam_3_only = ScalarRange(name="spam_scal_2", max=100)
        one = record_dao.get_given_scalars([spam_and_spam_3,
                                            spam_3_only])
        self.assertEqual(len(list(one)), 1)
        none_fulfill = ScalarRange(name="nonexistant", max=100)
        none = list(record_dao.get_given_scalars([spam_and_spam_3,
                                                 spam_3_only,
                                                 none_fulfill]))
        self.assertFalse(none)
        id_only = record_dao.get_given_scalars([spam_and_spam_3,
                                               spam_3_only],
                                               ids_only=True)
        self.assertIsInstance(id_only, types.GeneratorType,
                              "Method must return a generator.")
        id_only = list(id_only)
        self.assertEqual(len(id_only), 1)

        self.assertEqual(id_only[0], "spam3")

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

    def test_recorddao_get_scalars(self):
        """Test the RecordDAO is getting specific scalars correctly."""
        record_dao = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME).createRecordDAO()
        _populate_database_with_scalars()
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

    def test_rundao_get_scalars(self):
        """
        Test ability to find Runs by scalars.

        The current version inherits from RecordDAO and does only a little
        extra processing, and most of that in _convert_record_to_run. We're
        really just making sure nothing gets lost between those two.
        """
        # TODO: Test raises question of whether type should be tracked in
        # the scalars table.
        factory = sina_cass.DAOFactory(TEMP_KEYSPACE_NAME)
        _populate_database_with_scalars()
        run_dao = factory.createRunDAO()
        rec = Record(id="spam2", type="task",
                     user_defined={})
        run = Run(id="spam", user="bep", application="foo",
                  version="1.2", user_defined={"spam": "eggs"})
        run2 = Run(id="spam3", user="egg", application="foo",
                   version="0.4", user_defined={"eggs": "spam"})
        run_dao.record_DAO.insert(rec)
        run_dao.insert_many([run, run2])
        multi_range = ScalarRange(name="spam_scal")
        multi_scalar = list(run_dao.get_given_scalar(multi_range))
        self.assertEqual(len(multi_scalar), 2)
        # They're returned in primary key order
        spam_run = multi_scalar[0]
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
