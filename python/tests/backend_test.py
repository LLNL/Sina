#!/bin/python
"""Test a Sina backend."""

import os
import unittest
import csv
import itertools
import logging
from collections import OrderedDict
import types
import io
import tempfile

import six

# Disable pylint check due to its issue with virtual environments
from mock import patch  # pylint: disable=import-error

from sina.utils import (DataRange, import_json, export, _export_csv, has_all,
                        has_any, all_in, any_in, exists)
from sina.model import Run, Record, Relationship
import sina.sjson as json

LOGGER = logging.getLogger(__name__)
TARGET = None


# Disable pylint invalid-name due to significant number of tests with names
# exceeding the 30 character limit. Also disable too-many-lines
# pylint: disable=invalid-name,too-many-lines


def create_daos(class_):
    """
    Create DAOs for the specified class.

    :param class_: Backend class
    """
    class_.factory = class_.create_dao_factory()
    class_.record_dao = class_.factory.create_record_dao()
    class_.relationship_dao = class_.factory.create_relationship_dao()


def populate_database_with_data(record_dao):
    """
    Add test data to a database in a backend-independent way.

    :param record_dao: The RecordDAO used to insert records into a database.
    :return: a dict of all the inserted records, where the IDs are the keys
    """
    spam_record = Run(id="spam", application="breakfast_maker")
    spam_record["user"] = "Bob"
    spam_record["version"] = "1.4.0"
    spam_record.data["spam_scal"] = {"value": 10, "units": "pigs", "tags": ["hammy"]}
    spam_record.data["spam_scal_2"] = {"value": 200}
    spam_record.data["val_data"] = {"value": "runny", "tags": ["edible"]}
    spam_record.data["val_data_2"] = {"value": "double yolks"}
    spam_record.files = {"beep.wav": {},
                         "beep.pong": {}}
    spam_record.curve_sets["spam_curve"] = {
        "independent": {"time": {"value": [1, 2, 3], "tags": ["misc"]}},
        "dependent": {"internal_temp": {"value": [80, 95, 120], "units": "F"},
                      "rubberiness": {"value": [0, 0.1, 0.3],
                                      "tags": ["gross"]}},
        "tags": ["food"]}
    spam_record.curve_sets["egg_curve"] = {
        "independent": {"time": {"value": [1, 2, 3, 4], "tags": ["timer"]}},
        "dependent": {"yolk_yellowness": {"value": [10, 9, 8, 6]},
                      "rubberiness": {"value": [0, 0.1, 0.3, 0.8],
                                      "tags": ["gross"]}},
        "tags": ["food"]}

    spam_record_2 = Run(id="spam2", application="scal_generator")
    spam_record_2.data["spam_scal"] = {"value": 10.99999}
    spam_record_2.files = {"beep/png": {}}
    spam_record_2.curve_sets["spam_curve"] = {
        "independent": {"time": {"value": [1, 2, 3]}},
        "dependent": {"internal_temp": {"value": [80, 95, 120]}}}

    spam_record_3 = Record(id="spam3", type="foo")
    spam_record_3.data["spam_scal"] = {"value": 10.5}
    spam_record_3.data["spam_scal_2"] = {"value": 10.5}
    spam_record_3.data["val_data"] = {"value": "chewy", "tags": ["edible", "simple"]}
    spam_record_3.data["val_data_2"] = {"value": "double yolks"}
    spam_record_3.files = {"beeq.png": {"mimetype": 'image/png'}}

    spam_record_4 = Record(id="spam4", type="bar")
    spam_record_4.data["val_data_list_1"] = {"value": [-11, -9]}
    spam_record_4.data["val_data_2"] = {"value": "double yolks"}
    spam_record_4.files = {"beep.png": {"mimetype": 'image/png'}}

    spam_record_5 = Run(id="spam5", application="breakfast_maker")
    spam_record_5.data["spam_scal_3"] = {"value": 46}
    spam_record_5.data["val_data_3"] = {"value": "sugar"}
    spam_record_5.data["flex_data_1"] = {"value": [100, 200, 300]}
    spam_record_5.data["flex_data_2"] = {"value": 6}
    spam_record_5.data["val_data_list_1"] = {"value": [0, 8]}
    spam_record_5.data["val_data_list_2"] = {"value": ['eggs', 'pancake']}
    spam_record_5.files = {"beep.wav": {"tags": ["output", "eggs"],
                                        "mimetype": 'audio/wav'}}

    spam_record_6 = Record(id="spam6", type="spamrec")
    spam_record_6.data["flex_data_1"] = {"value": "orange juice"}
    spam_record_6.data["val_data_3"] = {"value": "syrup"}
    spam_record_6.data["val_data_list_1"] = {"value": [8, 20]}
    spam_record_6.data["val_data_list_2"] = {"value": ['eggs', 'pancake', 'yellow']}

    egg_record = Record(id="eggs", type="eggrec")
    egg_record.data["eggs_scal"] = {"value": 0}

    record_with_shared_scalar_data_and_curve = Record(
        id='shared_curve_set_and_matching_scalar_data', type='overlap')
    record_with_shared_scalar_data_and_curve.add_data('shared_scalar', 1000)
    record_with_shared_scalar_data_and_curve.curve_sets = {
        'cs1': {
            'independent': {'time': {'value': [1, 2, 3]}},
            'dependent': {'shared_scalar': {'value': [400, 500, 600]}}
        }
    }

    records = [spam_record_3, spam_record_4, spam_record_6, egg_record,
               spam_record, spam_record_2, spam_record_5,
               record_with_shared_scalar_data_and_curve]
    record_dao.insert(records)

    return {record.id: record for record in records}


def remove_file(filename):
    """
    Remove the specified file if it exists.

    :param filename: Name of the file to be removed
    """
    try:
        os.remove(filename)
    except OSError:
        pass


class TestModify(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """
    Unit tests that modify the database.

    Things like deletion and insertion go here. Each test is responsible for
    creating its own factory connection due to the database being wiped after
    each test.
    """

    __test__ = False

    def create_dao_factory(self, test_db_dest=None):
        """
        Create the DAO to run Modify tests.

        Must be implemented by child, likely via its mixin class (ex: SQLMixin).

        param test_db_dest: The database that the DAOFactory should target.
        """
        raise NotImplementedError

    def setUp(self):
        self.factory = self.create_dao_factory()

    def tearDown(self):
        self.factory.close()

    def _assert_records_equal(self, rec_1, rec_2):
        """
        Test for a limited version of the question "are these two records equal?".

        ID, type, data, files, and user_defined are independently checked for
        exact equality. Not suitable for use with doubles math.
        """
        # Done instead of __dict__ to make it clearer what part fails (if any)
        self.assertEqual(rec_1.id, rec_2.id)
        self.assertEqual(rec_1.type, rec_2.type)
        self.assertEqual(rec_1.data, rec_2.data)
        self.assertEqual(rec_1.files, rec_2.files)
        self.assertEqual(rec_1.user_defined, rec_2.user_defined)

    def test_recorddao_insert_retrieve(self):
        """Test that RecordDAO is inserting and getting correctly."""
        record_dao = self.factory.create_record_dao()
        rec = Record(id="spam", type="eggs",
                     data={"eggs": {"value": 12, "units": None, "tags": ["runny"]},
                           "recipes": {"value": []}},
                     files={"eggs.brek": {"mimetype": "egg", "tags": ["fried"]}},
                     user_defined={})
        record_dao.insert(rec)
        returned_record = record_dao.get("spam")
        self._assert_records_equal(returned_record, rec)

    def test_recorddao_insert_many(self):
        """Test that RecordDAO is inserting a generator of several Records correctly."""
        record_dao = self.factory.create_record_dao()
        rec_1 = Record(id="spam", type="eggs",
                       data={"eggs": {"value": 12}})
        rec_2 = Record(id="spam2", type="eggs",
                       data={"eggs": {"value": 32}})
        record_dao.insert((x for x in (rec_1, rec_2)))
        returned_records = list(record_dao.get((x for x in ("spam", "spam2"))))
        self.assertEqual(returned_records[0].data["eggs"]["value"],
                         rec_1["data"]["eggs"]["value"])
        self.assertEqual(returned_records[1].data["eggs"]["value"],
                         rec_2["data"]["eggs"]["value"])

    def test_recorddao_insert_bad(self):
        """
        Test that the RecordDAO can still be used to query records after an
        exception was raised."""
        record_dao = self.factory.create_record_dao()
        rec_1 = Record(id='spam1', type='eggs',
                       data={'eggs': {'value': 12}})
        rec_2 = Record(id='spam2', type='eggs',
                       data={'eggs': {'value': 32}})
        record_dao.insert((x for x in (rec_1, rec_2)))
        returned_ids = set(rec.id for rec in record_dao.get(['spam1', 'spam2']))
        self.assertEqual(returned_ids, {'spam1', 'spam2'})

        bad_record = Record(id='bad_one', type='eggs',
                            data={'eggs': {'value': float('NaN')}})

        # Different DAOs can raise different exceptions, so we can't be
        # more specific here
        self.assertRaises(Exception, record_dao.insert, bad_record)

        returned_ids = set(rec.id for rec in record_dao.get(['spam1', 'spam2']))
        self.assertEqual(returned_ids, {'spam1', 'spam2'})

    def test_recorddao_insert_overlapped_curves(self):
        """Test that curves with overlapping values are handled properly."""
        record_dao = self.factory.create_record_dao()
        rec = Record(id="spam", type="eggs")
        rec.curve_sets["spam_curve"] = {
            "dependent": {"firmness": {"value": [1, 1, 1, 1.2]}},
            "independent": {"time": {"value": [0, 1, 2, 3],
                                     "tags": ["misc", "protein"],
                                     "units": "seconds"}}}
        rec.curve_sets["egg_curve"] = {
            "dependent": {"firmness": {"value": [0, 0, 0.1, 0.3]}},
            "independent": {"time": {"value": [1, 2, 3, 4],
                                     "tags": ["timer", "protein"]}}}
        record_dao.insert(rec)
        ret_record = record_dao.get("spam")
        # We sort-of check how it's stored *in the db*
        # There's not a great way of doing that in a backend-independent way
        # since get_data doesn't handle timeseries data, though.
        # The best we can do is check that the values unified.
        should_be_empty = record_dao.data_query(time=all_in(DataRange(0, 4)))
        also_be_empty = record_dao.data_query(time=all_in(DataRange(1, 5)))
        self.assertFalse(list(should_be_empty))
        self.assertFalse(list(also_be_empty))
        # Repeat for dependent
        self.assertFalse(list(record_dao.data_query(firmness=all_in(DataRange(1, 1.2)))))
        self.assertFalse(list(record_dao.data_query(firmness=all_in(DataRange(0, 0.3)))))
        # Make sure we didn't overwrite anything while merging the times
        self.assertEqual(
            ret_record.curve_sets["spam_curve"]["independent"]["time"]["value"],
            rec["curve_sets"]["spam_curve"]["independent"]["time"]["value"])
        self.assertListEqual(
            ret_record.curve_sets["spam_curve"]["independent"]["time"]["tags"],
            rec["curve_sets"]["spam_curve"]["independent"]["time"]["tags"])
        self.assertEqual(
            ret_record.curve_sets["egg_curve"]["independent"]["time"]["value"],
            rec["curve_sets"]["egg_curve"]["independent"]["time"]["value"])
        self.assertListEqual(
            ret_record.curve_sets["egg_curve"]["independent"]["time"]["tags"],
            rec["curve_sets"]["egg_curve"]["independent"]["time"]["tags"])
        record_dao.delete(rec.id)
        # Make sure we're erroring on unit overwriting
        rec.curve_sets["bad_time"] = {
            "dependent": {},
            "independent": {"time": {"value": [1, 2, 3, 4],
                                     "tags": ["timer"],
                                     "units": "NOT SECONDS"}}}
        with self.assertRaises(ValueError) as context:
            record_dao.insert(rec)
        self.assertIn('Tried to set units', str(context.exception))

    def test_recorddao_insert_overlapped_curve_and_data(self):
        """Test that we can insert a record if a curve and data item overlap."""
        rec = Record(id="spam", type="eggs")
        rec.curve_sets = {
            "spam_curve": {
                "dependent": {"firmness": {"value": [1, 1, 1, 1.2]}},
                "independent": {"time": {"value": [0, 1, 2, 3],
                                         "tags": ["misc"],
                                         "units": "seconds"}}}}
        rec.data["time"] = {"value": 1}
        record_dao = self.factory.create_record_dao()
        record_dao.insert(rec)
        retrieved = record_dao.get('spam')
        self.assertIsNotNone(retrieved)

    def test_recorddao_delete_one(self):
        """Test that RecordDAO is deleting correctly."""
        record_dao = self.factory.create_record_dao()
        record_dao.insert(Record(id="rec_1", type="sample"))
        record_dao.delete("rec_1")
        self.assertEqual(list(record_dao.get_all_of_type("sample")), [])

    def test_recorddao_delete_invalid(self):
        """Verify that the RecordDAO can still be used after a failed deletion"""
        record_dao = self.factory.create_record_dao()
        record_dao.insert(Record(id="rec_1", type="sample"))
        record_dao.delete("no_such_id")
        self.assertIsNotNone(record_dao.get("rec_1"))

    def test_recorddao_delete_data_cascade(self):
        """Test that deletion of a Record correctly cascades to data and files."""
        record_dao = self.factory.create_record_dao()
        data = {"eggs": {"value": 12, "tags": ["breakfast"]},
                "flavor": {"value": "tasty"}}
        files = {"justheretoexist.png": {}}
        record_dao.insert(Record(id="rec_1", type="sample", data=data, files=files))
        record_dao.delete("rec_1")
        # Make sure the data, raw, files, and relationships were deleted as well
        dead_data = record_dao.get_data_for_records(id_list=["rec_1"],
                                                    data_list=["eggs", "flavor"])
        self.assertEqual(dead_data, {})
        dead_files = list(record_dao.get_given_document_uri("justheretoexist.png",
                                                            ids_only=True))
        self.assertEqual(dead_files, [])

    def test_recorddao_delete_one_with_relationship(self):
        """Test that RecordDAO deletions include relationships."""
        record_dao = self.factory.create_record_dao()
        relationship_dao = self.factory.create_relationship_dao()
        record_1 = Record(id="rec_1", type="sample")
        record_2 = Record(id="rec_2", type="sample")
        record_dao.insert([record_1, record_2])
        relationship_dao.insert(subject_id="rec_1", object_id="rec_2", predicate="dupes")
        record_dao.delete("rec_1")
        # Make sure the relationship was deleted
        self.assertFalse(relationship_dao.get(subject_id="rec_1"))
        # rec_2 should not be deleted
        remaining_records = list(record_dao.get_all_of_type("sample", ids_only=True))
        self.assertEqual(remaining_records, ["rec_2"])

    def test_recorddao_delete_many(self):
        """Test that RecordDAO can delete many at once."""
        record_dao = self.factory.create_record_dao()
        relationship_dao = self.factory.create_relationship_dao()
        record_1 = Record(id="rec_1", type="sample")
        record_2 = Record(id="rec_2", type="sample")
        record_3 = Record(id="rec_3", type="sample")
        record_4 = Record(id="rec_4", type="sample")
        all_ids = ["rec_1", "rec_2", "rec_3", "rec_4"]
        record_dao.insert([record_1, record_2, record_3, record_4])
        relationship_dao.insert(subject_id="rec_1", object_id="rec_2", predicate="dupes")
        relationship_dao.insert(subject_id="rec_2", object_id="rec_2", predicate="is")
        relationship_dao.insert(subject_id="rec_3", object_id="rec_4", predicate="dupes")
        relationship_dao.insert(subject_id="rec_4", object_id="rec_4", predicate="is")
        # Delete several
        record_dao.delete(["rec_1", "rec_2", "rec_3"])
        remaining_records = list(record_dao.get_all_of_type("sample", ids_only=True))
        self.assertEqual(remaining_records, ["rec_4"])

        # Make sure expected data entries were deleted as well (acts as cascade test)
        for_all = record_dao.get_data_for_records(id_list=all_ids,
                                                  data_list=["eggs", "flavor"])
        for_one = record_dao.get_data_for_records(id_list=["rec_4"],
                                                  data_list=["eggs", "flavor"])
        self.assertEqual(for_all, for_one)

        # Make sure expected Relationships were deleted
        self.assertFalse(relationship_dao.get(object_id="rec_2"))
        self.assertFalse(relationship_dao.get(subject_id="rec_3"))
        self.assertEqual(len(relationship_dao.get(object_id="rec_4")), 1)

    def test_recorddao_update_one(self):
        """Test that RecordDAO is updating correctly."""
        record_dao = self.factory.create_record_dao()
        rec = Record(id="spam", type="eggs",
                     data={"eggs": {"value": 12, "units": None, "tags": ["runny"]},
                           "recipes": {"value": 5}},
                     files={"eggs.brek": {"mimetype": "egg", "tags": ["fried"]}},
                     user_defined={})
        record_dao.insert(rec)
        returned_record = record_dao.get("spam")
        self.assertEqual(returned_record.data, rec.data)
        rec["data"]["eggs"]["value"] = 144
        rec["type"] = "gross_eggs"
        record_dao.update(rec)
        updated_record = record_dao.get("spam")
        self.assertEqual(returned_record.id, updated_record.id)
        self.assertEqual(returned_record.files, updated_record.files)
        self.assertEqual(returned_record.user_defined, updated_record.user_defined)
        self.assertEqual(returned_record.data["recipes"]["value"],
                         updated_record.data["recipes"]["value"])
        self.assertNotEqual(returned_record.type, updated_record.type)
        self.assertNotEqual(returned_record.data["eggs"]["value"],
                            updated_record.data["eggs"]["value"])
        self._assert_records_equal(updated_record, rec)

    def test_recorddao_update_with_invalid_data(self):
        """
        Test that RecordDAO can still be used after tyring to update a record
        with invalid data.
        """
        record_dao = self.factory.create_record_dao()
        rec = Record(id="spam", type="eggs",
                     data={"eggs": {"value": 12}})
        record_dao.insert(rec)
        returned_record = record_dao.get("spam")
        self.assertEqual(returned_record.data, rec.data)
        rec["data"]["eggs"]["value"] = float('NaN')
        rec["data"]["new_item"] = {
            'value': 15
        }
        self.assertRaises(Exception, record_dao.update, rec)

        returned_record = record_dao.get("spam")
        self.assertEqual(returned_record.id, rec.id)
        self.assertEqual(returned_record.data["eggs"]["value"], 12)
        self.assertNotIn("new_item", returned_record.data)

    def test_recorddao_update_many(self):
        """Test that RecordDAO is updating multiple Records at once correctly."""
        record_dao = self.factory.create_record_dao()
        rec = Record(id="spam", type="eggs", data={"count": {"value": 12}})
        rec2 = Record(id="spam2", type="bacon", data={"source": {"value": "pig"}})
        rec3 = Record(id="spam3", type="toast", data={"doneness": {"value": "very"}})
        record_dao.insert([rec, rec2, rec3])
        rec.type = "tofeggs"
        rec2.data["source"]["tags"] = ["applewood smoked"]
        rec3.files["image/of/toast.png"] = {}
        record_dao.update(rec for rec in [rec, rec2, rec3])  # test against generator
        upd_rec, upd_rec2, upd_rec3 = list(record_dao.get(["spam", "spam2", "spam3"]))
        self._assert_records_equal(upd_rec, rec)
        self._assert_records_equal(upd_rec2, rec2)
        self._assert_records_equal(upd_rec3, rec3)

    def test_recorddao_get_raw(self):
        """Verify we can get the raw JSON. This is useful for bad data"""
        record_dao = self.factory.create_record_dao()
        rec = Record(id="rec1", type="eggs",
                     data={"eggs": {"value": 12, "units": None, "tags": ["runny"]},
                           "recipes": {"value": []}},
                     files={"eggs.break": {"mimetype": "egg", "tags": ["fried"]}},
                     user_defined={})
        record_dao.insert(rec)
        returned_json = record_dao.get_raw("rec1")
        raw = json.loads(returned_json)
        self.assertDictEqual(raw, {
            'id': 'rec1',
            'type': 'eggs',
            'data': {
                'eggs': {
                    'value': 12,
                    'tags': ['runny'],
                    'units': None
                },
                'recipes': {
                    'value': []
                }
            },
            'files': {
                'eggs.break': {
                    'mimetype': 'egg',
                    'tags': ['fried']
                }
            },
            'curve_sets': {},
            'user_defined': {}
        })

    # RelationshipDAO
    def test_relationshipdao_insert_simple_retrieve(self):
        """Test that RelationshipDAO is inserting and getting correctly."""
        relationship_dao = self.factory.create_relationship_dao()
        record_dao = self.factory.create_record_dao()

        record_dao.insert(Record('spam', 'test_rec'))
        record_dao.insert(Record('eggs', 'test_rec'))

        relationship = Relationship(subject_id="spam", object_id="eggs", predicate="loves")
        relationship_dao.insert(relationship)
        subj = relationship_dao.get(subject_id=relationship.subject_id)
        pred = relationship_dao.get(predicate=relationship.predicate)
        for relationship_list in (subj, pred):
            result = relationship_list[0]
            # Testing one definition of "equality" between Relationships.
            self.assertEqual(result.subject_id, relationship.subject_id)
            self.assertEqual(result.object_id, relationship.object_id)
            self.assertEqual(result.predicate, relationship.predicate)

    def test_relationshipdao_insert_compound_retrieve(self):
        """Test that RelationshipDAO's multi-criteria getter is working correctly."""
        relationship_dao = self.factory.create_relationship_dao()
        record_dao = self.factory.create_record_dao()

        record_dao.insert(Record('spam', 'test_rec'))
        record_dao.insert(Record('eggs', 'test_rec'))

        relationship = Relationship(subject_id="spam", object_id="eggs", predicate="loves")
        relationship_dao.insert(relationship)
        obj_pred = relationship_dao.get(object_id=relationship.object_id,
                                        predicate=relationship.predicate)
        full = relationship_dao.get(subject_id=relationship.subject_id,
                                    object_id=relationship.object_id,
                                    predicate=relationship.predicate)
        for relationship_list in (obj_pred, full):
            result = relationship_list[0]
            self.assertEqual(result.subject_id, relationship.subject_id)
            self.assertEqual(result.object_id, relationship.object_id)
            self.assertEqual(result.predicate, relationship.predicate)

    def test_relationshipdao_get_uses_and(self):
        """Test that RelationshipDAO.get() users "and" to join restrictions."""
        # pylint: disable-msg=too-many-locals
        record_dao = self.factory.create_record_dao()
        relationship_dao = self.factory.create_relationship_dao()

        subjects = ['s' + str(i + 1) for i in range(0, 3)]
        predicates = ['p' + str(i + 1) for i in range(0, 4)]
        objects = ['o' + str(i + 1) for i in range(0, 5)]

        for record_id in itertools.chain(subjects, objects):
            record_dao.insert(Record(record_id, 'test_rec'))

        for subject_id in subjects:
            for predicate in predicates:
                for object_id in objects:
                    relationship_dao.insert(Relationship(subject_id=subject_id,
                                                         predicate=predicate,
                                                         object_id=object_id))

        def assertRightValuesReturned(restrict_subject, restrict_predicate, restrict_object):
            """
            Assert that the right relationships are returned for the given restrictions.

            :param restrict_subject: whether to restrict the subject
            :param restrict_predicate: whether to restrict the predicate
            :param restrict_object: whether to restrict the object
            """
            restrictions = {}

            def add_restriction(restrict, key, values):
                """
                Add a restriction to the query.

                :param restrict: whether to restrict the given key
                :param key: the key-word parameter of the restriction
                :param values: the array of values for the restriction
                :return: the valid values for the key
                """
                if restrict:
                    restrictions[key] = values[0]
                    return [values[0]]
                return values

            allowed_subjects = add_restriction(restrict_subject, 'subject_id', subjects)
            allowed_predicates = add_restriction(restrict_predicate, 'predicate', predicates)
            allowed_objects = add_restriction(restrict_object, 'object_id', objects)

            relationships = relationship_dao.get(**restrictions)
            expected_len = len(allowed_subjects) * len(allowed_predicates) * len(allowed_objects)
            self.assertEqual(expected_len, len(relationships))

        for restrict_subject in (True, False):
            for restrict_predicate in (True, False):
                for restrict_object in (True, False):
                    assertRightValuesReturned(
                        restrict_subject, restrict_predicate, restrict_object)

    def test_relationshipdao_bad_insert(self):
        """Test that the RelationshipDAO refuses to insert malformed relationships."""
        relationship_dao = self.factory.create_relationship_dao()
        with self.assertRaises(ValueError) as context:
            relationship_dao.insert(subject_id="spam", object_id="eggs")
        self.assertIn('Must supply either', str(context.exception))

    def test_relationshipdao_delete_single_criteria(self):
        """Test that RelationshipDAO is deleting correctly based on single criteria."""
        relationship_dao = self.factory.create_relationship_dao()
        record_dao = self.factory.create_record_dao()

        record_dao.insert(Record('spam', 'test_rec'))
        record_dao.insert(Record('eggs', 'test_rec'))
        record_dao.insert(Record('bacon', 'test_rec'))

        relationship = Relationship(subject_id="spam", object_id="bacon", predicate="loves")
        relationship_2 = Relationship(subject_id="spam", object_id="eggs", predicate="treasures")
        relationship_3 = Relationship(subject_id="eggs", object_id="bacon", predicate="treasures")
        relationship_dao.insert(relationships=[relationship, relationship_2, relationship_3])

        # Test subject id
        self.assertEqual(len(relationship_dao.get(subject_id="spam")), 2)
        relationship_dao.delete(subject_id="spam")
        self.assertEqual(len(relationship_dao.get(subject_id="spam")),
                         0, "Relationships with the target subject_id not deleted")
        self.assertEqual(len(relationship_dao.get(subject_id="eggs")),
                         1, "Relationships without the target subject_id deleted")

        # Test object id
        relationship_dao.insert(relationships=[relationship, relationship_2])
        relationship_dao.delete(object_id="bacon")
        self.assertEqual(len(relationship_dao.get(object_id="bacon")),
                         0, "Relationships with the target object_id not deleted")
        self.assertEqual(len(relationship_dao.get(object_id="eggs")),
                         1, "Relationships without the target object_id deleted")

        # Test predicate
        relationship_dao.insert(relationships=[relationship, relationship_3])
        relationship_dao.delete(predicate="treasures")
        self.assertEqual(len(relationship_dao.get(predicate="treasures")),
                         0, "Relationships with the target predicate not deleted")
        self.assertEqual(len(relationship_dao.get(predicate="loves")),
                         1, "Relationships without the target predicate deleted")

        # Make sure the Records are still in place
        self.assertTrue(all(list(record_dao.exist(['spam', 'eggs', 'bacon']))),
                        "Records deleted during Relationship deletion")

    def test_relationshipdao_delete_multiple_criteria(self):
        """Test that RelationshipDAO is deleting correctly when using multiple criteria."""
        relationship_dao = self.factory.create_relationship_dao()
        record_dao = self.factory.create_record_dao()

        record_dao.insert(Record('spam', 'test_rec'))
        record_dao.insert(Record('eggs', 'test_rec'))
        record_dao.insert(Record('cheese', 'test_rec'))

        relationships = [Relationship(subject_id="spam", object_id="eggs", predicate="loves"),
                         Relationship(subject_id="spam", object_id="eggs", predicate="treasures"),
                         Relationship(subject_id="cheese", object_id="eggs", predicate="loves"),
                         Relationship(subject_id="spam", object_id="cheese", predicate="loves")]
        relationship_dao.insert(relationships)
        rels = relationship_dao.get(subject_id="spam")
        self.assertEqual(len(rels), 3)
        relationship_dao.delete(subject_id="spam", object_id="eggs", predicate="loves")
        rels = relationship_dao.get(subject_id="spam")
        self.assertEqual(len(rels), 2)
        rels = relationship_dao.get(object_id="eggs")
        self.assertEqual(len(rels), 2)
        rels = relationship_dao.get(subject_id="spam", object_id="eggs", predicate="loves")
        self.assertEqual(len(rels), 0)
        self.assertTrue(all(list(record_dao.exist(["spam", "eggs", "cheese"]))))

    def test_relationshipdao_delete_no_criteria(self):
        """Test that RelationshipDAO raises a ValueError if no delete criteria are specified."""
        relationship_dao = self.factory.create_relationship_dao()
        with self.assertRaises(ValueError) as context:
            list(relationship_dao.delete())
        self.assertIn('Must specify at least one of subject_id, object_id, or predicate',
                      str(context.exception))


# Disable the pylint check if and until the team decides to refactor the code
class TestQuery(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """
    Unit tests that specifically deal with queries.

    These tests do not modify the database.
    """

    __test__ = False

    factory = None

    @classmethod
    def setUpClass(cls):
        """
        Initialize variables shared between Query tests.

        Class method to avoid it being re-run per test. Attributes must be set
        to appropriate (backend-specific) values by child.

        :param record_dao: A RecordDAO to perform queries.
        """
        cls.record_dao = None
        create_daos(cls)
        cls.inserted_records = populate_database_with_data(cls.record_dao)

    @classmethod
    def tearDownClass(cls):
        if cls.factory:
            cls.factory.close()

    # Due to the length of this section of tests, tests dealing with specific
    # methods are separated by headers.
    # ############################### get #################################
    def test_recorddao_get_one(self):
        """Test our ability to fetch a single record."""
        just_one = self.record_dao.get("spam3")
        self.assertIsInstance(just_one, Record)
        self.assertEqual(just_one.type, "foo")

    def test_recorddao_get_many(self):
        """Test our ability to fetch several Records, in this case from a generator."""
        many_gen = (x for x in ("spam", "spam2", "spam3"))
        assigned_types = ["run", "run", "foo"]
        returned_types = [x.type for x in self.record_dao.get(many_gen)]
        self.assertEqual(len(returned_types), 3)
        six.assertCountEqual(self, returned_types, assigned_types)

    def test_recorddao_raise_error_for_nonexistant(self):
        """Test that we raise an error for nonexistant ids."""
        with self.assertRaises(ValueError) as context:
            list(self.record_dao.get(["Idontexist", "NeitherdoI"]))
        self.assertIn('No Record found with id', str(context.exception))

    # ###################### get_given_document_uri ##########################
    def test_recorddao_uri_no_wildcards(self):
        """Test that RecordDAO is retrieving based on full uris correctly."""
        exact_match = self.record_dao.get_given_document_uri(uri="beep.png", ids_only=True)
        self.assertEqual(len(list(exact_match)), 1)

    def test_recorddao_uri_no_match(self):
        """Test that the RecordDAO uri query is retrieving no Records when there's no matches."""
        exact_match = self.record_dao.get_given_document_uri(uri="idontexist.png", ids_only=True)
        self.assertEqual(len(list(exact_match)), 0)

    def test_recorddao_uri_takes_generator(self):
        """Test that the uri-query method takes a generator properly."""
        allowed_ids = (x for x in ("spam3", "spam4"))
        exact_match = self.record_dao.get_given_document_uri(uri="beep.png",
                                                             accepted_ids_list=allowed_ids,
                                                             ids_only=True)
        self.assertIsInstance(exact_match, types.GeneratorType,
                              "Method must return a generator.")

    def test_recorddao_uri_returns_generator(self):
        """Test that the uri-query method returns a generator."""
        exact_match = self.record_dao.get_given_document_uri(uri="beep.png", ids_only=True)
        self.assertIsInstance(exact_match, types.GeneratorType,
                              "Method must return a generator.")

    def test_recorddao_uri_one_wildcard(self):
        """Test that RecordDAO is retrieving based on a wildcard-containing uri correctly."""
        end_wildcard = self.record_dao.get_given_document_uri(uri="beep.%", ids_only=True)
        # Note that we're expecting 3 even though there's 4 matches.
        # That's because id "beep" matches twice, but we don't repeat matches.
        self.assertEqual(len(list(end_wildcard)), 3)
        mid_wildcard = self.record_dao.get_given_document_uri(uri="beep%png")
        self.assertEqual(len(list(mid_wildcard)), 2)
        first_wildcard = self.record_dao.get_given_document_uri(uri="%png")
        self.assertEqual(len(list(first_wildcard)), 3)

    def test_recorddao_uri_many_wildcards(self):
        """Test that RecordDAO is retrieving based on many wildcards correctly."""
        multi_wildcard = self.record_dao.get_given_document_uri(uri="%.%")
        self.assertEqual(len(list(multi_wildcard)), 4)
        ids_only = list(self.record_dao.get_given_document_uri(uri="%.%", ids_only=True))
        self.assertEqual(len(ids_only), 4)
        six.assertCountEqual(self, ids_only, ["spam", "spam5", "spam3", "spam4"])

    def test_recorddao_uri_full_wildcard(self):
        """Ensure that a uri=% (wildcard) uri query matches all Records with files."""
        all_wildcard = self.record_dao.get_given_document_uri(uri="%")
        self.assertEqual(len(list(all_wildcard)), 5)

    # ############### get_given_document_uri for Runs ################
    def test_rundao_uri_one_wildcard(self):
        """Test ability to find only Runs by uri (filter out matching non-Run Records)."""
        end_wildcard_id = list(self.record_dao.get_given_document_uri(uri="beep.%",
                                                                      ids_only=True))
        self.assertEqual(len(end_wildcard_id), 3)
        end_wildcard_obj = self.record_dao.get_given_document_uri(uri="beep.%", ids_only=False)
        six.assertCountEqual(self, end_wildcard_id, (x.id for x in end_wildcard_obj))

    # ###################### get_with_max ##########################
    def test_get_with_max(self):
        """Test that we return the id of the record with the highest scalar_name value."""
        max_spam_scal = list(self.record_dao.get_with_max("spam_scal", id_only=True))
        self.assertEqual(max_spam_scal[0], "spam2")

    def test_get_with_max_multi(self):
        """Test we can return the X largest in correct order."""
        max_spam_scals = list(self.record_dao.get_with_max("spam_scal",
                                                           count=2,
                                                           id_only=True))
        self.assertEqual(max_spam_scals, ["spam2", "spam3"])

    # ###################### get_with_min ##########################
    def test_get_with_min(self):
        """Test that we return the id of the record with the lowest scalar_name value."""
        min_spam_scal = list(self.record_dao.get_with_min("spam_scal", id_only=True))
        self.assertEqual(min_spam_scal[0], "spam")

    def test_get_with_min_multi(self):
        """Test we can return the X smallest in correct order."""
        min_spam_scals = list(self.record_dao.get_with_min("spam_scal",
                                                           count=2,
                                                           id_only=True))
        self.assertEqual(min_spam_scals, ["spam", "spam3"])

    # ####################### test_exist ####################################
    def test_one_exists(self):
        """Make sure that we return a correct bool for each ID."""
        hit = self.record_dao.exist('spam')
        self.assertEqual(hit, True)
        miss = self.record_dao.exist('IDonNotExist')
        self.assertEqual(miss, False)

    def test_many_exist(self):
        """Make sure that we return a correct list of Bools"""
        result = list(self.record_dao.exist(id_ for id_ in
                                            ['spam', 'IDoNotExist',
                                             'spam2', 'IAlsoDoNotExist']))
        self.assertEqual(result, [True, False, True, False])

    # ####################### test_data_names ####################################
    def test_data_names_with_string(self):
        """Make sure that we get names of scalar data when given a string."""
        names = set(self.record_dao.data_names(record_type='foo', data_types='scalar'))
        self.assertEqual(names, set(["spam_scal", "spam_scal_2"]))

    def test_data_names_with_list(self):
        """Make sure that we get names of scalar data when given a list."""
        names = set(self.record_dao.data_names(record_type='foo', data_types=['scalar']))
        self.assertEqual(names, set(["spam_scal", "spam_scal_2"]))

    def test_data_names_with_default(self):
        """Make sure that we get names of all data by default."""
        names = set(self.record_dao.data_names(record_type='foo'))
        self.assertEqual(names, set(["spam_scal", "spam_scal_2", "val_data", "val_data_2"]))

    # ####################### test_get_available_types ######################
    def test_get_available_types(self):
        """Make sure that we return a correct list of the types in a datebase."""
        types_found = self.record_dao.get_available_types()
        six.assertCountEqual(self, types_found,
                             ["run", "spamrec", "bar", "foo", "eggrec", "overlap"])

    # ########################### basic data_query ##########################
    def test_recorddao_scalar_datum_query(self):
        """Test that the RecordDAO data query is retrieving based on one scalar correctly."""
        just_right_range = DataRange(min=0, max=300, max_inclusive=True)
        just_right = self.record_dao.data_query(spam_scal=just_right_range)
        self.assertEqual(len(list(just_right)), 3)

    def test_recorddao_scalar_datum_min_max(self):
        """Test that the RecordDAO data query is respecting the inclusivity settings."""
        restricted_range = DataRange(min=10, max=10.99999, min_inclusive=True, max_inclusive=False)
        restricted_recs = self.record_dao.data_query(spam_scal=restricted_range)
        six.assertCountEqual(self, list(restricted_recs), ["spam", "spam3"])

    def test_recorddao_data_query_returns_generator(self):
        """Test that the data-query method returns a generator."""
        too_big_range = DataRange(max=9, max_inclusive=True)
        too_big = self.record_dao.data_query(spam_scal=too_big_range)
        self.assertIsInstance(too_big, types.GeneratorType,
                              "Method must return generator.")

    def test_recorddao_scalar_datum_query_no_match(self):
        """Test that the RecordDAO data query is retrieving no Records when there's no matches."""
        too_small_range = DataRange(min=10.99999, min_inclusive=False)
        too_small = self.record_dao.data_query(spam_scal=too_small_range)
        self.assertFalse(list(too_small))
        nonexistant_scalar = self.record_dao.data_query(nonexistant_scalar=DataRange(-999, 0))
        self.assertFalse(list(nonexistant_scalar))

    def test_recorddao_many_scalar_data_query(self):
        """Test that RecordDAO's data query is retrieving on multiple scalars correctly."""
        spam_and_spam_3 = DataRange(min=10)
        one = self.record_dao.data_query(spam_scal=spam_and_spam_3,
                                         spam_scal_2=10.5)  # Matches spam_3 only
        self.assertEqual(len(list(one)), 1)
        none = self.record_dao.data_query(spam_scal=spam_and_spam_3,
                                          nonexistant=10101010)
        self.assertFalse(list(none))

    def test_recorddao_data_query_shared_data_and_curve_set(self):
        """Test that RecordDAO's data query is retrieving on multiple scalars correctly."""
        # ensure data matches our expectations
        inserted_record = self.inserted_records['shared_curve_set_and_matching_scalar_data']
        scalar_value = inserted_record.data['shared_scalar']['value']
        self.assertEqual(1000, scalar_value)
        inserted_cs_values =\
            inserted_record.curve_sets['cs1']['dependent']['shared_scalar']['value']
        list_min = min(inserted_cs_values)
        list_max = max(inserted_cs_values)
        self.assertEqual(400, list_min)
        self.assertEqual(600, list_max)

        matching_records = self.record_dao.data_query(
            shared_scalar=any_in(DataRange(min=list_min - 10, max=list_min + 10)))
        six.assertCountEqual(self, list(matching_records), [inserted_record.id])

        matching_records = self.record_dao.data_query(
            shared_scalar=any_in(DataRange(min=list_max - 10, max=list_max + 10)))
        six.assertCountEqual(self, list(matching_records), [inserted_record.id])

        matching_records = self.record_dao.data_query(
            shared_scalar=any_in(DataRange(min=scalar_value - 10, max=scalar_value + 10)))
        six.assertCountEqual(self, list(matching_records), [inserted_record.id])

    def test_recorddao_string_datum_query(self):
        """Test that the RecordDAO data query is retrieving based on one string correctly."""
        just_right_range = DataRange(min="astounding", max="runny", max_inclusive=True)
        just_right = self.record_dao.data_query(val_data=just_right_range)
        just_right_list = list(just_right)
        self.assertEqual(len(just_right_list), 2)
        six.assertCountEqual(self, just_right_list, ["spam", "spam3"])

    def test_recorddao_string_datum_query_no_match(self):
        """
        Test that the RecordDAO data query is retrieving no Records when there's no matches.

        String data edition.
        """
        too_big_range = DataRange(max="awesome", max_inclusive=True)
        too_big = self.record_dao.data_query(val_data=too_big_range)
        self.assertFalse(list(too_big))
        nonexistant_string = self.record_dao.data_query(nonexistant_string="narf")
        self.assertFalse(list(nonexistant_string))

    def test_recorddao_many_string_data_query(self):
        """Test that RecordDAO's data query is retrieving on multiple strings correctly."""
        one = self.record_dao.data_query(val_data=DataRange("runny"),  # Matches 1 only
                                         val_data_2="double yolks")  # Matches 1 and 3
        self.assertEqual(list(one), ["spam"])

    def test_recorddao_data_query_strings_and_records(self):
        """Test that the RecordDAO is retrieving on scalars AND strings correctly."""
        just_3 = self.record_dao.data_query(spam_scal=DataRange(10.1, 400),  # 2 and 3
                                            val_data_2="double yolks")  # 1, 3, and 4
        self.assertEqual(list(just_3), ["spam3"])

    # ###################### data_query list queries ########################
    def test_recorddao_data_query_all_in(self):
        """Test that the RecordDAO is retrieving on an all_in DataRange."""
        just_4_and_5 = list(self.record_dao.data_query(
            val_data_list_1=all_in(DataRange(-11, 20, max_inclusive=False))))
        self.assertEqual(len(just_4_and_5), 2)
        self.assertIn("spam4", just_4_and_5)
        self.assertIn("spam5", just_4_and_5)

    def test_recorddao_data_query_scalar_list_any_in(self):
        """Test that the RecordDAO is retrieving on an any_in DataRange."""
        just_5_and_6 = list(self.record_dao.data_query(
            val_data_list_1=any_in(DataRange(-1, 9))))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_data_query_scalar_list_inclusive(self):
        """Test that inclusiveness is respected for all_in and any_in."""
        not_4 = list(self.record_dao.data_query(
            val_data_list_1=any_in(DataRange(-9, 0,
                                             min_inclusive=False,
                                             max_inclusive=True))))  # 5, not 4
        self.assertEqual(len(not_4), 1)
        self.assertIn("spam5", not_4)
        only_5 = list(self.record_dao.data_query(
            val_data_list_1=all_in(DataRange(0, 8,
                                             max_inclusive=True))))  # 5
        self.assertEqual(len(only_5), 1)
        self.assertIn("spam5", only_5)
        none = list(self.record_dao.data_query(
            val_data_list_1=all_in(DataRange(0, 8,
                                             min_inclusive=False))))  # 5
        self.assertEqual(none, [])

    def test_recorddao_data_query_any_in_open_range(self):
        """Test that any-in works with partially open DataRanges."""
        just_5_and_6 = list(self.record_dao.data_query(
            val_data_list_1=any_in(DataRange(min=-1))))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)
        just_4 = list(self.record_dao.data_query(
            val_data_list_1=any_in(DataRange(max=-1))))  # 4
        self.assertEqual(len(just_4), 1)
        self.assertIn("spam4", just_4)

    def test_recorddao_data_query_all_in_open_range(self):
        """Test that all-in works with partially open DataRanges."""
        just_6 = list(self.record_dao.data_query(
            val_data_list_1=all_in(DataRange(min=8))))  # 6
        self.assertEqual(len(just_6), 1)
        self.assertIn("spam6", just_6)
        just_4 = list(self.record_dao.data_query(
            val_data_list_1=all_in(DataRange(max=0))))  # 4
        self.assertEqual(len(just_4), 1)
        self.assertIn("spam4", just_4)

    def test_recorddao_data_query_string_list_has_all(self):
        """Test that the RecordDAO is retrieving on a has_all list of strings."""
        just_5_and_6 = list(self.record_dao.data_query(
            val_data_list_2=has_all('eggs', 'pancake')))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_data_query_string_list_has_any(self):
        """Test that the RecordDAO is retrieving on a has_any list of strings."""
        just_5_and_6 = list(self.record_dao.data_query(
            val_data_list_2=has_any('yellow', 'orange', 'pancake')))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_exists(self):
        """Test that the RecordDAO is retrieving on an exists() call."""
        just_5_and_6 = list(self.record_dao.data_query(flex_data_1=exists()))  # 5 & 6
        self.assertEqual(len(just_5_and_6), 2)
        self.assertIn("spam5", just_5_and_6)
        self.assertIn("spam6", just_5_and_6)

    def test_recorddao_exists_many(self):
        """Test that the RecordDAO is retrieving on multiple exists() calls."""
        just_5 = list(self.record_dao.data_query(flex_data_1=exists(),  # 5 & 6
                                                 flex_data_2=exists()))  # 5
        self.assertEqual(len(just_5), 1)
        self.assertIn("spam5", just_5)

    def test_recorddao_data_query_mixed_list_criteria(self):
        """
        Test that the RecordDAO is retrieving on mixed data criteria.

        Test that we can mix searching on strings, lists of strings, existence, and dataranges.
        """
        just_6 = list(self.record_dao.data_query(
            val_data_list_2=has_all('eggs', 'pancake'),  # 5 & 6
            val_data_list_1=any_in(DataRange(0, 8, max_inclusive=True)),  # 5 & 6
            flex_data_1=exists(),  # 5 & 6
            val_data_3='syrup'))  # 6 only
        self.assertEqual(len(just_6), 1)
        self.assertEqual(just_6[0], "spam6")

    def test_recorddao_data_query_all_list_criteria(self):
        """
        Test that the RecordDAO is retrieving on mixed data criteria.

        Test that we can mix searching on strings, scalars, lists of strings,
        and dataranges, using has_all, has_any, all_in, any_in, and
        simple equivalence.
        """
        no_match = list(self.record_dao.data_query(
            val_data_list_1=any_in(DataRange(8, 8, max_inclusive=True)),  # 5 & 6
            spam_scal_3=DataRange(0, 50),  # 5 only
            val_data_list_2=has_all('eggs'),  # 5 & 6
            val_data_3=all_in(DataRange(7, 21))))  # 6 only
        self.assertFalse(no_match)

        just_5 = list(self.record_dao.data_query(
            val_data_list_1=all_in(DataRange(-11, 30, min_inclusive=False)),  # 5 & 6
            spam_scal_3=DataRange(0, 50),  # 5 only
            val_data_list_2=has_all('pancake'),  # 5 & 6
            val_data_3='sugar'))  # 5 only

        self.assertEqual(len(just_5), 1)
        self.assertEqual(just_5[0], "spam5")

    # ######################### get_all_of_type ###########################
    def test_recorddao_type(self):
        """Test the RecordDAO is retrieving based on type correctly."""
        get_one = list(self.record_dao.get_all_of_type("bar"))
        self.assertEqual(len(get_one), 1)
        self.assertIsInstance(get_one[0], Record)
        self.assertEqual(get_one[0].id, "spam4")
        self.assertEqual(get_one[0].type, "bar")
        self.assertEqual(get_one[0].user_defined, {})

    def test_recorddao_type_none(self):
        """Test that the RecordDAO type query returns no Records when none match."""
        get_none = list(self.record_dao.get_all_of_type("butterscotch"))
        self.assertFalse(get_none)

    def test_recorddao_type_returns_generator(self):
        """Test that the RecordDAO type query returns a generator."""
        ids_only = self.record_dao.get_all_of_type("run")
        self.assertIsInstance(ids_only, types.GeneratorType,
                              "Method must return a generator.")

    def test_recorddao_type_matches_many(self):
        """Test the RecordDAO type query correctly returns multiple Records."""
        ids_only = self.record_dao.get_all_of_type("run", ids_only=True)
        six.assertCountEqual(self, list(ids_only), ["spam", "spam2", "spam5"])

    # ######################### get_with_curve_set #########################
    def test_recorddao_get_with_curve_set(self):
        """Test that the RecordDAO is retrieving based on curve name."""
        get_one = list(self.record_dao.get_with_curve_set("egg_curve"))
        self.assertEqual(len(get_one), 1)
        self.assertIsInstance(get_one[0], Record)
        self.assertEqual(get_one[0].id, "spam")
        self.assertEqual(get_one[0].type, "run")
        self.assertEqual(get_one[0].user_defined, {})

    def test_recorddao_curve_none(self):
        """Test that the RecordDAO curve query returns no Records when none match."""
        get_none = list(self.record_dao.get_with_curve_set("butterscotch"))
        self.assertFalse(get_none)

    def test_recorddao_curve_returns_generator(self):
        """Test that the RecordDAO curve query returns a generator."""
        ids_only = self.record_dao.get_with_curve_set("spam_curve")
        self.assertIsInstance(ids_only, types.GeneratorType,
                              "Method must return a generator.")

    def test_recorddao_curve_matches_many(self):
        """Test the RecordDAO curve query correctly returns multiple Records."""
        ids_only = self.record_dao.get_with_curve_set("spam_curve", ids_only=True)
        six.assertCountEqual(self, list(ids_only), ["spam", "spam2"])

    # ######################### get_all ##################################
    def test_recorddao_get_all(self):
        """Test the RecordDAO is retrieving all Records."""
        all_records = list(self.record_dao.get_all())
        self.assertEqual(len(all_records), len(self.inserted_records))
        self.assertIsInstance(all_records[0], Record)

    def test_recorddao_get_all_returns_generator(self):
        """Test that the RecordDAO type query returns a generator."""
        all_records = self.record_dao.get_all()
        self.assertIsInstance(all_records, types.GeneratorType,
                              "Method must return a generator.")

    def test_recorddao_get_all_matches_many(self):
        """Test the RecordDAO type query correctly returns multiple Records."""
        all_ids = self.record_dao.get_all(ids_only=True)
        six.assertCountEqual(self, list(all_ids), list(self.inserted_records.keys()))

    # ###################### get_data_for_records ########################
    def test_recorddao_get_datum_for_record(self):
        """Test that we're getting a datum for one record correctly."""
        for_one = self.record_dao.get_data_for_records(id_list=["spam"],
                                                       data_list=["spam_scal"])
        self.assertEqual(for_one["spam"]["spam_scal"],
                         {"value": 10, "units": "pigs", "tags": ["hammy"]})

    def test_recorddao_get_data_for_record(self):
        """Test that we're getting several pieces of data for one record correctly."""
        many_scalars = ["spam_scal", "eggs_scal", "val_data"]
        for_one = self.record_dao.get_data_for_records(id_list=["spam"],
                                                       data_list=many_scalars)
        six.assertCountEqual(self, for_one["spam"].keys(), ["spam_scal", "val_data"])
        self.assertEqual(for_one["spam"]["val_data"],
                         {"value": "runny", "tags": ["edible"]})

    def test_recorddao_get_data_for_records(self):
        """Test that we're getting data for many records correctly."""
        many_ids = ["spam", "spam2", "spam3"]
        many_scalars = ["spam_scal", "eggs_scal", "spam_scal_2", "val_data"]
        for_many = self.record_dao.get_data_for_records(id_list=many_ids,
                                                        data_list=many_scalars)
        six.assertCountEqual(self, for_many.keys(), ["spam", "spam2", "spam3"])
        six.assertCountEqual(self, for_many["spam3"].keys(), ["spam_scal",
                                                              "spam_scal_2",
                                                              "val_data"])
        self.assertEqual(for_many["spam3"]["val_data"]["tags"], ["edible", "simple"])

    def test_recorddao_get_data_for_gen_of_records(self):
        """Test that we're getting data for a generator of many records correctly."""
        many_ids = (x for x in ("spam", "spam2", "spam3"))
        many_scalars = ["spam_scal", "eggs_scal", "spam_scal_2", "val_data"]
        for_gen = self.record_dao.get_data_for_records(id_list=many_ids,
                                                       data_list=many_scalars)
        six.assertCountEqual(self, for_gen.keys(), ["spam", "spam2", "spam3"])
        self.assertEqual(for_gen["spam3"]["val_data"]["tags"], ["edible", "simple"])

    def test_recorddao_get_no_data_for_nonexistant_records(self):
        """Test that we're not getting data for records that don't exist."""
        for_none = self.record_dao.get_data_for_records(id_list=["nope", "nada"],
                                                        data_list=["gone", "away"])
        self.assertFalse(for_none)

    def test_recorddao_get_data_for_all_records(self):
        """Test that we're getting data for all records when id_list isn't specified."""
        for_all = self.record_dao.get_data_for_records(data_list=["val_data_3"])
        six.assertCountEqual(self, for_all.keys(), ["spam5", "spam6"])
        six.assertCountEqual(self, for_all["spam5"].keys(), ["val_data_3"])

    # ###################### get_scalars (legacy) ########################
    def test_recorddao_get_scalars(self):
        """Test that RecordDAO is getting scalars for a record correctly (legacy method)."""
        get_one = self.record_dao.get_scalars(id="spam",
                                              scalar_names=["spam_scal"])
        self.assertEqual(len(get_one), 1)
        self.assertEqual(get_one["spam_scal"]["units"], "pigs")
        get_more = self.record_dao.get_scalars(id="spam",
                                               scalar_names=["spam_scal_2",
                                                             "spam_scal"])
        self.assertEqual(len(get_more), 2)
        self.assertEqual(get_more["spam_scal"]["tags"], ["hammy"])
        self.assertFalse(get_more["spam_scal_2"]["units"])
        self.assertFalse(get_more["spam_scal_2"]["tags"])
        get_gone = self.record_dao.get_scalars(id="spam",
                                               scalar_names=["value-1"])
        self.assertFalse(get_gone)
        get_norec = self.record_dao.get_scalars(id="wheeee",
                                                scalar_names=["value-1"])
        self.assertFalse(get_norec)

    def test_get_with_mime_type_single_record(self):
        """Test that the RecordDAO mimetype query retrieves only one Record."""
        just_5 = list(self.record_dao.get_with_mime_type(mimetype="audio/wav",
                                                         ids_only=False))
        self.assertEqual(len(just_5), 1)
        self.assertEqual(just_5[0].id, "spam5")

    def test_get_with_mime_type_multi_records(self):
        """Test that the RecordDAO mimetype query retrieves multiple Records."""
        just_3_and_4 = list(self.record_dao.get_with_mime_type(mimetype="image/png",
                                                               ids_only=False))
        self.assertEqual(len(just_3_and_4), 2)
        six.assertCountEqual(self, [just_3_and_4[0].id, just_3_and_4[1].id],
                             ["spam3", "spam4"])

    def test_get_with_mime_type_no_match(self):
        """Test that the RecordDAO mimetype query retrieves no Records when there is no match."""
        get_none = list(self.record_dao.get_with_mime_type(mimetype="nope/nonexist",
                                                           ids_only=False))
        self.assertFalse(get_none)

    def test_get_with_mime_type_single_id(self):
        """Test that the RecordDAO mimetype query retrieves only one ID."""
        just_5_id = list(self.record_dao.get_with_mime_type(mimetype="audio/wav",
                                                            ids_only=True))
        self.assertEqual(len(just_5_id), 1)
        self.assertEqual(just_5_id[0], "spam5")

    def test_get_with_mime_type_multi_ids(self):
        """Test that the RecordDAO mimetype query retrieves multiple IDs."""
        just_3_and_4_ids = list(self.record_dao.get_with_mime_type(mimetype="image/png",
                                                                   ids_only=True))
        self.assertEqual(len(just_3_and_4_ids), 2)
        six.assertCountEqual(self, just_3_and_4_ids, ["spam3", "spam4"])

    def test_get_with_mime_type_no_match_id_only(self):
        """Test that the RecordDAO mimetype query retrieves no IDs when there is no match."""
        get_no_ids = list(self.record_dao.get_with_mime_type(mimetype="nope/nonexist",
                                                             ids_only=True))
        self.assertFalse(get_no_ids)


class TestImportExport(unittest.TestCase):
    """
    Unit tests that involve importing and exporting.

    If it creates or consumes a file, it goes here.
    """

    __test__ = False

    def create_dao_factory(self):
        """
        Create the DAO to run Import/Export tests.

        Must be implemented by child, likely via its mixin class (ex: SQLMixin).
        """
        raise NotImplementedError

    def setUp(self):
        """
        Set up info needed for each Import/Export test.

        Attributes must be set to appropriate (backend-specific) values by
        child.
        """
        self.factory = self.create_dao_factory()
        self.test_file_path = tempfile.NamedTemporaryFile(
            suffix='.csv',
            delete=False,
            mode='w+b')

    def tearDown(self):
        self.factory.close()
        remove_file(self.test_file_path.name)

    # Importing
    def test_full_import(self):
        """
        Do an import using the utils importer, making sure all data is ingested.

        Also acts as a sanity check on all DAOs.
        """
        json_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 "test_files/sample_doc_1.json")
        import_json(factory=self.factory, json_paths=json_path)
        parent = self.factory.create_record_dao().get("parent_1")
        relation = self.factory.create_relationship_dao().get(object_id="child_1")
        rec_handler = self.factory.create_record_dao()
        child = rec_handler.get("child_1")
        canonical = json.loads(io.open(json_path, encoding='utf-8').read())
        self.assertEqual(canonical['records'][0]['type'], parent.type)
        self.assertEqual(canonical['records'][1]['type'], child.type)
        child_from_uri = list(rec_handler.get_given_document_uri("foo.png"))
        child_from_scalar_id = list(rec_handler.data_query(scalar_1=387.6))
        full_record = rec_handler.get(child_from_scalar_id[0])
        self.assertEqual(canonical['records'][1]['type'], full_record.type)
        self.assertEqual(child.id, child_from_uri[0].id)
        self.assertEqual(child.id, full_record.id)
        self.assertEqual(canonical['relationships'][0]['predicate'],
                         relation[0].predicate)

    # Exporting
    @patch('sina.utils._export_csv')
    def test_export_csv_good_input_mocked(self, mock):
        """
        Test export with mocked _csv_export() and good input.

        Test export with of one scalar from sql database to a csv file. Mock
        _export_csv() so we don't actually write to file.
        """
        populate_database_with_data(self.factory.create_record_dao())
        scalars = ['spam_scal']
        export(
            factory=self.factory,
            id_list=['spam_scal'],
            scalar_names=scalars,
            output_type='csv',
            output_file=self.test_file_path.name)
        self.assertTrue(mock.called)
        self.assertEqual(mock.call_count, 1)
        _, kwargs = mock.call_args
        self.assertEqual(kwargs['scalar_names'][0], scalars[0])

    @patch('sina.utils._export_csv')
    def test_export_csv_bad_input_mocked(self, mock):
        """
        Test export with mocked _csv_export() and bad input.

        Test export with of one scalar from sql database to a csv file. Mock
        _export_csv() so we don't actually write to file. Bad input in this
        case is an output_type that is not supported.
        """
        populate_database_with_data(self.factory.create_record_dao())
        scalars = ['spam_scal']
        with self.assertRaises(ValueError) as context:
            export(
                factory=self.factory,
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
        populate_database_with_data(self.factory.create_record_dao())
        export(
            factory=self.factory,
            id_list=['spam'],
            scalar_names=['spam_scal'],
            output_type='csv',
            output_file=self.test_file_path.name)

        with io.open(self.test_file_path.name, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader]
            self.assertEqual(rows[0], ['id', 'spam_scal'])
            # 10 is stored but 10.0 is retrieved due to SQL column types
            self.assertAlmostEqual(float(rows[1][1]), 10)

    def test_export_two_scalar_csv_good_input(self):
        """Test exporting two scalars & runs correctly to csv from sql."""
        populate_database_with_data(self.factory.create_record_dao())
        export(
            factory=self.factory,
            id_list=['spam3', 'spam'],
            scalar_names=['spam_scal', 'spam_scal_2'],
            output_type='csv',
            output_file=self.test_file_path.name)

        with io.open(self.test_file_path.name, 'r', encoding='utf-8') as csvfile:
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
            factory=self.factory,
            id_list=['child_1'],
            scalar_names=['bad-scalar'],
            output_type='csv',
            output_file=self.test_file_path.name)

        with io.open(self.test_file_path.name, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0], ['id', 'bad-scalar'])

    def test__export_csv(self):
        """Test we can write out data to csv and ensures everything expected is present."""
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
        with io.open(self.test_file_path.name, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = [row for row in reader]
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0], ['id'] + scalar_names)
            self.assertEqual(rows[1], ['a_fake_id_1', '123', '456'])
            self.assertEqual(rows[2], ['a_fake_id_2', '0.1', '-12'])
