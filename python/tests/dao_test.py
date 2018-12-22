"""Test logic related to DAOs."""

import unittest
from mock import patch, MagicMock

from sina.dao import RecordDAO
from sina.model import Record


class TestRecordDAO(unittest.TestCase):
    """Unit test for logic related to DAOs."""
    def setUp(self):
        """
        Create records used for testing.
        """
        self.record_one = Record(id="spam",
                                 type="new_eggs",
                                 data={"foo": {"value": 12},
                                       "bar": {"value": "1",
                                               "tags": ["in"]}},
                                 files=[{"uri": "ham.png", "mimetype": "png"},
                                        {"uri": "ham.curve", "tags": ["hammy"]}],
                                 user_defined={})
        self.record_two = Record(id="spam",
                                 type="new_eggs",
                                 data={"foo": {"value": 12},
                                       "bar": {"value": "1",
                                               "tags": ["in"]}},
                                 files=[{"uri": "ham.png", "mimetype": "png"},
                                        {"uri": "ham.curve", "tags": ["hammy"]}],
                                 user_defined={})
        self.record_three = Record(id="spam2",
                                   type="super_eggs",
                                   data={"foo": {"value": 13},
                                         "bar": {"value": "1",
                                                 "tags": ["in"]}},
                                   files=[{"uri": "ham.png", "mimetype": "png"},
                                          {"uri": "ham.curve", "tags": ["hammy"]}],
                                   user_defined={})

    @patch('sina.model.compare_records')
    @patch('sina.dao.RecordDAO.get')
    def test_compare_records_ids(self, mock_get, mock_compare):
        """
        Check that we get the records of the ids and call compare_records().
        """
        RecordDAO.__abstractmethods__ = set()
        record_dao = RecordDAO()
        record_dao.compare_records_ids(self.record_one.id,
                                       self.record_three.id)
        # Check we called RecordDAO.get twice with proper params
        _, kwargs1 = mock_get.call_args_list[0]
        _, kwargs2 = mock_get.call_args_list[1]
        self.assertEqual(kwargs1['id'], 'spam')
        self.assertEqual(kwargs2['id'], 'spam2')
        self.assertEqual(mock_get.call_count, 2)

        # Check we called model.compare_records with proper params
        _, kwargs3 = mock_compare.call_args
        self.assertTrue(isinstance(kwargs3['record_one'], MagicMock))
        self.assertTrue(isinstance(kwargs3['record_two'], MagicMock))
        self.assertEqual(kwargs3['exclude_paths'], [])
        self.assertEqual(kwargs3['exclude_types'], [])
        self.assertEqual(kwargs3['ignore_order'], True)
        self.assertEqual(kwargs3['report_repetition'], False)
        self.assertEqual(kwargs3['significant_digits'], None)
        self.assertEqual(kwargs3['verbose_level'], 2)
        self.assertEqual(kwargs3['view'], 'tree')
        self.assertEqual(mock_compare.call_count, 1)
