"""Test the SQL portion of the DAO structure."""

import unittest
import json

import sina.model as model


class TestModel(unittest.TestCase):
    """Unit tests for the model utility methods."""

    # Record
    def test_is_valid(self):
        """Ensure Record validation is working."""
        spam = model.Record(record_id="spam_and_eggs", record_type="recipe")

        # Minimal, valid run
        self.assertTrue(spam.is_valid())
        # Value that's missing a name
        spam.values = [{"value": "runny"}]
        self.assertFalse(spam.is_valid())
        # Value that's a missing value
        spam.values = [{"name": "eggstate"}]
        self.assertFalse(spam.is_valid())
        # Correct minimal value that has a bad tag list
        spam.values = [{"name": "eggstate", "value": "runny", "tags": "tEGGxture"}]
        self.assertFalse(spam.is_valid())
        # Second value is the bad one
        spam.values = [{"name": "eggstate", "value": "runny", "tags": ["tEGGxture"]},
                       'spam']
        self.assertFalse(spam.is_valid())

        spam.values = [{"name": "eggstate", "value": "runny", "tags": ["tEGGxture"]}]
        # File that's missing a uri
        spam.files = [{"mimetype": "text/plain"}]
        self.assertFalse(spam.is_valid())
        # Correct minimal file that has a bad tag list
        spam.files = [{"uri": "spam.log", "tags": "output"}]
        self.assertFalse(spam.is_valid())

        spam.files = [{"uri": "spam.log", "mimetype": "text/plain", "tags": ["output"]}]
        # Type is reserved for children
        spam.record_type = "run"
        self.assertFalse(spam.is_valid())

        spam.record_type = "recipe"
        # Raw isn't real json
        spam.raw = "hello there"
        self.assertFalse(spam.is_valid())

        spam.raw = '{"the_raw_can_differ": "from the contents"}'
        # user_defined is not a dictionary
        spam.user_defined = 12
        self.assertFalse(spam.is_valid())

        spam.user_defined = {"eggs_in_dozen": 12}

        # all previous errors fixed: "maximal" valid run
        self.assertTrue(spam.is_valid())

    def test_generate_json(self):
        """Ensure JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"greeting", '
                       '"values":[{"name":"language", "value":"english"},'
                       '{"name":"mood","value":"friendly"}],'
                       '"files":[{"uri":"pronounce.wav"}],'
                       '"user_defined":{"good": "morning"}}')
        test_record = model.Record("hello", "greeting")
        test_record.values = [{"name": "language", "value": "english"},
                              {"name": "mood", "value": "friendly"}]
        test_record.files = [{"uri": "pronounce.wav"}]
        test_record.user_defined = {"good": "morning"}
        # Raw is explicitly not reproduced in to_json()
        test_record.raw = '{"none_of_this": "should appear"}'
        self.assertTrue(test_record.is_valid())
        self.assertEqual(sorted(set(json.loads(target_json))),
                         sorted(set(json.loads(test_record.to_json()))))

    def test_generate_json_run(self):
        """Ensure Run JSON is generating properly."""
        target_json = ('{"id":"hello", "type":"run",'
                       '"application":"foo", "user":"JohnD", "version":0,'
                       '"values":[{"name":"language", "value":"english"},'
                       '{"name":"mood","value":"friendly"}],'
                       '"files":[{"uri":"pronounce.wav"}],'
                       '"user_defined":{"good": "morning"}}')
        test_run = model.Run("hello", "foo", user="JohnD", version=0)
        test_run.values = [{"name": "language", "value": "english"},
                           {"name": "mood", "value": "friendly"}]
        test_run.files = [{"uri": "pronounce.wav"}]
        test_run.user_defined = {"good": "morning"}
        # Raw is explicitly not reproduced in to_json()
        test_run.raw = '{"none_of_this": "should appear"}'
        self.assertTrue(test_run.is_valid())
        self.assertEqual(sorted(set(json.loads(target_json))),
                         sorted(set(json.loads(test_run.to_json()))))
