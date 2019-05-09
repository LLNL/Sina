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
from types import GeneratorType

import sina.utils
from sina.utils import DataRange, ListCriteria, sort_and_standardize_criteria

# Path to the directory for running tests involving temporary files.  (Use this
# file's directory as the basis for the path for now.)
RUN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                        "tests", "run_tests", "sina_utils"))

# Disable pylint invalid-name due to significant number of tests with names
# exceeding the 30 character limit
# pylint: disable=C0103


class TestSinaUtils(unittest.TestCase):  # pylint: disable=R0904
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

    def test_intersect_ordered_empty(self):
        """Test that the intersection of empty iterators is empty."""
        gen_none = (i for i in [])
        gen_also_none = (i for i in [])
        self.assertFalse(list(sina.utils.intersect_ordered([gen_none,
                                                            gen_also_none])))

    def test_intersect_ordered_one(self):
        """Test that the intersection of a single iterator is the contents of that iterator."""
        alone_list = [1, 2, 3, 4]
        gen_alone = (i for i in alone_list)
        self.assertEqual(list(sina.utils.intersect_ordered([gen_alone])),
                         alone_list)

    def test_intersect_ordered_empty_nonempty(self):
        """Test that the intersection of an empty and non-empty iterator is empty."""
        gen_none = (i for i in [])
        gen_some = (i for i in [1, 2, 3])
        self.assertFalse(list(sina.utils.intersect_ordered([gen_none,
                                                            gen_some])))

    def test_intersect_ordered_nonempty_empty(self):
        """
        Test that the intersection of a non-empty and empty iterator is empty.

        Essentially, test that order doesn't matter.
        """
        gen_none = (i for i in [])
        gen_some = (i for i in [1, 2, 3])
        self.assertFalse(list(sina.utils.intersect_ordered([gen_some,
                                                            gen_none])))

    def test_intersect_ordered_many(self):
        """Test that non-empty iterators return the intersection of their contents."""
        gen_even = (i for i in range(0, 10, 2))
        gen_rando = (i for i in [-1, 0, 1, 2, 5, 6, 8])
        gen_10 = (i for i in range(10))
        intersect = sina.utils.intersect_ordered([gen_even,
                                                  gen_rando,
                                                  gen_10])
        # Order is important
        self.assertEqual(list(intersect), [0, 2, 6, 8])

        gen_colors = (i for i in ["blue", "orange", "white"])
        gen_fruits = (i for i in ["apple", "banana", "orange"])
        intersect_str = sina.utils.intersect_ordered([gen_colors,
                                                      gen_fruits])
        self.assertEqual(list(intersect_str), ["orange"])

    def test_intersect_ordered_lists(self):
        """Test that intersect_ordered works with lists as well as generators."""
        list_even = range(0, 10, 2)
        list_rando = [-1, 0, 1, 2, 5, 6, 8]
        list_10 = range(10)
        intersect = sina.utils.intersect_ordered([list_even,
                                                  list_rando,
                                                  list_10])
        # Order is important
        self.assertEqual(list(intersect), [0, 2, 6, 8])

        gen_colors = (i for i in ["blue", "orange", "white"])
        list_fruits = ["apple", "banana", "orange"]
        intersect_str = sina.utils.intersect_ordered([gen_colors,
                                                      list_fruits])
        self.assertEqual(list(intersect_str), ["orange"])

    def test_intersect_ordered_return_type(self):
        """Test that, no matter the type of iterator given, what's returned is a generator."""
        list_many = [1, 2, 3, 4]
        list_many_more = [3, 4, 5, 6]
        gen_many = (i for i in list_many)
        gen_many_more = (i for i in list_many_more)
        list_and_list = sina.utils.intersect_ordered([list_many, list_many_more])
        self.assertTrue(isinstance(list_and_list, GeneratorType))
        gen_and_gen = sina.utils.intersect_ordered([gen_many, gen_many_more])
        self.assertTrue(isinstance(gen_and_gen, GeneratorType))
        iterator_mix = sina.utils.intersect_ordered([gen_many, list_many_more,
                                                     list_many, gen_many_more])
        self.assertTrue(isinstance(iterator_mix, GeneratorType))
        no_iterator = sina.utils.intersect_ordered([])
        self.assertTrue(isinstance(no_iterator, GeneratorType))

    def test_merge_overlapping_ranges(self):
        """Test that we merge overlapping DataRanges."""
        ranges = [DataRange(max=0),
                  DataRange(min=0, max=5),
                  DataRange(min=3, max=4)]
        merged_range = DataRange(max=5)
        self.assertEqual(sina.utils.merge_ranges(ranges), [merged_range])

    def test_merge_non_overlapping_ranges(self):
        """Test that we don't merge non-overlapping DataRanges."""
        ranges = [DataRange(min=3, max=4),
                  DataRange(min=5, max=6)]
        self.assertEqual(sina.utils.merge_ranges(ranges), ranges)

    def test_merge_disordered_ranges(self):
        """Test that we correctly order our ranges and their mergings."""
        ranges = [DataRange(min=5.5),
                  DataRange(min=3, max=4, min_inclusive=False),
                  DataRange(min=5, max=6)]
        merged_ranges = [DataRange(min=3, max=4, min_inclusive=False),
                         DataRange(min=5)]
        self.assertEqual(sina.utils.merge_ranges(ranges), merged_ranges)

    def test_merge_string_ranges(self):
        """Test that we merge string ranges correctly."""
        ranges = [DataRange(min="cat", max="giraffe", min_inclusive=False),
                  DataRange(min="dog", max="zebra")]
        merged_ranges = [DataRange(min="cat", max="zebra", min_inclusive=False)]
        self.assertEqual(sina.utils.merge_ranges(ranges), merged_ranges)

    def test_invert_ranges_one_range(self):
        """Test that we correctly invert a single DataRange."""
        data_range = DataRange(min=2, max=4)
        opposite_ranges = [DataRange(max=2, max_inclusive=False),
                           DataRange(min=4, min_inclusive=True)]
        self.assertEqual(sina.utils.invert_ranges([data_range]), opposite_ranges)

    def test_invert_ranges_one_range_zeroes(self):
        """
        Test that we correctly invert a single DataRange.

        Checks for correct behavior on range bounds that are "Falsey" (ex: zero).
        """
        data_range = DataRange(min=0, max=0, max_inclusive=True)
        opposite_ranges = [DataRange(max=0),
                           DataRange(min=0, min_inclusive=False)]
        self.assertEqual(sina.utils.invert_ranges([data_range]), opposite_ranges)

    def test_invert_ranges_many_ranges(self):
        """Test that we correctly invert multiple DataRanges."""
        ranges = [DataRange(max=2, max_inclusive=False),
                  DataRange(min=4, min_inclusive=True)]
        opposite_range = DataRange(min=2, max=4)
        self.assertEqual(sina.utils.invert_ranges(ranges), [opposite_range])

    def test_invert_ranges_strings(self):
        """Test that range inversion works with strings."""
        ranges = [DataRange(max="cat", max_inclusive=True),
                  DataRange(min="dog", min_inclusive=False)]
        opposite_range = DataRange(min="cat", max="dog",
                                   min_inclusive=False, max_inclusive=True)
        self.assertEqual(sina.utils.invert_ranges(ranges), [opposite_range])

    def test_invert_ranges_multitype_error(self):
        """Test that a TypeError is raised if mixed types of ranges are inverted."""
        ranges = [DataRange(max="cat", max_inclusive=True),
                  DataRange(min=2, min_inclusive=False)]
        with self.assertRaises(TypeError) as context:
            sina.utils.invert_ranges(ranges)
        self.assertIn('must be only numeric DataRanges or', str(context.exception))

    def test_invert_ranges_none_error(self):
        """Test that a ValueError is raised if no ranges are inverted."""
        ranges = []
        with self.assertRaises(ValueError) as context:
            sina.utils.invert_ranges(ranges)
        self.assertIn('must contain at least one DataRange', str(context.exception))

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
        with self.assertRaises(ValueError) as context:
            DataRange()
        self.assertIn('Null DataRange', str(context.exception))

    def test_data_range_equality(self):
        """Test the DataRange equality operator."""
        basic_case = DataRange(1, 2)
        flipped_inclusivity = DataRange(1, 2e0, min_inclusive=False, max_inclusive=True)
        with_strings = DataRange("foo_a", "foo_c")
        basic_case_again = DataRange(1, 2)
        self.assertEqual(basic_case, basic_case_again)
        self.assertNotEqual(basic_case, flipped_inclusivity)
        self.assertNotEqual(basic_case, with_strings)

    def test_data_range_contains(self):
        """Test the DataRange contains operator."""
        flipped_inclusivity = DataRange(1, 2, min_inclusive=False, max_inclusive=True)
        inf_max = DataRange(max=100)
        with_strings = DataRange(min="foo_a", min_inclusive=False)
        self.assertTrue(2 in flipped_inclusivity)
        self.assertFalse(1 in flipped_inclusivity)
        self.assertTrue(-999 in inf_max)
        self.assertFalse(100 in inf_max)
        self.assertTrue("foo_c" in with_strings)
        self.assertFalse("foo_a" in with_strings)

    def test_data_range_overlaps(self):
        """Test that we detect when DataRanges overlap."""
        lesser = DataRange(1, None)
        greater = DataRange(-4, 5)
        self.assertTrue(lesser.overlaps(greater))
        self.assertTrue(greater.overlaps(lesser))

    def test_data_range_no_overlap(self):
        """Test that we detect when DataRanges don't overlap."""
        lesser = DataRange(1, 2)
        greater = DataRange(3, 5)
        self.assertFalse(lesser.overlaps(greater))
        self.assertFalse(greater.overlaps(lesser))

    def test_data_range_overlap_strings(self):
        """Test that we detect overlapping string DataRanges."""
        lesser = DataRange("cat", "horse")
        greater = DataRange("dog", "fish")
        self.assertTrue(greater.overlaps(lesser))

    def test_data_range_overlap_bad_types(self):
        """Test that we refuse to check type-mismatched DataRanges for overlap."""
        strings = DataRange("cat", "horse")
        scalars = DataRange(42, 45)
        with self.assertRaises(TypeError) as context:
            self.assertFalse(strings.overlaps(scalars))
        self.assertIn('Only DataRanges of the same type (numeric or lexicographic)',
                      str(context.exception))

    def test_data_range_min_is_finite(self):
        """Test that we correctly detect a DataRanges with closed min bounds."""
        open_min = DataRange(max=12)
        bounded_min = DataRange(min=12)
        self.assertFalse(open_min.min_is_finite())
        self.assertTrue(bounded_min.min_is_finite())

    def test_data_range_max_is_finite(self):
        """Test that we correctly detect a DataRanges with closed max bounds."""
        open_max = DataRange(min=12)
        bounded_max = DataRange(max=12)
        self.assertFalse(open_max.max_is_finite())
        self.assertTrue(bounded_max.max_is_finite())

    def test_data_range_is_single(self):
        """Test the DataRange is_single_value method."""
        is_single = DataRange(2, 2, max_inclusive=True)
        is_also_single = DataRange("cat", "cat", max_inclusive=True)
        is_not_single = DataRange(2, 10, max_inclusive=True)
        self.assertTrue(is_single.is_single_value())
        self.assertTrue(is_also_single.is_single_value())
        self.assertFalse(is_not_single.is_single_value())

    def test_data_range_identity(self):
        """Test functions that return what kind of range the DataRange is."""
        numerical = DataRange(min=1)
        lexographic = DataRange(max="foo_c")
        self.assertTrue(numerical.is_numeric_range())
        self.assertFalse(numerical.is_lexographic_range())
        self.assertTrue(lexographic.is_lexographic_range())
        self.assertFalse(lexographic.is_numeric_range())

    def test_data_range_string_setters_with_scalars(self):
        """Test the functions that use strings to set up DataRanges with scalar vals."""
        flipped_inclusivity = DataRange(1, 2e100, min_inclusive=False, max_inclusive=True)
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

    def test_basic_listcriteria(self):
        """Test that ListCriteria can be initialized properly."""
        strings = ("spam", "eggs")
        scalars = (1, 2, 3)
        all_alt = sina.utils.ListQueryOperation.ALL
        with_strings = ListCriteria(entries=strings, operation="ALL")
        with_scalars = ListCriteria(entries=scalars, operation=all_alt)
        self.assertEqual(with_strings.entries, strings)
        self.assertEqual(with_scalars.entries, scalars)
        self.assertEqual(with_strings.operation, with_scalars.operation,
                         sina.utils.ListQueryOperation.ALL)

    def test_listcriteria_assignment(self):
        """Verify ListCriteria setters and getters are working as expected."""
        strings = ("spam", "eggs")
        scalars = (1, 2, 3)
        criteria = ListCriteria(entries=strings, operation="ALL")
        # Setters (we're using @property)
        criteria.entries = scalars
        criteria.operation = "ANY"
        # Getters
        self.assertEqual(criteria.entries, scalars)
        self.assertEqual(criteria.operation, sina.utils.ListQueryOperation.ANY)

    def test_listcriteria_tostring(self):
        """Verify that ListCriteria display as expected."""
        scalars = (1, 2, 3)
        all_alt = sina.utils.ListQueryOperation.ALL
        criteria = ListCriteria(entries=scalars, operation=all_alt)
        self.assertEqual(criteria.__repr__(), criteria.__str__(),
                         'ListCriteria <entries={}, operation={}>'
                         .format(scalars, all_alt))

    def test_listcriteria_type(self):
        """Verify that ListCriteria have is_lexographic and is_numeric set."""
        strings = ("spam", "eggs")
        scalars = (1, 2, 3)
        criteria = ListCriteria(entries=strings, operation="ONLY")
        self.assertTrue(criteria.is_lexographic)
        self.assertFalse(criteria.is_numeric)
        # Switching entry type should set fields appropriately.
        criteria.entries = scalars
        self.assertFalse(criteria.is_lexographic)
        self.assertTrue(criteria.is_numeric)
        criteria.entries = strings
        self.assertTrue(criteria.is_lexographic)
        self.assertFalse(criteria.is_numeric)

    def test_listcriteria_validation_tuples(self):
        """Test ListCriteria only accepts tuples."""
        valid_vals = ("spam", "eggs")
        disallowed_iter = [1, 2, 3]
        criteria = ListCriteria(entries=valid_vals, operation="ALL")

        with self.assertRaises(TypeError) as context:
            criteria.entries = disallowed_iter
        self.assertIn('Entries must be expressed as a tuple',
                      str(context.exception))

    def test_listcriteria_validation_entries_type(self):
        """Test ListCriteria enforces entries being numeric xor lexographic."""
        valid_vals = ("spam", "eggs")
        invalid_vals = ("spam", 12)
        criteria = ListCriteria(entries=valid_vals, operation="ALL")
        with self.assertRaises(TypeError) as context:
            criteria.entries = invalid_vals
        self.assertIn("Entries must be only strings/lexographic DataRanges "
                      "or only scalars/numeric DataRanges.", str(context.exception))

    def test_listcriteria_validation_entries_exist(self):
        """Test ListCriteria enforces entries a non-empty entries list."""
        valid_vals = ("spam", "eggs")
        no_vals = ()
        criteria = ListCriteria(entries=valid_vals, operation="ALL")
        with self.assertRaises(TypeError) as context:
            criteria.entries = no_vals
        self.assertIn("Entries must be a tuple of strings/lexographic DataRanges, "
                      "or of scalars/numeric DataRanges, not empty",
                      str(context.exception))

    def test_listcriteria_validation_operator(self):
        """Test ListCriteria enforces choosing an existing ListQueryOperation."""
        criteria = ListCriteria(entries=("spam", "eggs"), operation="ALL")
        with self.assertRaises(ValueError) as context:
            criteria.operation = "FORBIDDEN_OPERATOR"
        self.assertIn('is not a valid ListQueryOperation', str(context.exception))

    def test_list_criteria_numeric_protection(self):
        """Test that ListCriteria's is_numeric cannot be set by hand."""
        criteria = ListCriteria(entries=("spam", "eggs"), operation="ALL")
        with self.assertRaises(AttributeError) as context:
            criteria.is_numeric = True
        self.assertIn("can't set attribute", str(context.exception))

    def test_list_criteria_lexographic_protection(self):
        """Test that ListCriteria's is_lexographic cannot be set by hand."""
        criteria = ListCriteria(entries=("spam", "eggs"), operation="ALL")
        with self.assertRaises(AttributeError) as context:
            criteria.is_lexographic = True
        self.assertIn("can't set attribute", str(context.exception))

    def test_has_all(self):
        """Test that has_all is creating the expected ListCriteria object."""
        has_all = sina.utils.has_all("spam", "egg")
        equiv = ListCriteria(entries=("spam", "egg"), operation="ALL")
        self.assertEqual(has_all.entries, equiv.entries)
        self.assertEqual(has_all.operation, equiv.operation)

    def test_has_any(self):
        """Test that has_any is creating the expected ListCriteria object."""
        has_any = sina.utils.has_any("spam", "egg")
        equiv = ListCriteria(entries=("spam", "egg"), operation="ANY")
        self.assertEqual(has_any.entries, equiv.entries)
        self.assertEqual(has_any.operation, equiv.operation)

    def test_has_only(self):
        """Test that has_only is creating the expected ListCriteria object."""
        has_only = sina.utils.has_only("spam", "egg")
        equiv = ListCriteria(entries=("spam", "egg"), operation="ONLY")
        self.assertEqual(has_only.entries, equiv.entries)
        self.assertEqual(has_only.operation, equiv.operation)

    def test_sort_and_standardizing(self):
        """Test the function for processing query criteria."""
        criteria = {"numra": DataRange(1, 2),
                    "lexra": DataRange("bar", "foo"),
                    "num": 12,
                    "num2": 2,
                    "listnum": ListCriteria(entries=(1, 2), operation="ALL"),
                    "lex": "cat"}
        scalar, string, scalar_list, string_list = sort_and_standardize_criteria(criteria)
        num_equiv = DataRange(12, 12, max_inclusive=True)
        num2_equiv = DataRange(2, 2, max_inclusive=True)
        lex_equiv = DataRange("cat", "cat", max_inclusive=True)
        # assertCountEqual WOULD make sense, except it seems to test on object
        # identity and not using the == operator. Instead, we sort
        scalar.sort()
        string.sort()
        self.assertEqual(scalar, [("num", num_equiv),
                                  ("num2", num2_equiv),
                                  ("numra", criteria["numra"])])
        self.assertEqual(string, [("lex", lex_equiv),
                                  ("lexra", criteria["lexra"])])
        self.assertEqual(scalar_list[0], ("listnum", criteria["listnum"]))
        self.assertFalse(string_list)

        with self.assertRaises(ValueError) as context:
            sina.utils.sort_and_standardize_criteria({"bork": ["meow"]})
        self.assertIn('criteria must be a number, string', str(context.exception))

    def test_parse_data_string(self):
        """Test the function for parsing a string to names and DataRanges."""
        just_one = "speed=[1,2)"
        basic_case = DataRange(1, 2)
        a_few = "speed=(1,2] quadrant=nw"
        flipped_inclusivity = DataRange(1, 2, min_inclusive=False, max_inclusive=True)
        both_sides_equal = DataRange("nw", "nw", max_inclusive=True)
        none = ""
        self.assertEqual(basic_case, sina.utils.parse_data_string(just_one)["speed"])
        few_dict = sina.utils.parse_data_string(a_few)
        self.assertEqual(flipped_inclusivity, few_dict["speed"])
        self.assertEqual(both_sides_equal, few_dict["quadrant"])
        self.assertFalse(sina.utils.parse_data_string(none))
