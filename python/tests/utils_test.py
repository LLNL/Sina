"""
Tests for Sina utilities.

Note that testing options may be limited in some cases.  For example, the
get_example_path function depends on the SINA_TEST_KERNEL environment, which
should always be set during testing (through tox); however, the function is
written such that this should not be a testing issue.
"""
import os
import shutil
import unittest
import sina.utils
from sina.utils import DataRange

# Path to the directory for running tests involving temporary files.  (Use this
# file's directory as the basis for the path for now.)
RUN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                        "tests", "run_tests", "sina_utils"))


class TestSinaUtils(unittest.TestCase):
    """Tests for Sina Utilities functions."""

    def setUp(self):
        """Set up the tests."""
        if os.path.isdir(RUN_PATH):
            shutil.rmtree(RUN_PATH, True)

        os.makedirs(RUN_PATH)
        if "SINA_TEST_KERNEL" not in os.environ:
            os.environ["SINA_TEST_KERNEL"] = "sina-unittest"

    def tearDown(self):
        """Tear down the tests."""
        if os.path.isdir(RUN_PATH):
            shutil.rmtree(RUN_PATH, True)

    def test_get_example_path_no_db(self):
        """Test the function when there is no database present."""
        with self.assertRaises(ValueError):
            sina.utils.get_example_path("missing.sqlite3",
                                        example_dirs=RUN_PATH)

    def test_get_example_path_test_db(self):
        """
        Test the function when there is a test "database" present.

        The function doesn't care about the file type so create an empty text
        file.
        """
        suffix = '-test'
        path_format = "test_db/first{}.txt"
        filename = os.path.join(RUN_PATH, path_format.format(suffix))
        os.makedirs(os.path.dirname(filename))
        with open(filename, "w") as fout:
            fout.write("\n")

        result = sina.utils.get_example_path(path_format.format(''), suffix,
                                             RUN_PATH)
        self.assertEqual(filename, result,
                         "Expected {}, not {}".format(filename, result))
        os.remove(filename)

    def test_get_example_path_db(self):
        """
        Test the function when there is a test "database" present.

        The function doesn't care about the file type so create an empty text
        file.
        """
        filename = os.path.join(RUN_PATH, "test_db2/another.txt")
        os.makedirs(os.path.dirname(filename))
        with open(filename, "w") as fout:
            fout.write("\n")

        result = sina.utils.get_example_path(filename, '-test2', RUN_PATH)
        self.assertEqual(filename, result,
                         "Expected {}, not {}".format(filename, result))
        os.remove(filename)

    def test_basic_data_range_scalar(self):
        """Test basic DataRange creation using scalars."""
        basic_case = DataRange(1, 2)
        self.assertEqual(basic_case.min, 1)
        self.assertEqual(basic_case.max, 2)
        self.assertTrue(basic_case.min_inclusive)
        self.assertFalse(basic_case.max_inclusive)

    def test_basic_data_range_string(self):
        """
        Test basic DataRange creation using strings.

        We test both to ensure no bad assumptions are being made, as previously
        we only handled scalars in our ranges.
        """
        with_strings = DataRange("foo_a", "foo_c")
        self.assertEqual(with_strings.min, "foo_a")
        self.assertEqual(with_strings.max, "foo_c")
        self.assertTrue(with_strings.min_inclusive)
        self.assertFalse(with_strings.max_inclusive)

    def test_data_range_inclusivity_assignment(self):
        """Test DataRange creation including inclusivity."""
        flipped_inclusivity = DataRange(1, 2, min_inclusive=False, max_inclusive=True)
        self.assertFalse(flipped_inclusivity.min_inclusive)
        self.assertTrue(flipped_inclusivity.max_inclusive)

    def test_data_range_bad_assignment(self):
        """Tests invalid assignments for DataRanges."""
        with self.assertRaises(TypeError) as context:
            DataRange(30, "fast")
        self.assertIn('Bad type for portion of range', str(context.exception))
        with self.assertRaises(TypeError) as context:
            DataRange(["foo", "bar"], ["spam", "eggs"])
        self.assertIn('Bad type for portion of range', str(context.exception))
        with self.assertRaises(ValueError) as context:
            DataRange(30, 1)
        self.assertIn('min must be <= max', str(context.exception))

    def test_data_range_equality(self):
        """Test the DataRange equality operator."""
        basic_case = DataRange(1, 2)
        flipped_inclusivity = DataRange(1, 2e0, min_inclusive=False, max_inclusive=True)
        with_strings = DataRange("foo_a", "foo_c")
        basic_case_again = DataRange(1, 2)
        self.assertEqual(basic_case, basic_case_again)
        self.assertNotEqual(basic_case, flipped_inclusivity)
        self.assertNotEqual(basic_case, with_strings)

    def test_data_range_identity(self):
        """Test functions that return what kind of range the DataRange is."""
        numerical = DataRange(min=1)
        lexographic = DataRange(max="foo_c")
        empty = DataRange()
        self.assertTrue(numerical.is_numeric_range())
        self.assertFalse(numerical.is_lexographic_range())
        self.assertTrue(lexographic.is_lexographic_range())
        self.assertFalse(lexographic.is_numeric_range())
        self.assertFalse(empty.is_numeric_range())
        self.assertFalse(empty.is_lexographic_range())

    def test_data_range_string_setters_with_scalars(self):
        """Test the functions that use strings to set up DataRanges with scalar vals."""
        flipped_inclusivity = DataRange(1, 2e0, min_inclusive=False, max_inclusive=True)
        flipped_inclusivity.parse_min("[0")
        self.assertEqual(flipped_inclusivity.min, 0)
        self.assertTrue(flipped_inclusivity.min_inclusive)
        flipped_inclusivity.parse_max("4)")
        self.assertEqual(flipped_inclusivity.max, 4)
        self.assertFalse(flipped_inclusivity.max_inclusive)
        # None should automatically set inclusivity to False
        flipped_inclusivity.parse_min("[")
        self.assertIsNone(flipped_inclusivity.min)
        self.assertFalse(flipped_inclusivity.min_inclusive)

    def test_data_range_string_setters_with_strings(self):
        """Test the functions that use strings to set up DataRanges with string vals."""
        # Strings must follow python variable naming conventions, so we don't
        # test strings like '4' or 'some=body'
        with_strings = DataRange("foo_a", "foo_c")
        with_strings.parse_min("(a_p3pp3r_mint")
        self.assertEqual(with_strings.min, 'a_p3pp3r_mint')
        self.assertFalse(with_strings.min_inclusive)
        with_strings.parse_max('spam]')
        self.assertEqual(with_strings.max, 'spam')
        self.assertTrue(with_strings.max_inclusive)

    def test_data_range_bad_string_setters_min(self):
        """Test invalid string setters for DataRanges. For min only."""
        flipped_inclusivity = DataRange(1, 2, min_inclusive=False, max_inclusive=True)
        with_strings = DataRange("foo_a", "foo_c")
        with self.assertRaises(TypeError) as context:
            flipped_inclusivity.parse_min("(cat")
        self.assertIn('Bad type for portion of range', str(context.exception))
        with self.assertRaises(ValueError) as context:
            with_strings.parse_min("spam")
        self.assertIn('Bad inclusiveness specifier', str(context.exception))

    def test_data_range_bad_string_setters_max(self):
        """Test invalid string setters for DataRanges. For max only."""
        flipped_inclusivity = DataRange(1, 2, min_inclusive=False, max_inclusive=True)
        with_strings = DataRange("foo_a", "foo_c")
        with self.assertRaises(TypeError) as context:
            flipped_inclusivity.parse_max("cat)")
        self.assertIn('Bad type for portion of range', str(context.exception))
        with self.assertRaises(ValueError) as context:
            with_strings.parse_max("4")
        self.assertIn('Bad inclusiveness specifier', str(context.exception))

    def test_parse_data_string(self):
        """Test the function for parsing a string to names and DataRanges."""
        just_one = "speed=[1,2)"
        basic_case = DataRange(1, 2)
        a_few = "speed=(1,2] quadrant=nw"
        flipped_inclusivity = DataRange(1, 2, min_inclusive=False, max_inclusive=True)
        both_sides_equal = DataRange("nw", "nw", max_inclusive=True)
        none = ""
        self.assertEqual(("speed", basic_case),
                         sina.utils.parse_data_string(just_one)[0])
        few_list = sina.utils.parse_data_string(a_few)
        self.assertEqual(("speed", flipped_inclusivity), few_list[0])
        self.assertEqual(("quadrant", both_sides_equal), few_list[1])
        self.assertFalse(sina.utils.parse_data_string(none))
