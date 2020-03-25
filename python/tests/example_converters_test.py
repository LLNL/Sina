"""Test that example converters create valid Sina-schema files."""
import unittest
import tempfile
import shutil
import subprocess
import os
import json
import io

# Disable pylint check due to its issue with virtual environments
import jsonschema  # pylint: disable=import-error


class TestFukushima(unittest.TestCase):
    """Test fukushima example creates valid Sina-schema files."""

    def setUp(self):
        """Prepare for each test by creating a temp output directory."""
        self.temp_sina_output = tempfile.mkdtemp()
        self.cwd = os.path.dirname(os.path.realpath(__file__))

    def tearDown(self):
        """Clean up temp output directory after each test."""
        shutil.rmtree(self.temp_sina_output)

    def test_converter(self):
        """Verify the fukushima converter can create a valid Sina-schema file."""
        args = ['python',
                os.path.join(self.cwd,
                             '../../examples/fukushima/fukushima_csv_to_sina.py'),
                os.path.join(self.cwd,
                             'test_files/test_AMS C12 Sea Data.csv'),
                self.temp_sina_output]
        subprocess.check_call(args)

        sina_output_file = os.path.join(
            self.temp_sina_output, 'files/AMS_C12_SeaData.json')
        try:
            _test_file_against_schema(file_=sina_output_file)
        except jsonschema.exceptions.ValidationError:
            self.fail('jsonschema.validate() raised ValidationError. '
                      'Invalid Sina-schema file.')


class TestNOAA(unittest.TestCase):
    """Test noaa example creates valid Sina-schema files."""

    def setUp(self):
        """Extract a tar file and make a temporary output directory as test setup."""
        self.temp_sina_output = tempfile.mkdtemp()
        self.temp_tar_output = tempfile.mkdtemp()
        self.cwd = os.path.dirname(os.path.realpath(__file__))

        args = ['tar', '-xf',
                os.path.join(self.cwd,
                             '../../examples/raw_data/noaa.tar.gz'),
                '-C', self.temp_tar_output]
        subprocess.check_call(args)

    def tearDown(self):
        """Clean up tar and Sina-schema directories."""
        shutil.rmtree(self.temp_sina_output)
        shutil.rmtree(self.temp_tar_output)

    def test_converter(self):
        """Verify the noaa converter can create a valid Sina-schema file."""
        args = ['python',
                os.path.join(self.cwd,
                             '../../examples/noaa/noaa_csv_to_sina.py'),
                os.path.join(self.temp_tar_output,
                             ('0123467/2.2/data/1-data/'
                              'WCOA11-01-06-2015_data.csv')),
                self.temp_sina_output]
        subprocess.check_call(args)
        sina_output_file = os.path.join(
            self.temp_sina_output, 'files/WCOA11-01-06-2015.json')
        try:
            _test_file_against_schema(file_=sina_output_file)
        except jsonschema.exceptions.ValidationError:
            self.fail('jsonschema.validate() raised ValidationError. '
                      'Invalid Sina file.')


def _test_file_against_schema(file_, schema=None):
    """
    Take a schema and check it against the json file.

    :param file_: The json file to test with the schema.
    :param schema: The json schema to check the file against. Defaults to the
                   Sina schema.
    :raises ValidationError: If the file is invalid, a ValidationError
                             detailing the problem of the file is raised.
    """
    if not schema:
        schema = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), '../../sina_schema.json')
    with io.open(file_, 'r', encoding='utf-8') as file_loaded:
        file_json = json.load(file_loaded)
        with io.open(schema, 'r', encoding='utf-8') as schema_loaded:
            schema = json.load(schema_loaded)
            jsonschema.validate(file_json, schema)
