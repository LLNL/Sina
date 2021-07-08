"""Test the SQL portion of the DAO structure."""

import unittest
import json

from sina.model import Record, Run, Relationship, CurveSet
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
        self.curve_set_one = CurveSet("foo", {})

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
        """Test to make sure we can add data when a curve set already has the same name."""
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
        """Test to make sure we can set the data when a curve set already has the same name."""
        rec = model.Record(id='data_test', type='test')
        cs1 = CurveSet("cs1")
        cs1.add_independent("time", [1, 2, 3])
        cs1.add_dependent("density", [4, 5, 6])
        rec.add_curve_set(cs1)
        rec.data = {'density': {'value': 40}}
        self.assertIn('density', rec.data)
        self.assertIn('density', rec.curve_sets['cs1']['dependent'])

    def test_add_data_conflicts_with_curve_set(self):
        """Test to make sure we can add data when a curve set already has the same name."""
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

    def test_set_curve_set(self):
        """Test to make sure that we can update CurveSets for a Record."""
        foo_curve_set = CurveSet("foo", {"independent": {"time": {"value": [1, 2, 3]}}})
        rec = model.Record(id="curve_set_test", type="test")
        rec.set_curve_set(foo_curve_set)
        self.assertEqual({"foo": foo_curve_set.raw}, rec.curve_sets)
        # Need to ensure that both are updated
        vol_vals = [0, 0, 0.1]
        foo_curve_set.add_dependent(curve_name="volume", value=vol_vals)
        self.assertEqual(foo_curve_set["dependent"]["volume"]["value"], vol_vals)
        self.assertEqual(rec.get_curve_set("foo").dependent["volume"]["value"], vol_vals)
        # and that replacement works
        foo_2_curve_set = CurveSet("foo", {"independent": {"conc": {"value": [0, 0.5, 2]}}})
        rec.set_curve_set(foo_2_curve_set)
        self.assertEqual({"foo": foo_2_curve_set.raw}, rec.curve_sets)

    def test_add_curve_set(self):
        """
        Test to make sure that we can add CurveSets to a Record.

        Also test that a ValueError is raised if a CurveSet by that name already exists.
        """
        foo_curve_set = CurveSet("foo", {"independent": {"time": {"value": [1, 2, 3]}},
                                         "dependent": {}})
        rec = model.Record(id="curve_set_test", type="test")
        foo_curve_set = rec.add_curve_set("foo")
        foo_curve_set.add_independent("time", value=[1, 2, 3])
        self.assertEqual({"foo": foo_curve_set.raw}, rec.curve_sets)
        with self.assertRaises(ValueError) as context:
            rec.add_curve_set(foo_curve_set)
        self.assertIn('Duplicate curve set', str(context.exception))

    def test_remove_file(self):
        """Test add/remove file to a record"""
        complete_files = {"/foo/bar.txt": {}}
        rec = model.Record(id="file_test", type="test")
        rec.add_file("/foo/bar.txt")
        self.assertEqual(complete_files, rec.files)
        rec.remove_file("/foo/bar.txt")
        self.assertEqual(rec.files, {})
        # we can remove it even though it's gone
        rec.remove_file("/foo/bar.txt")
        self.assertEqual(rec.files, {})

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
        """Allow data and curve sets to have the same name."""
        complete_curveset = CurveSet("set_1")
        complete_curveset.add_independent("time", [1, 2])
        complete_curveset.add_dependent("density", [3, 4])
        complete_data = {"density": {"value": 40}}
        rec = model.Record(id="data_test", type="test", data=complete_data)
        rec.add_curve_set(complete_curveset)
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

    def test_record_get_curve_set(self):
        """Ensure accessing via get_curve_set returns CurveSets."""
        rec = model.Record(id="spam_test", type="test")
        with self.assertRaises(AttributeError) as context:
            egg_set = rec.get_curve_set("egg_set")
        self.assertIn("has no curve set", str(context.exception))

        rec.add_curve_set("egg_set")
        egg_set = rec.get_curve_set("egg_set")
        self.assertIsInstance(egg_set, CurveSet)
        self.assertEqual(egg_set.name, "egg_set")
        self.assertEqual(egg_set.raw, {"independent": {}, "dependent": {}})
        num_boiled_vals = [0, 0, 0, 1]
        egg_set.add_dependent("num_boiled", num_boiled_vals)
        filled_egg_set = rec.get_curve_set("egg_set")
        self.assertIsInstance(filled_egg_set, CurveSet)
        self.assertEqual(filled_egg_set.get_dependent("num_boiled")["value"],
                         num_boiled_vals)

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
        flat_rec = model.flatten_library_content(self.libdata_rec)
        string_raw = json.dumps(flat_rec.raw)
        self.assertIn('"runtime": {"value": 87', string_raw)
        self.assertIn('"runtime": {"value": 32', string_raw)
        self.assertIn('"speed": {"value": [0, 2]', string_raw)
        self.assertNotIn('"outer_lib/runtime"', string_raw)
        self.assertNotIn('"inner_lib/runtime"', string_raw)
        self.assertNotIn('"outer_lib/inner_lib/distance"', string_raw)

    def test_generate_json(self):
        """Ensure JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"greeting", '
                       '"data":{"language": {"value": "english"},'
                       '"mood": {"value": "friendly"}},'
                       '"library_data": {"my_lib": {"data": {"mood": {"value": "joyful"}}}},'
                       '"curve_sets":{"learning": {'
                       '"independent":{"time": {"value": [1, 2, 3], "tags": ["raw"]}},'
                       '"dependent": {"words": {"value": [0, 6, 12], "units": "sec"}}}},'
                       '"files":{"pronounce.wav": {}},'
                       '"user_defined":{"good": "morning"}}')
        test_record = model.Record("hello", "greeting")
        test_record.data = {"language": {"value": "english"},
                            "mood": {"value": "friendly"}}
        learning_curves = test_record.add_curve_set("learning")
        learning_curves.add_independent("time", [1, 2, 3], tags=["raw"])
        learning_curves.add_dependent("words", [0, 6, 12], units="sec")
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

    # CurveSet
    def test_init(self):
        """
        Test that an empty CurveSet gets an empty dict for independents and dependents.

        Also tests that tags are unset.
        """
        self.assertEqual(self.curve_set_one["independent"], {})
        self.assertEqual(self.curve_set_one["dependent"], {})
        self.assertIsNone(self.curve_set_one.raw.get("tags"))

    def test_curve_set_add_independent(self):
        """
        Test that we can add an independent curve to the CurveSet.

        Also test that an error is raised if an independent curve by that name already exists.
        """
        curve = self.curve_set_one.add_independent("time")
        vals = [1, 2, 3]
        curve.value = vals
        self.assertEqual(curve.raw, self.curve_set_one["independent"]["time"], vals)
        with self.assertRaises(ValueError) as context:
            self.curve_set_one.add_independent("time")
        self.assertIn('Duplicate curve', str(context.exception))
        self.assertIn('independent', str(context.exception))

    def test_curve_set_add_dependent(self):
        """Test that we can add a dependent curve to the CurveSet."""
        curve = self.curve_set_one.add_dependent("volume")
        vals = [0, 0, 0.5]
        curve.value = vals
        self.assertEqual(curve.raw, self.curve_set_one.dependent["volume"], vals)
        with self.assertRaises(ValueError) as context:
            self.curve_set_one.add_dependent("volume")
        self.assertIn('Duplicate curve', str(context.exception))
        self.assertIn('dependent', str(context.exception))

    def test_curve_set_get_dependent(self):
        """Test that we can get a dependent curve from the CurveSet."""
        curve = self.curve_set_one.add_dependent("distance")
        curve.value = [200000, 2000000000]
        self.assertEqual(curve.raw, self.curve_set_one.get_dependent("distance"))
        with self.assertRaises(AttributeError) as context:
            self.curve_set_one.get_dependent("volume")
        self.assertIn("has no dependent", str(context.exception))

    def test_curve_set_get_independent(self):
        """Test that we can get an independent curve from the CurveSet."""
        curve = self.curve_set_one.add_independent("time")
        curve.value = [1, 2]
        self.assertEqual(curve.raw, self.curve_set_one.get_independent("time"))
        with self.assertRaises(AttributeError) as context:
            self.curve_set_one.get_independent("concentration")
        self.assertIn("has no independent", str(context.exception))

    def test_curve_set_get(self):
        """Test that we can get a curve from the CurveSet."""
        ind_curve = self.curve_set_one.add_independent("time")
        ind_curve.value = [1, 2]
        dep_curve = self.curve_set_one.add_dependent("distance")
        dep_curve.value = [200000, 2000000000]
        self.assertEqual(ind_curve.raw, self.curve_set_one.get("time"))
        self.assertEqual(dep_curve.raw, self.curve_set_one.get("distance"))
        # While the overlap is unsupported, we still do define the behavior
        weird_curve = self.curve_set_one.add_independent("distance")
        weird_curve.value = [1, 3]
        self.assertEqual(weird_curve.raw, self.curve_set_one.get("distance"))
        with self.assertRaises(AttributeError) as context:
            self.curve_set_one.get("concentration")
        self.assertIn("has no curve", str(context.exception))

    def test_curve_set_as_dict(self):
        """Test that we can transform a dict or CurveSet into a dict."""
        source_dict = {"independent": {"time": {"value": [1, 2, 3]}},
                       "dependent": {"volume": {"value": [10, 12, 9]}}}
        source_curve_set = CurveSet("test", raw=source_dict)
        self.assertEqual(CurveSet.as_dict(source_dict), source_dict)
        self.assertEqual(CurveSet.as_dict(source_curve_set), source_dict)

    def test_curve_set_as_curve_set(self):
        """Test that we can transform a dict or CurveSet into a CurveSet."""
        source_dict = {"independent": {"time": {"value": [1, 2, 3]}},
                       "dependent": {"volume": {"value": [10, 12, 9]}}}
        source_curve_set = CurveSet("test", raw=source_dict)
        unnamed_curve_set = CurveSet("<unnamed CurveSet>", raw=source_dict)
        self.assertEqual(CurveSet.as_curve_set(source_dict).name, unnamed_curve_set.name)
        self.assertEqual(CurveSet.as_curve_set(source_dict).raw, unnamed_curve_set.raw)
        self.assertEqual(CurveSet.as_curve_set(source_curve_set).name, source_curve_set.name)
        self.assertEqual(CurveSet.as_curve_set(source_curve_set).raw, source_curve_set.raw)
