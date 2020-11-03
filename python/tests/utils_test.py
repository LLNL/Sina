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

import six

import sina.utils
from sina.utils import (DataRange, StringListCriteria, ScalarListCriteria,
                        sort_and_standardize_criteria)

# Path to the directory for running tests involving temporary files.  (Use this
# file's directory as the basis for the path for now.)
RUN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                        "tests", "run_tests", "sina_utils"))

# Disable pylint invalid-name due to significant number of tests with names
# exceeding the 30 character limit
# pylint: disable=invalid-name


# Disable pylint public methods to if and until the team decides to refactor the code
class TestSinaUtils(unittest.TestCase):  # pylint: disable=too-many-public-methods
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

    def test_intersect_lists_empty(self):
        """Test that the intersection of empty lists is empty."""
        self.assertEqual(sina.utils.intersect_lists([]), set())

    def test_intersect_lists_one(self):
        """Test that the intersection of one list is the set of itself."""
        test_list = ["spam", "eggs", 29]
        self.assertEqual(sina.utils.intersect_lists([test_list]), set(test_list))

    def test_intersect_lists_many(self):
        """Test that the intersection of many lists represents their shared elements."""
        first_list = ["spam", "eggs", "ham", 29, 4.14]
        second_list = [4.14, "spam", "eggs", 29, "spam"]
        third_list = [-20, 29, "spam", "eggs", "ham"]
        all_lists = [first_list, second_list, third_list]
        shared_elements = set(["spam", "eggs", 29])
        self.assertEqual(sina.utils.intersect_lists(all_lists), shared_elements)

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

    def test_resolve_curves(self):
        """Test that curves with overlapping values are handled properly."""
        curve_sets = {}
        curve_sets["spam_curve"] = {
            "dependent": {"saltiness": {"value": [1, 1, 1, 0.8]}},
            "independent": {"time": {"value": [0, 1, 2, 3],
                                     "tags": ["misc", "protein"],
                                     "units": "seconds"}}}
        curve_sets["egg_curve"] = {
            "dependent": {"time": {"value": [1, 2, 3, 4],
                                   "tags": ["timer", "protein"]}},
            "independent": {"firmness": {"value": [0, 0, 0.1, 0.3]}}}
        resolved_curves = sina.utils.resolve_curve_sets(curve_sets, {})
        # Make sure they're not equal. If they are, curve_sets was overwritten.
        self.assertNotEqual(curve_sets, resolved_curves)

        # There is only one time in the return set, spam's time and egg's time combined
        time = resolved_curves["time"]

        # Proper min, max, tags, and units
        self.assertEqual(time["value"][0], 0)
        self.assertEqual(time["value"][1], 4)
        self.assertEqual(time["units"], "seconds")
        six.assertCountEqual(self, time["tags"], ["timer", "protein", "misc"])

        # Error out on unit overwriting
        curve_sets["bad_time"] = {
            "dependent": {},
            "independent": {"time": {"value": [1, 2, 3, 4],
                                     "tags": ["timer", "output"],
                                     "units": "NOT SECONDS"}}}
        with self.assertRaises(ValueError) as context:
            sina.utils.resolve_curve_sets(curve_sets, {})
        self.assertIn('Tried to set units', str(context.exception))

    def test_resolve_curves_matching_scalar_data(self):
        """Test that curves with overlapping scalar data values are handled properly."""
        curve_sets = {
            'cs1': {
                'independent': {'time': {'value': [1, 2, 3]}},
                'dependent': {
                    'scalar_smaller': {'value': [4, 5, 6]},
                    'scalar_bigger': {'value': [7, 8, 9]},
                    'scalar_in_middle': {'value': [10, 11, 12]},
                },
            }
        }
        data = {
            'scalar_smaller': {'value': -100},
            'scalar_bigger': {'value': 100},
            'scalar_in_middle': {'value': 11.5},
        }
        resolved_curves = sina.utils.resolve_curve_sets(curve_sets, data)

        # Make sure they're not equal. If they are, curve_sets was overwritten.
        self.assertNotEqual(curve_sets, resolved_curves)

        self.assertEqual(resolved_curves['time']['value'][0], 1)
        self.assertEqual(resolved_curves['time']['value'][1], 3)

        self.assertEqual(resolved_curves['scalar_smaller']['value'][0], -100)
        self.assertEqual(resolved_curves['scalar_smaller']['value'][1], 6)

        self.assertEqual(resolved_curves['scalar_bigger']['value'][0], 7)
        self.assertEqual(resolved_curves['scalar_bigger']['value'][1], 100)

        self.assertEqual(resolved_curves['scalar_in_middle']['value'][0], 10)
        self.assertEqual(resolved_curves['scalar_in_middle']['value'][1], 12)

    def test_resolve_curves_matching_list_data(self):
        """Test that curves with overlapping list data values are handled properly."""
        curve_sets = {
            'cs1': {
                'independent': {'time': {'value': [1, 2, 3]}},
                'dependent': {
                    'scalar_smaller': {'value': [4, 5, 6]},
                    'scalar_bigger': {'value': [7, 8, 9]},
                    'scalar_in_middle': {'value': [10, 11, 12]},
                },
            }
        }
        data = {
            'scalar_smaller': {'value': [-100, 5]},
            'scalar_bigger': {'value': [100, 8]},
            'scalar_in_middle': {'value': [10.5, 11.5]},
        }
        resolved_curves = sina.utils.resolve_curve_sets(curve_sets, data)

        # Make sure they're not equal. If they are, curve_sets was overwritten.
        self.assertNotEqual(curve_sets, resolved_curves)

        self.assertEqual(resolved_curves['time']['value'][0], 1)
        self.assertEqual(resolved_curves['time']['value'][1], 3)

        self.assertEqual(resolved_curves['scalar_smaller']['value'][0], -100)
        self.assertEqual(resolved_curves['scalar_smaller']['value'][1], 6)

        self.assertEqual(resolved_curves['scalar_bigger']['value'][0], 7)
        self.assertEqual(resolved_curves['scalar_bigger']['value'][1], 100)

        self.assertEqual(resolved_curves['scalar_in_middle']['value'][0], 10)
        self.assertEqual(resolved_curves['scalar_in_middle']['value'][1], 12)

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

    def test_basic_stringlistcriteria(self):
        """Test that StringListCriteria can be initialized properly."""
        strings = ("spam", "eggs")
        has_all = sina.utils.ListQueryOperation.HAS_ALL
        with_strings = StringListCriteria(value=strings, operation=has_all)
        self.assertEqual(with_strings.value, strings)
        self.assertEqual(with_strings.operation, has_all)

    def test_basic_scalarlistcriteria(self):
        """Test that ScalarListCriteria can be initialized properly."""
        datarange = DataRange(1, 4)
        all_in = sina.utils.ListQueryOperation.ALL_IN
        with_scalars = ScalarListCriteria(value=datarange, operation=all_in)
        self.assertEqual(with_scalars.value, datarange)
        self.assertEqual(with_scalars.operation, all_in)

    def test_stringlistcriteria_assignment(self):
        """Verify StringListCriteria setters and getters are working as expected."""
        strings = ("spam", "eggs")
        new_strings = ("ham", "hashbrowns")
        criteria = StringListCriteria(value=strings,
                                      operation=sina.utils.ListQueryOperation.HAS_ALL)
        # Setters (we're using @property)
        criteria.value = new_strings
        has_any = sina.utils.ListQueryOperation.HAS_ALL
        criteria.operation = has_any
        # Getters
        self.assertEqual(criteria.value, new_strings)
        self.assertEqual(criteria.operation, has_any)

    def test_scalarlistcriteria_assignment(self):
        """Verify ScalarListCriteria setters and getters are working as expected."""
        datarange = DataRange(1, 4)
        new_range = DataRange(7, 10)
        criteria = ScalarListCriteria(value=datarange,
                                      operation=sina.utils.ListQueryOperation.ALL_IN)
        # Setters (we're using @property)
        criteria.value = new_range
        any_in = sina.utils.ListQueryOperation.ANY_IN
        criteria.operation = any_in
        # Getters
        self.assertEqual(criteria.value, new_range)
        self.assertEqual(criteria.operation, any_in)

    def test_stringlistcriteria_tostring(self):
        """Verify that StringListCriteria display as expected."""
        strings = ("foo", "bar")
        all_alt = sina.utils.ListQueryOperation.HAS_ALL
        criteria = StringListCriteria(value=strings, operation=all_alt)
        self.assertEqual(criteria.__repr__(), criteria.__str__(),
                         'StringListCriteria <value={}, operation={}>'
                         .format(strings, all_alt))

    def test_stringlistcriteria_validation_values_exist(self):
        """Test StringListCriteria enforces a non-empty value iterator."""
        valid_vals = ("spam", "eggs")
        no_vals = ()
        criteria = StringListCriteria(value=valid_vals,
                                      operation=sina.utils.ListQueryOperation.HAS_ALL)
        with self.assertRaises(TypeError) as context:
            criteria.value = no_vals
        self.assertIn('Value must be a non-empty iterable of strings',
                      str(context.exception))

    def test_scalarlistcriteria_validation_datarange(self):
        """Test ScalarListCriteria only accepts a datarange."""
        valid_val = DataRange(1, 2, max_inclusive=True)
        disallowed_iter = [1, 2]
        criteria = ScalarListCriteria(value=valid_val,
                                      operation=sina.utils.ListQueryOperation.ALL_IN)
        with self.assertRaises(TypeError) as context:
            criteria.value = disallowed_iter
        self.assertIn('Value must be a numeric DataRange',
                      str(context.exception))

    def test_stringlistcriteria_validation_value_type(self):
        """Test StringListCriteria enforces value entries being strings."""
        valid_vals = ("spam", "eggs")
        invalid_vals = (1, 2)
        criteria = StringListCriteria(value=valid_vals,
                                      operation=sina.utils.ListQueryOperation.HAS_ALL)
        with self.assertRaises(TypeError) as context:
            criteria.value = invalid_vals
        self.assertIn('Value must be a non-empty iterable of strings', str(context.exception))

    def test_scalarlistcriteria_validation_value_type(self):
        """Test ScalarListCriteria enforces range being numeric."""
        valid_vals = DataRange(1, 2)
        invalid_vals = DataRange("moo", "zar")
        criteria = ScalarListCriteria(value=valid_vals,
                                      operation=sina.utils.ListQueryOperation.ALL_IN)
        with self.assertRaises(TypeError) as context:
            criteria.value = invalid_vals
        self.assertIn("Value must be a numeric DataRange", str(context.exception))

    def test_stringlistcriteria_validation_operator(self):
        """Test StringListCriteria enforces choosing a valid ListQueryOperation."""
        criteria = StringListCriteria(value=("spam", "eggs"),
                                      operation=sina.utils.ListQueryOperation.HAS_ALL)
        with self.assertRaises(TypeError) as context:
            criteria.operation = sina.utils.ListQueryOperation.ALL_IN
        self.assertIn('is not valid for an iterable of strings',
                      str(context.exception))

    def test_scalarlistcriteria_validation_operator(self):
        """Test ScalarListCriteria enforces choosing a valid ListQueryOperation."""
        criteria = ScalarListCriteria(value=DataRange(2),
                                      operation=sina.utils.ListQueryOperation.ANY_IN)
        with self.assertRaises(TypeError) as context:
            criteria.operation = sina.utils.ListQueryOperation.HAS_ANY
        self.assertIn('is not valid for a numeric datarange', str(context.exception))

    def test_has_all(self):
        """Test that has_all is creating the expected StringListCriteria object."""
        has_all = sina.utils.has_all("spam", "egg")
        equiv = StringListCriteria(value=("spam", "egg"),
                                   operation=sina.utils.ListQueryOperation.HAS_ALL)
        self.assertEqual(has_all.value, equiv.value)
        self.assertEqual(has_all.operation, equiv.operation)

    def test_has_any(self):
        """Test that has_any is creating the expected StringListCriteria object."""
        has_any = sina.utils.has_any("spam", "egg")
        equiv = StringListCriteria(value=("spam", "egg"),
                                   operation=sina.utils.ListQueryOperation.HAS_ANY)
        self.assertEqual(has_any.value, equiv.value)
        self.assertEqual(has_any.operation, equiv.operation)

    def test_all_in(self):
        """Test that all_in is creating the expected ScalarListCriteria object."""
        all_in = sina.utils.all_in(DataRange(1, 2))
        equiv = ScalarListCriteria(value=DataRange(1, 2),
                                   operation=sina.utils.ListQueryOperation.ALL_IN)
        self.assertEqual(all_in.value, equiv.value)
        self.assertEqual(all_in.operation, equiv.operation)

    def test_any_in(self):
        """Test that any_in is creating the expected ScalarListCriteria object."""
        any_in = sina.utils.any_in(DataRange(1, 2))
        equiv = ScalarListCriteria(value=DataRange(1, 2),
                                   operation=sina.utils.ListQueryOperation.ANY_IN)
        self.assertEqual(any_in.value, equiv.value)
        self.assertEqual(any_in.operation, equiv.operation)

    def test_exists(self):
        """Test that exists is simply returning the relevant operation."""
        exists_op = sina.utils.exists()
        self.assertEqual(exists_op, sina.utils.UniversalQueryOperation.EXISTS)

    def test_sort_and_standardizing(self):
        """Test the function for processing query criteria."""
        criteria = {"numra": DataRange(1, 2),
                    "lexra": DataRange("bar", "foo"),
                    "num": 12,
                    "num2": 2,
                    "listnum": ScalarListCriteria(value=DataRange(1, 2),
                                                  operation=sina.utils.ListQueryOperation.ANY_IN),
                    "liststr": StringListCriteria(value=("foo", "bar"),
                                                  operation=sina.utils.ListQueryOperation.HAS_ANY),
                    "lex": "cat"}
        (scalar, string, scalar_list,
         string_list, _) = sort_and_standardize_criteria(criteria)
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
        self.assertEqual(string_list[0], ("liststr", criteria["liststr"]))

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
