"""Test the SQL portion of the DAO structure."""

import unittest
import json

from sina.model import Record, Run, Relationship
import sina.model as model

# Accessing "private" methods is necessary for testing them.
# pylint: disable=protected-access

# Our test classes, as with the other tests, have public methods *as* tests.
# pylint: disable=too-many-public-methods


class TestModel(unittest.TestCase):
    """Unit tests for the model utility methods."""

    def setUp(self):
        """Create records used for testing."""
        self.record_one = Record(id="spam",
                                 type="new_eggs",
                                 data={"list_scalars": {"value": [1, 2, 3]},
                                       "list_strings": {"value": ['apple',
                                                                  'orange']},
                                       "bar": {"value": "1",
                                               "tags": ["in"]}},
                                 files={"ham.png": {"mimetype": "png"},
                                        "ham.curve": {"tags": ["hammy"]}},
                                 user_defined={})
        self.record_two = Record(id="spam2",
                                 type="new_eggs",
                                 data={"bad_list": {"value": ['bad', 3]},
                                       "bad_list_2": {"value":
                                                      [1, 2, {'not': 'allowed'}]},
                                       "bar": {"value": "1",
                                               "tags": ["in"]}},
                                 files={"ham.png": {"mimetype": "png"},
                                        "ham.curve": {"tags": ["hammy"]}},
                                 user_defined={})
        self.library_data = {"outer_lib": {
            "data": {"runtime": {"value": 44, "tags": ["output"]}},
            "library_data": {
                "inner_lib": {
                    "data": {"runtime": {"value": 32},
                             "mark_distances": {"value": [0, 5], "units": "km"}},
                    "curve_sets": {
                        "dist": {
                            "independent": {"time": {"value": [0, 0.5]}},
                            "dependent": {"distance": {"value": [0, 6],
                                                       "units": "km"},
                                          "speed": {"value": [0, 2]}},
                            "independent_order": ["time"],
                            "dependent_order": ["distance", "speed"]
                        }
                    }}}}}
        self.libdata_rec = Record(id="lotsalibs",
                                  type="lib_pal",
                                  data={"runtime": {"value": 87}},
                                  curve_sets={"dist": {
                                      "independent": {"time": {"value": [1, 2]}},
                                      "dependent": {"distance": {"value": [0, 10]}}}},
                                  library_data=self.library_data,
                                  user_defined={})
        self.relationship_one = Relationship(subject_id="spam",
                                             predicate="supersedes",
                                             object_id="spam2")

    # Record
    def test_is_valid(self):
        """Ensure Record validation is working."""
        spam = model.Record(id="spam_and_eggs", type="recipe")

        # Minimal, valid run
        self.assertTrue(spam.is_valid())
        # Value that's a missing value
        spam.data = {"eggstate": {"tags": ["tEGGxture"]}}
        self.assertFalse(spam.is_valid()[0])
        # Correct minimal value that has a bad tag list
        spam.data = {"eggstate": {"value": "runny", "tags": "tEGGxture"}}
        self.assertFalse(spam.is_valid()[0])
        # Second value is the bad one
        spam.data = {"eggstate": {"value": "runny", "tags": "tEGGxture"},
                     'spam': 'spam'}
        self.assertFalse(spam.is_valid()[0])
        # Data needs to be a dict, not a list!
        # We have to use ["data"] notation as .data will trigger the setter,
        # which TypeErrors on non-dicts.
        spam["data"] = [{"value": "runny", "tags": ["tEGGxture"]}]
        self.assertFalse(spam.is_valid()[0])

        spam.data = {"eggstate": {"value": "runny", "tags": ["tEGGxture"]}}
        # Files as a list instead of a dict
        spam.files = {"spam.txt": ["text/plain"]}
        self.assertFalse(spam.is_valid()[0])

        # Correct minimal file that has a bad tag list
        spam.files = {"spam.log": {"tags": "output"}}
        self.assertFalse(spam.is_valid()[0])

        spam.files = {"spam.log": {"mimetype": "text/plain", "tags": ["output"]}}

        spam.type = "recipe"

        # User_defined as a list instead of a dict
        spam.user_defined = ["hello"]
        self.assertFalse(spam.is_valid()[0])

        spam.user_defined = {"hello": "greeting"}
        # all previous errors fixed: "maximal" valid run
        self.assertTrue(spam.is_valid()[0])

    def test__is_valid_library_data(self):
        """Test that we're properly validating library data."""
        self.library_data["malformed_lib"] = {"data": 2}
        spam = model.Record(id="spam", type="eggs", library_data=self.library_data)
        self.assertFalse(spam.is_valid()[0])
        self.assertIn(spam.is_valid()[1][0], "Record spam's malformed_lib/data field "
                                             "must be a dictionary!")

    def test__is_valid_list_good(self):
        """Test we report a list as valid when it is."""
        self.assertTrue(model._is_valid_list(
            self.record_one.data['list_scalars']['value']))
        self.assertTrue(model._is_valid_list(
            self.record_one.data['list_strings']['value']))

    def test__is_valid_list_unsupported(self):
        """
        Test we raise a ValueError if given an unsupported entry type.

        If the list contains an entry other than a string or scalar, raise a
        ValueError.
        """
        with self.assertRaises(ValueError) as context:
            model._is_valid_list(self.record_two.data['bad_list_2']['value'])
        self.assertIn("List of data contains entry that isn't a "
                      "string or scalar.", str(context.exception))

    def test__is_valid_list_bad_mix(self):
        """
        Test we return False if given a mixture of string/scalars in a list.

        If the list contains some mixture of strings and scalars, we should
        return False with the corresponding bad indices.
        """
        is_valid, scalar_index, string_index = model._is_valid_list(
            self.record_two.data['bad_list']['value'])
        self.assertFalse(is_valid)
        self.assertEqual(scalar_index, 1)
        self.assertEqual(string_index, 0)

    def test_set_data(self):
        """Test to make sure we can set data correctly for a Record."""
        complete_data = {"density": {"value": 12},
                         "init_energy": {"value": 100, "units": "J", "tags": ["input"]}}
        rec = model.Record(id="data_test", type="test")
        rec.set_data("density", 12)
        rec.set_data("init_energy", 100, tags=["input"], units="J")
        self.assertEqual(complete_data, rec.data)

    def test_set_file(self):
        """Test to make sure we can set files correctly for a Record."""
        complete_files = {"/foo/bar.txt": {},
                          "/foo/spam.txt": {"mimetype": "text", "tags": ["doc"]}}
        rec = model.Record(id="file_test", type="test")
        rec.set_file("/foo/bar.txt")
        rec.set_file("/foo/spam.txt", mimetype="text", tags=["doc"])
        self.assertEqual(complete_files, rec.files)

    def test_set_data_update(self):
        """Test to make sure we can update data for a Record."""
        complete_data = {"init_energy": {"value": 100, "units": "J", "tags": ["input"]}}
        rec = model.Record(id="data_test", type="test")
        rec.set_data("init_energy", 250, tags=["output"], units="MJ")
        rec.set_data("init_energy", 100, tags=["input"], units="J")
        self.assertEqual(complete_data, rec.data)

    def test_set_data_item_conflicts_with_curve_set(self):
        """Test to make sure we can add data when a curve set already has the same name"""
        rec = model.Record(id="data_test", type="test")
        curve_sets = {
            'cs1': {
                'independent': {'time': {'value': [1, 2, 3]}},
                'dependent': {'density': {'value': [4, 5, 6]}}
            }
        }
        rec.curve_sets = curve_sets
        rec.set_data("density", 40)
        self.assertIn('density', rec.data)
        self.assertIn('density', rec.curve_sets['cs1']['dependent'])

    def test_set_data_conflicts_with_curve_set(self):
        """Test to make sure we can set the data when a curve set already has the same name"""
        rec = model.Record(id='data_test', type='test')
        curve_sets = {
            'cs1': {
                'independent': {'time': {'value': [1, 2, 3]}},
                'dependent': {'density': {'value': [4, 5, 6]}}
            }
        }
        rec.curve_sets = curve_sets
        rec.data = {'density': {'value': 40}}
        self.assertIn('density', rec.data)
        self.assertIn('density', rec.curve_sets['cs1']['dependent'])

    def test_add_data_conflicts_with_curve_set(self):
        """Test to make sure we can add data when a curve set already has the same name"""
        rec = model.Record(id="data_test", type="test")
        curve_sets = {
            'cs1': {
                'independent': {'time': {'value': [1, 2, 3]}},
                'dependent': {'density': {'value': [4, 5, 6]}}
            }
        }
        rec.curve_sets = curve_sets
        rec.add_data("density", 40)
        self.assertIn('density', rec.data)
        self.assertIn('density', rec.curve_sets['cs1']['dependent'])

    def test_set_file_update(self):
        """Test to make sure we can update files for a Record."""
        complete_files = {"/foo/spam.txt": {"mimetype": "text", "tags": ["doc"]}}
        rec = model.Record(id="file_test", type="test")
        rec.set_file("/foo/spam.txt", mimetype="image", tags=["photo"])
        rec.set_file("/foo/spam.txt", mimetype="text", tags=["doc"])
        self.assertEqual(complete_files, rec.files)

    def test_add_file(self):
        """Test to make sure that, when adding a file that already exists, an error is raised."""
        complete_files = {"/foo/bar.txt": {}}
        rec = model.Record(id="file_test", type="test")
        rec.add_file("/foo/bar.txt")
        self.assertEqual(complete_files, rec.files)
        with self.assertRaises(ValueError) as context:
            rec.add_file("/foo/bar.txt", mimetype="text")
        self.assertIn('Duplicate file', str(context.exception))

    def test_add_data(self):
        """Test to make sure that, when adding a datum that already exists, an error is raised."""
        complete_data = {"density": {"value": 12}}
        rec = model.Record(id="data_test", type="test")
        rec.add_data("density", 12)
        self.assertEqual(complete_data, rec.data)
        with self.assertRaises(ValueError) as context:
            rec.add_data("density", 40)
        self.assertIn('Duplicate datum', str(context.exception))

    def test_add_curve_with_data_overlap(self):
        """Allow data and curve sets to have the same name"""
        complete_curvesets = {"set_1": {"independent": {"time": {"value": [1, 2]}},
                                        "dependent": {"density": {"value": [3, 4]}}}}
        complete_data = {"density": {"value": 40}}
        rec = model.Record(id="data_test", type="test", data=complete_data,
                           curve_sets=complete_curvesets)
        self.assertEqual(40, rec.data['density']['value'])
        self.assertListEqual([3, 4],
                             rec.curve_sets['set_1']['dependent']['density']['value'])

    def test_record_access(self):
        """Ensure accessing record attribs using rec["spam"]."""
        rec = model.Record(id="spam_test", type="test")
        rec["eggs"] = "nutritious"
        self.assertEqual(rec['eggs'], "nutritious")
        self.assertEqual(rec.__dict__["raw"]["eggs"], "nutritious")
        del rec["eggs"]
        self.assertTrue('eggs' not in rec.__dict__["raw"])

    def test_flatten_library_content_data(self):
        """Ensure that library flattening is happening for data."""
        flat_rec = model.flatten_library_content(self.libdata_rec)
        # Check basic existence
        self.assertTrue("runtime" in flat_rec.data.keys())
        self.assertTrue("outer_lib/runtime" in flat_rec.data.keys())
        self.assertTrue("outer_lib/inner_lib/runtime" in flat_rec.data.keys())
        # Check that the values are correct
        self.assertEqual(flat_rec.data["runtime"]["value"], 87)
        self.assertEqual(flat_rec.data["outer_lib/runtime"]["value"], 44)
        self.assertEqual(flat_rec.data["outer_lib/inner_lib/runtime"]["value"], 32)
        # Check that other keys/info are preserved
        self.assertEqual(flat_rec.data["outer_lib/inner_lib/mark_distances"]["value"], [0, 5])
        self.assertEqual(flat_rec.data["outer_lib/inner_lib/mark_distances"]["units"], "km")
        self.assertEqual(flat_rec.data["outer_lib/runtime"]["tags"], ["output"])

    def test_flatten_library_content_curves(self):
        """Ensure that library flattening is happening for curves."""
        flat_rec = model.flatten_library_content(self.libdata_rec)
        # Check basic existence
        self.assertTrue("dist" in flat_rec.curve_sets.keys())
        self.assertTrue("time" in flat_rec.curve_sets["dist"]["independent"].keys())
        self.assertTrue("distance" in flat_rec.curve_sets["dist"]["dependent"].keys())
        nest_curve = "outer_lib/inner_lib/dist"
        self.assertTrue(nest_curve in flat_rec.curve_sets.keys())
        self.assertTrue("outer_lib/inner_lib/time"
                        in flat_rec.curve_sets[nest_curve]["independent"].keys())
        self.assertTrue("outer_lib/inner_lib/distance"
                        in flat_rec.curve_sets[nest_curve]["dependent"].keys())
        self.assertTrue("outer_lib/inner_lib/speed"
                        in flat_rec.curve_sets[nest_curve]["dependent"].keys())
        # Check that the values are correct
        self.assertEqual(flat_rec.curve_sets["dist"]["independent"]["time"]["value"], [1, 2])
        prefix = "outer_lib/inner_lib/"
        nest_curve = prefix+"dist"
        self.assertEqual(flat_rec.curve_sets[nest_curve]["independent"][prefix+"time"]["value"],
                         [0, 0.5])
        self.assertEqual(flat_rec.curve_sets[nest_curve]["dependent"][prefix+"distance"]["value"],
                         [0, 6])
        self.assertEqual(flat_rec.curve_sets[nest_curve]["dependent"][prefix+"speed"]["value"],
                         [0, 2])
        # Check that other info is preserved
        self.assertEqual(flat_rec.curve_sets[nest_curve]["dependent_order"], [prefix+"distance",
                                                                              prefix+"speed"])
        self.assertEqual(flat_rec.curve_sets[nest_curve]["dependent"][prefix+"distance"]["units"],
                         "km")

    def test_flatten_library_content_raw(self):
        """Ensure that library flattening does not affect the raw."""

    def test_generate_json(self):
        """Ensure JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"greeting", '
                       '"data":{"language": {"value": "english"},'
                       '"mood": {"value": "friendly"}},'
                       '"library_data": {"my_lib": {"data": {"mood": {"value": "joyful"}}}},'
                       '"curve_sets":{"learning": {'
                       '"independent":{"time": {"value": [1, 2, 3]}},'
                       '"dependent": {"words": {"value": [0, 6, 12]}}}},'
                       '"files":{"pronounce.wav": {}},'
                       '"user_defined":{"good": "morning"}}')
        test_record = model.Record("hello", "greeting")
        test_record.data = {"language": {"value": "english"},
                            "mood": {"value": "friendly"}}
        test_record.curve_sets = {"learning": {
            "independent": {"time": {"value": [1, 2, 3]}},
            "dependent": {"words": {"value": [0, 6, 12]}}}}
        test_record.library_data = {"my_lib": {"data": {"mood": {"value": "joyful"}}}}
        test_record.files = {"pronounce.wav": {}}
        test_record.user_defined = {"good": "morning"}
        # Raw is explicitly not reproduced in to_json()
        self.assertTrue(test_record.is_valid())
        self.assertEqual(sorted(set(json.loads(target_json))),
                         sorted(set(json.loads(test_record.to_json()))))

    def test_generate_json_run(self):
        """Ensure Run JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"run",'
                       '"application":"foo", "user":"JohnD", "version":0,'
                       '"data": {"language": {"value":"english"},'
                       '"mood": {"value":"friendly"}},'
                       '"library_data": {"my_lib": {"data": {"mood": {"value": "joyful"}}}},'
                       '"curve_sets":{"learning": {'
                       '"independent":{"time": {"value": [1, 2, 3]}},'
                       '"dependent": {"words": {"value": [0, 6, 12]}}}},'
                       '"files":{"pronounce.wav": {}},'
                       '"user_defined":{"good": "morning"}}')
        test_run = model.Run("hello", "foo", user="JohnD", version=0)
        test_run.data = {"language": {"value": "english"},
                         "mood": {"value": "friendly"}}
        test_run.library_data = {"my_lib": {"data": {"mood": {"value": "joyful"}}}}
        test_run.files = {"pronounce.wav": {}}
        test_run.user_defined = {"good": "morning"}
        self.assertTrue(test_run.is_valid())
        self.assertEqual(sorted(set(json.loads(target_json))),
                         sorted(set(json.loads(test_run.to_json()))))

    def test_gen_record_from_json_good(self):
        """Ensure we can generate a Record from valid json input."""
        json_input = {"id": "spam",
                      "type": "eggs",
                      "user_defined": {"water": "bread"},
                      "data": {"eggs": {"value": 12,
                                        "units": "cm",
                                        "tags": ["runny"]}},
                      "library_data": self.library_data,
                      "files": {"eggs.brek": {"mimetype": "egg",
                                              "tags": ["fried"]}}}
        record = model.generate_record_from_json(json_input=json_input)
        self.assertEqual(json_input['id'], record.id)
        self.assertEqual(json_input['type'], record.type)
        self.assertEqual(json_input['user_defined'], record.user_defined)
        self.assertEqual(json_input['data'], record.data)
        self.assertEqual(json_input['library_data'], record.library_data)
        self.assertEqual(json_input['files'], record.files)

    def test_gen_record_from_json_bad(self):
        """
        Ensure we throw a ValueError when creating a Record from bad json.

        This is because we do not want to allow creation of Records that do not
        adhere to the Sina schema.
        """
        json_input = {"type": "eggs",
                      "user_defined": {"water": "bread"},
                      "data": {"eggs": {"value": 12,
                                        "units": "cm",
                                        "tags": ["runny"]}},
                      "files": {"eggs.brek": {"mimetype": "egg",
                                              "tags": ["fried"]}}}
        with self.assertRaises(ValueError) as context:
            model.generate_record_from_json(json_input=json_input)
        self.assertIn("Missing required key <'id'>.", str(context.exception))

    def test_gen_run_from_json_good(self):
        """Ensure we can generate a Run from valid json input."""
        json_input = {"id": "spam",
                      "type": "run",
                      "user": "cook",
                      "application": "skillet",
                      "version": "1.2",
                      "user_defined": {"water": "bread"},
                      "curve_sets": {
                          "set_1": {
                              "independent": {
                                  "time": {"value": [1, 2]}
                              },
                              "dependent": {
                                  "density": {"value": [1, 2]}
                              }
                          }
                      },
                      "data": {"eggs": {"value": 12,
                                        "units": "cm",
                                        "tags": ["runny"]}},
                      "files": {"eggs.brek": {"mimetype": "egg",
                                              "tags": ["fried"]}}}
        run = model.generate_run_from_json(json_input=json_input)
        self.assertEqual(json_input['id'], run.id)
        self.assertEqual(json_input['type'], run.type)
        self.assertEqual(json_input['user'], run.user)
        self.assertEqual(json_input['application'], run.application)
        self.assertEqual(json_input['version'], run.version)
        self.assertEqual(json_input['user_defined'], run.user_defined)
        self.assertEqual(json_input['data'], run.data)
        self.assertEqual(json_input['curve_sets'], run.curve_sets)
        self.assertEqual(json_input['files'], run.files)

    def test_gen_run_from_json_bad(self):
        """
        Ensure we throw a ValueError when creating a Run from bad json.

        This is because we do not want to allow creation of Runs that do not
        adhere to the Sina schema.
        """
        json_input = {"id": "spam",
                      "type": "eggs",
                      "user_defined": {"water": "bread"},
                      "data": {"eggs": {"value": 12,
                                        "units": "cm",
                                        "tags": ["runny"]}},
                      "files": {"eggs.brek": {"mimetype": "egg",
                                              "tags": ["fried"]}}}
        with self.assertRaises(ValueError) as context:
            model.generate_run_from_json(json_input=json_input)
        self.assertIn("Missing required key <'application'>.",
                      str(context.exception))

    def test_convert_record_to_run_good(self):
        """Test we return a Run when given a Record with valid input."""
        raw_record = {"id": "run1",
                      "type": "run",
                      "application": "foo",
                      "user": "John Doe",
                      "data": {}, "curve_sets": {},
                      "library_data": {},
                      "user_defined": {},
                      "files": {}, "version": None}
        rec = model.generate_record_from_json(json_input=raw_record)
        converted_run = model.convert_record_to_run(record=rec)
        self.assertEqual(converted_run.raw, raw_record)
        self.assertEqual(type(converted_run), Run)

    def test_convert_record_to_run_bad(self):
        """Test we raise a ValueError when given a Record with bad input."""
        raw_record = {"id": "sub1",
                      "type": "not_a_run",
                      "application": "foo",
                      "user": "John Doe",
                      "data": {}, "user_defined": {},
                      "files": {}, "version": None}
        rec = model.generate_record_from_json(json_input=raw_record)
        with self.assertRaises(ValueError) as context:
            model.convert_record_to_run(record=rec)
        self.assertIn('Record must be of subtype Run to convert to Run. Given',
                      str(context.exception))

    # Relationship
    def test_relationship_to_json(self):
        """Test that Relationship's to_json() is working as intended."""
        expected_json = '{"subject": "spam", "predicate": "supersedes", "object": "spam2"}'
        self.assertEqual(json.loads(expected_json), json.loads(self.relationship_one.to_json()))
