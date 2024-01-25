import subprocess
import io
import json
import os
import sina
import unittest

# Disable pylint check due to its issue with virtual environments
import jsonschema  # pylint: disable=import-error


class TestFortranExampleIntegration(unittest.TestCase):
    
    def setUp(self):
        ''' Invoke example Fortran application to dump a sina file '''
        subprocess.run(['./example_program'])
        self.location = os.path.dirname(os.path.realpath(__file__))
        self.test_files = [os.path.join(self.location, 'sina_dump.json')]
        
    def tearDown(self):
        ''' Clean up output directory after each test. '''
        os.remove('sina_dump.json')
    
    def test_file_validity(self):
        ''' Make sure the files we're importing follow the Sina schema. '''
        schema_file = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   '../../sina_schema.json')
        with io.open(schema_file, 'r', encoding='utf-8') as schema:
            schema = json.load(schema)
            for test_file in self.test_files:
                with io.open(test_file, 'r', encoding='utf-8') as loaded_test:
                    file_json = json.load(loaded_test)
                    jsonschema.validate(file_json, schema)
    
                    
    def test_validate_contents_of_record(self):
        ''' Ensure that the  record written out matches what we expect '''
        rec = sina.utils.load_sole_record(self.test_files[0])
        
        # Test the metadata in the record
        self.assertEqual('my_rec_id', rec.id)
        self.assertEqual('my_type', rec.type)
        
        # Test the files
        self.assertEqual(list(rec.files.keys()), ['/path/to/my/file/my_other_file.txt', '/path/to/my/file/my_file.txt'])
        self.assertEqual(rec.files['/path/to/my/file/my_other_file.txt']['mimetype'], 'png')
        self.assertEqual(rec.files['/path/to/my/file/my_file.txt']['mimetype'], 'txt')
        
        # Test the signed variants 
        self.assertEqual('A', rec.data['char']['value'])
        self.assertEqual(10, rec.data['int']['value'])
        self.assertEqual(0, rec.data['logical']['value'])
        self.assertEqual(1000000000.0, rec.data['long']['value'])
        self.assertEqual(1.23456704616547, rec.data['real']['value'])
        self.assertEqual(0.810000002384186, rec.data['double']['value'])
        
        # Test the unsigned variants
        self.assertEqual('A', rec.data['u_char']['value'])
        self.assertEqual('kg', rec.data['u_char']['units'])
        self.assertEqual(10, rec.data['u_int']['value'])
        self.assertEqual('kg', rec.data['u_int']['units'])
        self.assertEqual(1.0, rec.data['u_logical']['value'])
        self.assertEqual('kg', rec.data['u_logical']['units'])
        self.assertEqual(1000000000.0, rec.data['u_long']['value'])
        self.assertEqual('kg', rec.data['u_long']['units'])
        self.assertEqual(1.23456704616547, rec.data['u_real']['value'])
        self.assertEqual('kg', rec.data['u_real']['units'])
        self.assertEqual(0.810000002384186, rec.data['u_double']['value'])
        self.assertEqual('kg', rec.data['u_double']['units'])
        self.assertEqual(0.810000002384186, rec.data['u_double_w_tag']['value'])
        self.assertEqual('kg', rec.data['u_double_w_tag']['units'])
        self.assertEqual(['new_fancy_tag'], rec.data['u_double_w_tag']['tags'])
        
        # Test the curves
        nums = range(1, 21)
        real_arr = [i for i in nums]
        double_arr = [i*2 for i in nums]
        int_arr = [i*3 for i in nums]
        long_arr = [i*4 for i in nums]
        curveset = "my_curveset"
        for kind, loc in (("indep", "independent"), ("dep", "dependent")):
            for val_type, target in (("real", real_arr), ("double", double_arr), ("int", int_arr), ("long", long_arr)):
                name = "my_{}_curve_{}".format(kind, val_type)
                self.assertEqual(target, rec.curve_sets[curveset][loc][name]["value"])
        double_2_name = "my_dep_curve_double_2"
        self.assertEqual(double_arr, rec.curve_sets[curveset]["dependent"][double_2_name]["value"])
