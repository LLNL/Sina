#!/bin/python
"""Test Sina's optional command line tools."""

import sys
import unittest
import logging

from six.moves import cStringIO
from nose.plugins.attrib import attr

from sina.model import Record
try:
    import sina.cli_tools
except ImportError:
    # Not having the cli tools for tests is a valid case and should be coupled with
    # an "-a '!cli_tools'" flag for Nose. If not, another error will be raised.
    # Even though none of the tests in this file are run with the above flag,
    # Nose doesn't know that initially, and thus tries these imports anyways.
    pass

LOGGER = logging.getLogger(__name__)
TARGET = None


@attr('cli_tools')
class TestRecordDiff(unittest.TestCase):
    """Unit tests that involve diffing Records using the CLI."""

    def setUp(self):
        """Create some Records to compare."""
        self.record_one = Record(id="spam",
                                 type="new_eggs",
                                 data={"foo": {"value": 12},
                                       "bar": {"value": "1", "tags": ["in"]}},
                                 files=[{"uri": "ham.png", "mimetype": "png"},
                                        {"uri": "ham.curve", "tags": ["hammy"]}],
                                 user_defined={})
        self.record_two = Record(id="spam",
                                 type="new_eggs",
                                 data={"foo": {"value": 12},
                                       "bar": {"value": "1", "tags": ["in"]}},
                                 files=[{"uri": "ham.png", "mimetype": "png"},
                                        {"uri": "ham.curve", "tags": ["hammy"]}],
                                 user_defined={})
        self.record_three = Record(id="spam2",
                                   type="super_eggs",
                                   data={"foo": {"value": 13},
                                         "bar": {"value": "1", "tags": ["in"]}},
                                   files=[{"uri": "ham.png", "mimetype": "png"},
                                          {"uri": "ham.curve", "tags": ["hammy"]}],
                                   user_defined={})

    def test_pprint_deep_diff_equal(self):
        """Check we print an empty texttable when comparing an empty ddiff."""
        try:
            # Grab stdout and send to string io
            sys.stdout = cStringIO()
            sina.cli_tools.print_diff_records(record_one=self.record_one,
                                              record_two=self.record_one)
            std_output = sys.stdout.getvalue()
            self.assertEqual(std_output, '+-----+------+------+\n'
                                         '| key | spam | spam |\n'
                                         '+=====+======+======+\n'
                                         '+-----+------+------+\n\n')
        finally:
            # Reset stdout
            sys.stdout = sys.__stdout__

    def test_pprint_deep_diff_not_equal(self):
        """Check we print a correct texttable when comparing nonempty ddiff."""
        try:
            # Grab stdout and send to string io
            sys.stdout = cStringIO()
            sina.cli_tools.print_diff_records(record_one=self.record_one,
                                              record_two=self.record_three)
            std_output = sys.stdout.getvalue()
            self.assertEqual(
                std_output,
                "+--------------------------+----------+------------+\n"
                "|           key            |   spam   |   spam2    |\n"
                "+==========================+==========+============+\n"
                "| ['data']['foo']['value'] |    12    |     13     |\n"
                "+--------------------------+----------+------------+\n"
                "|         ['type']         | new_eggs | super_eggs |\n"
                "+--------------------------+----------+------------+\n\n")
        finally:
            # Reset stdout
            sys.stdout = sys.__stdout__
