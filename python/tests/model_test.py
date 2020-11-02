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

    def test_add_data_with_curve_overlap(self):
        """Test for error raising when same-name curve and datum are added."""
        complete_curvesets = {"set_1": {"independent": {"density": {"value": [1, 2]}},
                                        "dependent": {"density": {"value": [1, 2]}}}}
        rec = model.Record(id="data_test", type="test", curve_sets=complete_curvesets)
        with self.assertRaises(ValueError) as context:
            rec.add_data("density", 40)
        self.assertIn('is already the name of a curve', str(context.exception))
        # Subtle difference between add_data() and just assigning the entire data chunk
        # Errors are different, as the latter can have more than one collision.
        with self.assertRaises(ValueError) as context:
            rec.data = {"density": {"value": 40}}
        self.assertIn('overlapping curve and data entries', str(context.exception))

    def test_add_curve_with_data_overlap(self):
        """Test for error raising when same-name datum and curve are added."""
        complete_curvesets = {"set_1": {"independent": {"density": {"value": [1, 2]}},
                                        "dependent": {"density": {"value": [1, 2]}}}}
        complete_data = {"density": {"value": 40}}
        rec = model.Record(id="data_test", type="test", data=complete_data)
        with self.assertRaises(ValueError) as context:
            rec.curve_sets = complete_curvesets
        self.assertIn('overlapping curve and data entries', str(context.exception))

    def test_record_access(self):
        """Ensure accessing record attribs using rec["spam"]."""
        rec = model.Record(id="spam_test", type="test")
        rec["eggs"] = "nutritious"
        self.assertEqual(rec['eggs'], "nutritious")
        self.assertEqual(rec.__dict__["raw"]["eggs"], "nutritious")
        del rec["eggs"]
        self.assertTrue('eggs' not in rec.__dict__["raw"])

    def test_generate_json(self):
        """Ensure JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"greeting", '
                       '"data":{"language": {"value": "english"},'
                       '"mood": {"value": "friendly"}},'
                       '"curve_sets":{"learning": {'
                       '"independent":{"time": {"value": [1, 2, 3]}},'
                       '"dependent": {"words": {"value": [0, 6, 12]}}}},'
                       '"files":{"pronounce.wav": {}},'
                       '"user_defined":{"good": "morning"}}')
        test_record = model.Record("hello", "greeting")
        test_record.data = {"language": {"value": "english"},
                            "mood": {"value": "friendly"}}
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
                       '"curve_sets":{"learning": {'
                       '"independent":{"time": {"value": [1, 2, 3]}},'
                       '"dependent": {"words": {"value": [0, 6, 12]}}}},'
                       '"files":{"pronounce.wav": {}},'
                       '"user_defined":{"good": "morning"}}')
        test_run = model.Run("hello", "foo", user="JohnD", version=0)
        test_run.data = {"language": {"value": "english"},
                         "mood": {"value": "friendly"}}
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
                      "files": {"eggs.brek": {"mimetype": "egg",
                                              "tags": ["fried"]}}}
        record = model.generate_record_from_json(json_input=json_input)
        self.assertEqual(json_input['id'], record.id)
        self.assertEqual(json_input['type'], record.type)
        self.assertEqual(json_input['user_defined'], record.user_defined)
        self.assertEqual(json_input['data'], record.data)
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

    def test_test_gen_run_from_json_good_bad_data_overlap(self):
        """Test for error raising when same-name curve and datum are added."""
        json_input = {
            "id": "rec1",
            "type": "run",
            "application": "test_app",
            "data": {"density": {"value": 2}},
            "curve_sets": {
                "set_1": {
                    "independent": {
                        "time": {"value": [1, 2]}
                    },
                    "dependent": {
                        "density": {"value": [1, 2]}
                    }
                }
            }
        }
        with self.assertRaises(ValueError) as context:
            model.generate_run_from_json(json_input=json_input)
        self.assertIn("overlapping curve and data entries", str(context.exception))


    def test_convert_record_to_run_good(self):
        """Test we return a Run when given a Record with valid input."""
        raw_record = {"id": "run1",
                      "type": "run",
                      "application": "foo",
                      "user": "John Doe",
                      "data": {}, "curve_sets": {},
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
