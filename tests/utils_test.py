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

# Path to the directory for running tests involving temporary files.  (Use this 
# file's directory as the basis for the path for now.)
RUN_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                        "tests", "run_tests"))


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
        """
        Test the function when there is no database present.
        """
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
