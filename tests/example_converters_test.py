"""Test that example converters reate valid mnoda files."""
import unittest
import tempfile
import shutil
import subprocess
import os
import json
import jsonschema


class TestFukushima(unittest.TestCase):
    """Test fukushima example creates valid mnoda files."""

    def setUp(self):
        """Prepare for each test by creating a temp output directory."""
        self.temp_mnoda_output = tempfile.mkdtemp()
        self.cwd = os.path.dirname(os.path.realpath(__file__))

    def tearDown(self):
        """Clean up temp output directory after each test."""
        shutil.rmtree(self.temp_mnoda_output)

    def test_converter(self):
        """Verify the fukushima converter can create a valid mnoda file."""

        args = ['python',
                os.path.join(self.cwd,
                             '../examples/fukushima/fukushima_csv2mnoda.py'),
                os.path.join(self.cwd,
                             'test_files/test_AMS C12 Sea Data.csv'),
                self.temp_mnoda_output]
        subprocess.check_call(args)

        mnoda_output_file = os.path.join(
                                self.temp_mnoda_output,
                                'files/AMS_C12_SeaData.json')
        with open(mnoda_output_file) as mnoda_file:
            mnoda_output = json.load(mnoda_file)
            mnoda_schema_file = os.path.join(self.cwd, '../mnoda.json')
            with open(mnoda_schema_file) as mnoda_schema:
                schema = json.load(mnoda_schema)
                try:
                    jsonschema.validate(mnoda_output, schema)
                except jsonschema.exceptions.ValidationError:
                    self.fail('jsonschema.validate() raised ValidationError. '
                              'Invalid mnoda file.')
