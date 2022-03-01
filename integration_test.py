"""
Tests for integration between the C++ and Python portions of Sina.

Ingests/dumps jsons found in python/test_files with C++ then compares with Python
"""

import unittest
import tempfile
import os
import subprocess

import sina.utils


CPP_EXEC = "cpp/build/bin/read_write_json"
TEST_FILE_DIR = "python/tests/test_files/"


class IntegrationTests(unittest.TestCase):
    """For testing integration between C++ and Python."""

    def assert_records_equal(self, expected_records, dumped_records):
        """Test that two lists of records are equal for the purpose of the integration tests."""
        self.assertEqual(len(expected_records), len(dumped_records))
        dumped_records_dict = {x.id: x for x in dumped_records}
        for expected_record in expected_records:
            dumped_record = dumped_records_dict[expected_record.id]
            self.assertEqual(expected_record.user_defined, dumped_record.user_defined)
            self.assertEqual(expected_record.type, dumped_record.type)
            # C++ is allowed to remove empty tag lists, hence "manual" equality check
            for name in expected_record.data.keys():
                self.assertEqual(expected_record.data[name]["value"],
                                 dumped_record.data[name]["value"])
                self.assertEqual(expected_record.data[name].get("units"),
                                 dumped_record.data[name].get("units"))
                if expected_record.data[name].get("tags"):
                    self.assertEqual(expected_record.data[name].get("tags"),
                                     dumped_record.data[name].get("tags"))
            self.assertEqual(expected_record.files, dumped_record.files)
            self.assertEqual(expected_record.curve_sets, dumped_record.curve_sets)

    def assert_relationships_equal(self, expected_relationships, dumped_relationships):
        """Test two lists of relationships are equal for the purpose of the integration tests."""
        self.assertEqual(len(expected_relationships), len(dumped_relationships))

        def rel_sort(relationships):
            relationships.sort(key=lambda x: (x.subject_id, x.object_id))
        rel_sort(expected_relationships)
        rel_sort(dumped_relationships)
        for exp_rel, dump_rel in zip(expected_relationships, dumped_relationships):
            # There's no definition of equality for relationship objects
            self.assertEqual(exp_rel.subject_id, dump_rel.subject_id)
            self.assertEqual(exp_rel.object_id, dump_rel.object_id)
            self.assertEqual(exp_rel.predicate, dump_rel.predicate)

    def _get_recs_and_rels_from_json(self, json_name):
        """Extract records and relationships from C++ and Python from JSON at a path."""
        json_path = os.path.join(TEST_FILE_DIR, json_name)
        subprocess.call([CPP_EXEC, json_path, self.temp_file_name])
        expected_records, expected_relationships = \
            sina.utils.convert_json_to_records_and_relationships(json_path)
        dumped_records, dumped_relationships = \
            sina.utils.convert_json_to_records_and_relationships(self.temp_file_name)
        return ((expected_records, dumped_records), (expected_relationships, dumped_relationships))

    def assert_json_is_equal(self, json_path):
        """
        Perform the general form of the ingest/dump JSON test.

        Ingest json found at json_path using the C++, dumps to file, checks equivalence in Python.
        """
        test_records, test_relationships = self._get_recs_and_rels_from_json(json_path)
        self.assert_records_equal(*test_records)
        self.assert_relationships_equal(*test_relationships)

    def setUp(self):
        """Create the file we'll write the test JSON to."""
        handle, self.temp_file_name = tempfile.mkstemp()
        os.close(handle)

    def tearDown(self):
        """Remove the temp file we wrote to."""
        os.remove(self.temp_file_name)

    def test_full_record(self):
        """Make sure the C++ portion can return a fully-populated Record parseable by the Python."""
        self.assert_json_is_equal("full_doc.json")

    def test_minimal_doc(self):
        """Make sure the C++ portion can read/write an empty Sina document."""
        self.assert_json_is_equal("minimal_doc.json")

    def test_recs_no_relationships(self):
        """Make sure the C++ portion can read/write Sina records without relationships."""
        self.assert_json_is_equal("recs_no_rels.json")

    def test_data_recs(self):
        """Make sure the C++ portion can read/write the different data types."""
        self.assert_json_is_equal("rec_data_only.json")

    def test_local_id_recs(self):
        """Make sure local_id still works."""
        # Because of how these tests work, Python and C++ independently get a chance
        # to assign the local id. So we do need to unify them.
        recs, rels = self._get_recs_and_rels_from_json("local_id_rec.json")
        expected_recs, dumped_recs = recs  # unpack
        global_id_python = None
        global_id_cpp = None
        for rec in expected_recs:
            if rec.type == "local_id_rec":
                global_id_python = rec.id
        for rec in dumped_recs:
            if rec.type == "local_id_rec":
                global_id_cpp = rec.id
                rec.id = global_id_python
        expected_rels, dumped_rels = rels
        for rel in dumped_rels:
            if rel.subject_id == global_id_cpp:
                rel.subject_id = global_id_python
            if rel.object_id == global_id_cpp:
                rel.object_id == global_id_python
        self.assert_records_equal(expected_recs, dumped_recs)
        self.assert_relationships_equal(expected_rels, dumped_rels)
