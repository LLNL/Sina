"""Test that example converters create valid mnoda files."""
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
        try:
            _test_file_against_schema(file=mnoda_output_file)
        except jsonschema.exceptions.ValidationError:
            self.fail('jsonschema.validate() raised ValidationError. '
                      'Invalid mnoda file.')


class TestNOAA(unittest.TestCase):
    """Test noaa example creates valid mnoda files."""

    def setUp(self):
        """
        Prepare for each test by extracting tar file and making a temporary
        output directory.
        """
        self.temp_mnoda_output = tempfile.mkdtemp()
        self.temp_tar_output = tempfile.mkdtemp()
        self.cwd = os.path.dirname(os.path.realpath(__file__))

        args = ['tar', '-xf',
                os.path.join(self.cwd,
                             '../examples/raw_data/noaa.tar.gz'),
                '-C', self.temp_tar_output]
        subprocess.check_call(args)

    def tearDown(self):
        """Clean up []"""
        shutil.rmtree(self.temp_mnoda_output)
        shutil.rmtree(self.temp_tar_output)

    def test_converter(self):
        """Verify the noaa xoncerter can create a valid mnoda file."""
        args = ['python',
                os.path.join(self.cwd,
                             '../examples/noaa/noaa_csv2mnoda.py'),
                os.path.join(self.temp_tar_output,
                             ('0123467/2.2/data/1-data/'
                              'WCOA11-01-06-2015_data.csv')),
                self.temp_mnoda_output]
        subprocess.check_call(args)
        mnoda_output_file = os.path.join(
                                self.temp_mnoda_output,
                                'files/WCOA11-01-06-2015.json')
        try:
            _test_file_against_schema(file=mnoda_output_file)
        except jsonschema.exceptions.ValidationError:
            self.fail('jsonschema.validate() raised ValidationError. '
                      'Invalid mnoda file.')


def _test_file_against_schema(file, schema=None):
    """
    Take a schema and check it against the json file.

    :param file: The json file to test with the schema.
    :param schema: The json schema to check the file against. Defaults to the
                   mnoda schema.
    :raises ValidationError: If the file is invalid, a ValidationError
                             detailing the problem of the file is raised.
    """
    if not schema:
        schema = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), '../mnoda.json')
    with open(file) as file_loaded:
        file_json = json.load(file_loaded)
        with open(schema) as schema_loaded:
            schema = json.load(schema_loaded)
            jsonschema.validate(file_json, schema)
