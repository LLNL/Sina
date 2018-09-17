"""Test the SQL portion of the DAO structure."""

import unittest
import json

import sina.model as model


class TestModel(unittest.TestCase):
    """Unit tests for the model utility methods."""

    # Record
    def test_is_valid(self):
        """Ensure Record validation is working."""
        spam = model.Record(id="spam_and_eggs", type="recipe")

        # Minimal, valid run
        self.assertTrue(spam._is_valid())
        # Value that's missing a name
        spam.data = [{"value": "runny"}]
        self.assertFalse(spam._is_valid()[0])
        # Value that's a missing value
        spam.data = [{"name": "eggstate"}]
        self.assertFalse(spam._is_valid()[0])
        # Correct minimal value that has a bad tag list
        spam.data = [{"name": "eggstate", "value": "runny", "tags": "tEGGxture"}]
        self.assertFalse(spam._is_valid()[0])
        # Second value is the bad one
        spam.data = [{"name": "eggstate", "value": "runny", "tags": ["tEGGxture"]},
                     'spam']
        self.assertFalse(spam._is_valid()[0])

        spam.data = [{"name": "eggstate", "value": "runny", "tags": ["tEGGxture"]}]
        # File that's missing a uri
        spam.files = [{"mimetype": "text/plain"}]
        self.assertFalse(spam._is_valid()[0])
        # Correct minimal file that has a bad tag list
        spam.files = [{"uri": "spam.log", "tags": "output"}]
        self.assertFalse(spam._is_valid()[0])

        spam.files = [{"uri": "spam.log", "mimetype": "text/plain", "tags": ["output"]}]

        spam.type = "recipe"

        spam.user_defined = {"eggs_in_dozen": 12}

        # all previous errors fixed: "maximal" valid run
        self.assertTrue(spam._is_valid()[0])

    def test_generate_json(self):
        """Ensure JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"greeting", '
                       '"data":[{"name":"language", "value":"english"},'
                       '{"name":"mood","value":"friendly"}],'
                       '"files":[{"uri":"pronounce.wav"}],'
                       '"user_defined":{"good": "morning"}}')
        test_record = model.Record("hello", "greeting")
        test_record.data = [{"name": "language", "value": "english"},
                            {"name": "mood", "value": "friendly"}]
        test_record.files = [{"uri": "pronounce.wav"}]
        test_record.user_defined = {"good": "morning"}
        # Raw is explicitly not reproduced in to_json()
        self.assertTrue(test_record._is_valid())
        self.assertEqual(sorted(set(json.loads(target_json))),
                         sorted(set(json.loads(test_record.to_json()))))

    def test_generate_json_run(self):
        """Ensure Run JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"run",'
                       '"application":"foo", "user":"JohnD", "version":0,'
                       '"data":[{"name":"language", "value":"english"},'
                       '{"name":"mood","value":"friendly"}],'
                       '"files":[{"uri":"pronounce.wav"}],'
                       '"user_defined":{"good": "morning"}}')
        test_run = model.Run("hello", "foo", user="JohnD", version=0)
        test_run.data = [{"name": "language", "value": "english"},
                         {"name": "mood", "value": "friendly"}]
        test_run.files = [{"uri": "pronounce.wav"}]
        test_run.user_defined = {"good": "morning"}
        self.assertTrue(test_run._is_valid())
        self.assertEqual(sorted(set(json.loads(target_json))),
                         sorted(set(json.loads(test_run.to_json()))))

    def test_generate_record_from_json_good(self):
        """Ensure we can generate a Record from valid json input."""
        json_input = {
                         "id": "spam",
                         "type": "eggs",
                         "user_defined": {"water": "bread"},
                         "data": [{
                                     "name": "eggs",
                                     "value": 12,
                                     "units": "cm",
                                     "tags": ["runny"]
                                    }
                                  ],
                         "files": [{
                                     "uri": "eggs.brek",
                                     "mimetype": "egg",
                                     "tags": ["fried"]
                                   }
                                   ]
                     }
        record = model.generate_record_from_json(json_input=json_input)
        self.assertEqual(json_input['id'], record.id)
        self.assertEqual(json_input['type'], record.type)
        self.assertEqual(json_input['user_defined'], record.user_defined)
        self.assertEqual(json_input['data'], record.data)
        self.assertEqual(json_input['files'], record.files)

    def test_generate_record_from_json_bad(self):
        """
        Ensure we throw a ValueError when creating a Record from bad json.

        This is because we do not want to allow creation of Records that do not
        adhere to the Mnoda schema.
        """
        json_input = {
                         "type": "eggs",
                         "user_defined": {"water": "bread"},
                         "data": [{
                                     "name": "eggs",
                                     "value": 12,
                                     "units": "cm",
                                     "tags": ["runny"]
                                    }
                                  ],
                         "files": [{
                                     "uri": "eggs.brek",
                                     "mimetype": "egg",
                                     "tags": ["fried"]
                                   }
                                   ]
                     }
        with self.assertRaises(ValueError) as context:
            model.generate_record_from_json(json_input=json_input)
        self.assertIn("Missing required key <'id'>.", str(context.exception))

    def test_generate_run_from_json_good(self):
        """Ensure we can generate a Run from valid json input."""
        json_input = {
                         "id": "spam",
                         "type": "run",
                         "user": "cook",
                         "application": "skillet",
                         "version": "1.2",
                         "user_defined": {"water": "bread"},
                         "data": [{
                                     "name": "eggs",
                                     "value": 12,
                                     "units": "cm",
                                     "tags": ["runny"]
                                    }
                                  ],
                         "files": [{
                                     "uri": "eggs.brek",
                                     "mimetype": "egg",
                                     "tags": ["fried"]
                                   }
                                   ]
                     }
        run = model.generate_run_from_json(json_input=json_input)
        self.assertEqual(json_input['id'], run.id)
        self.assertEqual(json_input['type'], run.type)
        self.assertEqual(json_input['user'], run.user)
        self.assertEqual(json_input['application'], run.application)
        self.assertEqual(json_input['version'], run.version)
        self.assertEqual(json_input['user_defined'], run.user_defined)
        self.assertEqual(json_input['data'], run.data)
        self.assertEqual(json_input['files'], run.files)

    def test_generate_run_from_json_bad(self):
        """
        Ensure we throw a ValueError when creating a Run from bad json.

        This is because we do not want to allow creation of Runs that do not
        adhere to the Mnoda schema.
        """
        json_input = {
                         "id": "spam",
                         "type": "eggs",
                         "user_defined": {"water": "bread"},
                         "data": [{
                                     "name": "eggs",
                                     "value": 12,
                                     "units": "cm",
                                     "tags": ["runny"]
                                    }
                                  ],
                         "files": [{
                                     "uri": "eggs.brek",
                                     "mimetype": "egg",
                                     "tags": ["fried"]
                                   }
                                   ]
                     }
        with self.assertRaises(ValueError) as context:
            model.generate_run_from_json(json_input=json_input)
        self.assertIn("Missing required key <'application'>.", str(context.exception))
