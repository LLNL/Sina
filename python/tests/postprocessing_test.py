"""
Tests for Sina postprocessing utilities.

Mostly these are utility functions that were grouped together for the sake of
keeping utils clean and making the documentation more parseable.
"""
import unittest

import sina.model
import sina.utils
import sina.postprocessing as spp


def provide_records():  # pylint: disable=too-many-statements
    """
    Add test data to a database in a backend-independent way.

    :return: a dict of records, where the IDs are the keys
    """
    # Pylint disable note: we need to insert enough data to cover our test cases.
    long_rec = sina.model.Run(id="long_rec", application="test", user="Bob")
    long_rec.add_data("my_list", [2, 4, 6, 8, 10, 12])
    long_rec.add_data("my_other_list", ["cat", "dog", "trilobite"])
    long_rec.add_data("eggs", 12)
    long_rec.add_data("juice", "pomegranate")
    long_rec.add_file("cool/cat.png")
    long_rec.add_file("there.is")
    cs1 = sina.model.CurveSet("cs1")
    cs1.add_independent("time", [2, 4, 6])
    cs1.add_dependent("density", [4, 5, 6])
    cs2 = sina.model.CurveSet("cs2")
    cs2.add_independent("time", [2, 4, 6, 8, 10])
    cs2.add_dependent("egg_doneness", [0, 0.5, 0.75, 4, 5])
    long_rec.add_curve_set(cs1)
    long_rec.add_curve_set(cs2)
    long_rec.library_data = {"my_lib": {"data": {"mood": {"value": "joyful"},
                                                 "rates": {"value": [4, 3]}}}}

    short_rec = sina.model.Record(id="short_rec", type="test_rec")
    short_rec.add_data("eggs", 8)
    short_rec.add_data("weggs", 800)
    short_rec.add_data("my_other_list", ["leaf_sheep"])
    short_rec.add_file("cool/cat.png")
    short_rec.add_curve_set(cs2)
    short_rec.library_data = {"my_lib": {"data": {"mood": {"value": "thoughtful"}}}}

    return {record.id: record for record in [long_rec, short_rec]}


# Disable pylint public methods to if and until the team decides to refactor the code
class TestSinaPostProcessing(unittest.TestCase):  # pylint: disable=too-many-public-methods
    """Tests for Sina Utilities functions."""

    def setUp(self):
        """Create records used for testing."""
        self.recs = provide_records()

    def test_filter_keep(self):
        """Test that the allow filtering mode filters correctly."""
        run_func = spp.filter_keep(self.recs["short_rec"])
        filtered_rec = run_func(self.recs["long_rec"])
        # Make sure desired ones are kept
        self.assertTrue("eggs" in filtered_rec.data)
        # Non-desired ones aren't
        self.assertFalse("juice" in filtered_rec.data)
        # Missing ones aren't added
        self.assertFalse("weggs" in filtered_rec.data)
        # And recursion works
        self.assertTrue("mood" in filtered_rec.library_data["my_lib"]["data"])
        self.assertFalse("rates" in filtered_rec.library_data["my_lib"]["data"])

    def test_filter_remove(self):
        """Test that the denial filtering mode filters correctly."""
        run_func = spp.filter_remove(self.recs["short_rec"])
        filtered_rec = run_func(self.recs["long_rec"])
        # Make sure undesired ones are removed
        self.assertFalse("eggs" in filtered_rec.data)
        # Desired ones are kept
        self.assertTrue("juice" in filtered_rec.data)
        # Missing ones aren't added
        self.assertFalse("weggs" in filtered_rec.data)
        # And recursion works
        self.assertFalse("mood" in filtered_rec.library_data["my_lib"]["data"])

    def test_register_source(self):
        """Test that we add a source with the expected mimetype."""
        uri = "my/home/sina.json"
        run_func = spp.register_source(uri)
        sourced_rec = run_func(self.recs["short_rec"])
        self.assertTrue(uri in sourced_rec.files)
        self.assertEqual(sourced_rec.files[uri]["mimetype"], spp.SINA_MIMETYPE)

    def test_underlay(self):
        """Test that we can underlay a record."""
        underlay_func = spp.underlay(self.recs["long_rec"])
        underlayed_rec = underlay_func(self.recs["short_rec"])
        # We expect the underlayed record's shared values to be present
        self.assertEqual(underlayed_rec.data_values["eggs"], 8)
        # and ones not shared to be present
        self.assertEqual(underlayed_rec.data_values["juice"], "pomegranate")
        # and for this behavior to be recursive
        self.assertEqual(underlayed_rec.curve_sets["cs1"]["independent"]["time"]["value"],
                         [2, 4, 6])

    def test_overlay(self):
        """Test that we can overlay a record."""
        overlay_func = spp.overlay(self.recs["short_rec"])
        overlayed_rec = overlay_func(self.recs["long_rec"])
        # We expect the overlayed record's shared values to be absent
        self.assertEqual(overlayed_rec.data_values["eggs"], 8)
        # ones not shared to be present
        self.assertEqual(overlayed_rec.data_values["juice"], "pomegranate")
        # and for this behavior to be recursive
        self.assertEqual(overlayed_rec.curve_sets["cs1"]["independent"]["time"]["value"],
                         [2, 4, 6])
        # Also we should make sure this isn't the exact same function as above
        # We've already altered our long_rec, so we need to gen a new one.
        overlay_func = spp.overlay(provide_records()["long_rec"])
        overlayed_rec = overlay_func(self.recs["short_rec"])
        self.assertEqual(overlayed_rec.data_values["eggs"], 12)

    # _force_list_to_len() is protected as it's a helper method, but due to its
    # complexity, it benefits from dedicated testing.
    # pylint: disable=protected-access
    def test_force_length(self):
        """Test (roughly) our ability to "resample" arbitrary scalar lists."""
        # We test the helper method here and the user-facer for broader capability.
        sample_list_ascend = [2, 4, 6, 8]
        sample_list_descend = [2, 0, -2, -4]
        lengths_tested = [1, 3, 4, 7, 8, 16, 22, 200]
        for (target, comp_func) in ((sample_list_ascend, lambda x, y: x < y),
                                    (sample_list_descend, lambda x, y: x > y)):
            for length in lengths_tested:
                relengthened = spp._force_list_to_len(target, length)
                self.assertEqual(len(relengthened), length)
                if length != 1:
                    self.assertEqual(relengthened[0], target[0])
                self.assertEqual(relengthened[-1], target[-1])
                for idx in range(len(relengthened)-1):
                    self.assertTrue(comp_func(relengthened[idx], relengthened[idx+1]))

    def test_resample_scalar_lists(self):
        """Test the resampling as applied to whole records."""
        resample_func = spp.resample_scalar_lists(10)
        # We've already tested the functionality, we just need to make sure everything
        # ends up the same length.
        resampled_rec = resample_func(self.recs["long_rec"])
        self.assertEqual(len(resampled_rec.data_values["my_list"]), 10)
        self.assertEqual(len(resampled_rec.curve_sets["cs1"]["independent"]["time"]["value"]), 10)
        self.assertEqual(len(resampled_rec.curve_sets["cs1"]["dependent"]["density"]["value"]), 10)
        self.assertEqual(len(resampled_rec.curve_sets["cs2"]["independent"]["time"]["value"]), 10)
        self.assertEqual(
            len(resampled_rec.curve_sets["cs2"]["dependent"]["egg_doneness"]["value"]), 10)

    def test_resample_scalar_lists_with_length(self):
        """Test the resampling as applied to lists with specified lengths."""
        resample_func = spp.resample_scalar_lists(
            10, sina.utils.DataRange(min=5, min_inclusive=True))
        resampled_rec = resample_func(self.recs["long_rec"])
        self.assertEqual(len(resampled_rec.data_values["my_list"]), 10)
        self.assertEqual(len(resampled_rec.curve_sets["cs1"]["independent"]["time"]["value"]), 3)
        self.assertEqual(len(resampled_rec.curve_sets["cs1"]["dependent"]["density"]["value"]), 3)
        self.assertEqual(len(resampled_rec.curve_sets["cs2"]["independent"]["time"]["value"]), 10)
        self.assertEqual(
            len(resampled_rec.curve_sets["cs2"]["dependent"]["egg_doneness"]["value"]), 10)
