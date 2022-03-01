"""Test the SQL portion of the DAO structure."""

import unittest
import types

from sina.model import Record, CurveSet
import sina.proxies as proxies

# Our test classes, as with the other tests, have public methods *as* tests.
# pylint: disable=too-many-public-methods


class DataValuesTest(unittest.TestCase):
    """Test the different properties on Record.data_values."""
    def setUp(self):
        self.record = Record('my_rec', 'test_type',
                             data={
                                 'k1': {'value': 'v1', 'tags': ['t1']},
                                 'k2': {'value': 'v2', 'tags': ['t2']},
                                 'k3': {'value': 123, 'tags': ['t3']},
                             })

    def test_getattr_existing(self):
        """Verify attribute access for existing keys gets the right value."""
        self.assertEqual('v1', self.record.data_values.k1)
        self.assertEqual('v2', self.record.data_values.k2)
        self.assertEqual(123, self.record.data_values.k3)

    def test_getattr_missing(self):
        """Verify attribute access for missing keys raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        data_values = self.record.data_values
        with self.assertRaises(AttributeError) as err:
            value = data_values.no_such_key
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('no_such_key', str(err.exception))

    def test_getitem_existing(self):
        """Verify subscript access for existing keys gets the right value."""
        self.assertEqual('v1', self.record.data_values['k1'])
        self.assertEqual('v2', self.record.data_values['k2'])
        self.assertEqual(123, self.record.data_values['k3'])

    def test_getitem_missing(self):
        """Verify subscript access for missing keys raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        data_values = self.record.data_values
        with self.assertRaises(KeyError) as err:
            value = data_values['no_such_key']
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('no_such_key', str(err.exception))

    def test_setattr_existing(self):
        """Verify attribute setting for existing keys sets the right value."""
        self.record.data_values.k1 = 'new_value'
        self.assertEqual('new_value', self.record.data['k1']['value'])
        self.assertListEqual(['t1'], self.record.data['k1']['tags'])

    def test_setattr_new(self):
        """Verify attribute setting for existing keys sets the right value."""
        self.record.data_values.new_key = 'new_value'
        self.assertEqual('new_value', self.record.data['new_key']['value'])

    def test_setitem_existing(self):
        """Verify attribute setting for existing keys sets the right value."""
        self.record.data_values['k1'] = 'new_value'
        self.assertEqual('new_value', self.record.data['k1']['value'])

    def test_setitem_new(self):
        """Verify attribute setting for new keys sets the right value."""
        self.record.data_values['new_key'] = 'new_value'
        self.assertEqual('new_value', self.record.data['new_key']['value'])

    def test_delitem_existing(self):
        """Verify deleting existing keys removes values."""
        del self.record.data_values['k1']
        self.assertNotIn('k1', self.record.data)

    def test_delitem_missing(self):
        """Verify deleting missing keys raises KeyError."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        data_values = self.record.data_values
        with self.assertRaises(KeyError):
            del data_values['no_such_key']

    def test_delattr_existing(self):
        """Verify deleting existing keys removes values."""
        del self.record.data_values.k1
        self.assertNotIn('k1', self.record.data)

    def test_delattr_missing(self):
        """Verify deleting missing keys raises KeyError."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        data_values = self.record.data_values
        with self.assertRaises(AttributeError) as err:
            del data_values.no_such_key
        self.assertIn('no_such_key', str(err.exception))

    def test_in(self):
        """Test checking whether keys are in data_values"""
        self.assertIn('k1', self.record.data_values)
        self.assertIn('k2', self.record.data_values)
        self.assertIn('k3', self.record.data_values)
        self.assertNotIn('no_such_key', self.record.data_values)

    def test_iterate(self):
        """Test iterating over data_values"""
        expected_values = {
            'k1': 'v1',
            'k2': 'v2',
            'k3': 123
        }
        items = iter(self.record.data_values)
        self.assertIsInstance(items, types.GeneratorType)
        actual_values = {key: val for key, val in items}
        self.assertDictEqual(actual_values, expected_values)


# Every time we access .dependent/.independent we get errors from pylint
# saying they are not members of dictionaries, even though the objects we
# are accessing them from are not dictionaries.
# pylint: disable=no-member
class CurveSetValuesTest(unittest.TestCase):
    """Test the different properties on Record.curve_set_values."""
    def setUp(self):
        self.record = Record('my_rec', 'test_type')

        cs1 = CurveSet('cs1')
        cs1.add_independent('time', [1, 2, 3], 'ms', ['t1', 't2'])
        cs1.add_dependent('energy', [4, 5, 6])
        cs1.add_dependent('temperature', [7, 8, 9], 'K', ['t3', 't4'])
        self.record.add_curve_set(cs1)

        cs2 = CurveSet('cs2')
        cs2.add_independent('cycle', [10, 20, 30])
        cs2.add_dependent('density', [40, 50, 60])
        self.record.add_curve_set(cs2)

    def test_getattr_existing(self):
        """Verify attribute access for existing keys gets the right value."""
        self.assertListEqual(
            [1, 2, 3], self.record.curve_set_values.cs1.time)
        self.assertListEqual(
            [7, 8, 9], self.record.curve_set_values.cs1.temperature)
        self.assertListEqual(
            [10, 20, 30], self.record.curve_set_values.cs2.cycle)

    def test_getattr_existing_in_specific_set(self):
        """
        Verify attribute access for existing keys gets the right value when
        accessed via .dependent and .independent.
        """
        self.assertListEqual(
            [1, 2, 3], self.record.curve_set_values.cs1.independent.time)
        self.assertListEqual(
            [7, 8, 9], self.record.curve_set_values.cs1.dependent.temperature)
        self.assertListEqual(
            [10, 20, 30], self.record.curve_set_values.cs2.independent.cycle)

    def test_getattr_curve_set_missing(self):
        """Verify attribute access for missing curve sets raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs_values = self.record.curve_set_values
        with self.assertRaises(AttributeError) as err:
            value = cs_values.no_such_key
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('no_such_key', str(err.exception))

    def test_getattr_curve_missing(self):
        """Verify attribute access for missing curves raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs1_proxy = self.record.curve_set_values.cs1
        with self.assertRaises(AttributeError) as err:
            value = cs1_proxy.no_such_key
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('no_such_key', str(err.exception))

    def test_getattr_curve_set_missing_in_specific_set(self):
        """
        Verify attribute access for missing curve sets via .dependent
        and .independent raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs_values = self.record.curve_set_values.cs1.dependent
        with self.assertRaises(AttributeError) as err:
            value = cs_values.time
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('time', str(err.exception))

        cs_values = self.record.curve_set_values.cs1.independent
        with self.assertRaises(AttributeError) as err:
            value = cs_values.energy
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('energy', str(err.exception))

    def test_getitem_existing(self):
        """Verify subscript access for existing keys gets the right value."""
        self.assertListEqual(
            [1, 2, 3], self.record.curve_set_values['cs1']['time'])
        self.assertListEqual(
            [7, 8, 9], self.record.curve_set_values['cs1']['temperature'])
        self.assertListEqual(
            [10, 20, 30], self.record.curve_set_values['cs2']['cycle'])

    def test_getitem_existing_in_specific_set(self):
        """Verify subscript access for existing keys gets the right value."""
        self.assertListEqual(
            [1, 2, 3],
            self.record.curve_set_values['cs1'].independent['time'])
        self.assertListEqual(
            [7, 8, 9],
            self.record.curve_set_values['cs1'].dependent['temperature'])
        self.assertListEqual(
            [10, 20, 30],
            self.record.curve_set_values['cs2'].independent['cycle'])

    def test_getitem_curve_set_missing(self):
        """Verify subscript access for missing curve sets raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs_values = self.record.curve_set_values
        with self.assertRaises(KeyError) as err:
            value = cs_values['no_such_key']
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('no_such_key', str(err.exception))

    def test_getitem_curve_missing(self):
        """Verify subscript access for missing curves raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs1_proxy = self.record.curve_set_values.cs1
        with self.assertRaises(KeyError) as err:
            value = cs1_proxy['no_such_key']
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('no_such_key', str(err.exception))

    def test_getitem_curve_missing_in_specific_set(self):
        """
        Verify subscript access for missing curve sets via .dependent
        and .independent raises an exception."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs_values = self.record.curve_set_values.cs1.independent
        with self.assertRaises(KeyError) as err:
            value = cs_values['temperature']
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('temperature', str(err.exception))

        cs_values = self.record.curve_set_values.cs1.dependent
        with self.assertRaises(KeyError) as err:
            value = cs_values['time']
            self.fail('Should have failed, but got {}'.format(value))
        self.assertIn('time', str(err.exception))

    def test_setattr_on_curve_set(self):
        """Verify trying to set a curve set fails."""
        with self.assertRaises(TypeError):
            # new
            self.record.curve_set_values.new_curve_set = {}
        with self.assertRaises(TypeError):
            # existing
            self.record.curve_set_values.cs1 = {}

    def test_setattr_existing_independent(self):
        """Verify attribute setting for existing independent curves sets the
        right value without changing other attributes."""
        self.record.curve_set_values.cs1.time = [100, 200, 300]
        time = self.record.curve_sets['cs1']['independent']['time']
        self.assertListEqual([100, 200, 300], time['value'])
        self.assertListEqual(['t1', 't2'], time['tags'])
        self.assertEqual('ms', time['units'])

    def test_setattr_existing_independent_in_specific_set(self):
        """
        Verify attribute setting for existing independent curves
        directly through .independent sets the
        right value without changing other attributes.
        """
        self.record.curve_set_values.cs1.independent.time = [100, 200, 300]
        time = self.record.curve_sets['cs1']['independent']['time']
        self.assertListEqual([100, 200, 300], time['value'])
        self.assertListEqual(['t1', 't2'], time['tags'])
        self.assertEqual('ms', time['units'])

    def test_setattr_existing_dependent(self):
        """Verify attribute setting for existing dependent curves sets the
        right value without changing other attributes."""
        self.record.curve_set_values.cs1.temperature = [100, 200, 300]
        temp = self.record.curve_sets['cs1']['dependent']['temperature']
        self.assertListEqual([100, 200, 300], temp['value'])
        self.assertListEqual(['t3', 't4'], temp['tags'])
        self.assertEqual('K', temp['units'])

    def test_setattr_existing_dependent_in_specific_set(self):
        """
        Verify attribute setting for existing dependent curves
        directly through .dependent sets the
        right value without changing other attributes.
        """
        self.record.curve_set_values.cs1.dependent.temperature = [100, 200, 300]
        temp = self.record.curve_sets['cs1']['dependent']['temperature']
        self.assertListEqual([100, 200, 300], temp['value'])
        self.assertListEqual(['t3', 't4'], temp['tags'])
        self.assertEqual('K', temp['units'])

    def test_setattr_new_dependent(self):
        """Verify attribute setting for a new dependent curve creates the
        corresponding curve."""
        self.record.curve_set_values.cs1.new_curve = [100, 200, 300]
        new_curve = self.record.curve_sets['cs1']['dependent']['new_curve']
        self.assertListEqual([100, 200, 300], new_curve['value'])
        self.assertNotIn('tags', new_curve)
        self.assertNotIn('units', new_curve)

    def test_setattr_new_independent_in_specific_set(self):
        """Verify attribute setting for a new independent curve creates the
        corresponding curve."""
        self.record.curve_set_values.cs1.independent.new_curve = [100, 200, 300]
        new_curve = self.record.curve_sets['cs1']['independent']['new_curve']
        self.assertListEqual([100, 200, 300], new_curve['value'])
        self.assertNotIn('tags', new_curve)
        self.assertNotIn('units', new_curve)

    def test_setattr_new_dependent_in_specific_set(self):
        """Verify attribute setting for a new dependent curve creates the
        corresponding curve."""
        self.record.curve_set_values.cs1.dependent.new_curve = [100, 200, 300]
        new_curve = self.record.curve_sets['cs1']['dependent']['new_curve']
        self.assertListEqual([100, 200, 300], new_curve['value'])
        self.assertNotIn('tags', new_curve)
        self.assertNotIn('units', new_curve)

    def test_setitem_on_curve_set(self):
        """Verify trying to set a curve set via subscripting fails."""
        with self.assertRaises(AttributeError):
            # new
            self.record.curve_set_values['new_curve_set'] = {}
        with self.assertRaises(AttributeError):
            # existing
            self.record.curve_set_values['cs1'] = {}

    def test_setitem_existing_independent(self):
        """Verify attribute setting for existing independent curves sets the
        right value without changing other attributes."""
        self.record.curve_set_values.cs1['time'] = [100, 200, 300]
        time = self.record.curve_sets['cs1']['independent']['time']
        self.assertListEqual([100, 200, 300], time['value'])
        self.assertListEqual(['t1', 't2'], time['tags'])
        self.assertEqual('ms', time['units'])

    def test_setitem_existing_independent_on_specific_set(self):
        """Verify attribute setting for existing independent curves
        (specified via .independent) sets the right value without changing
        other attributes."""
        self.record.curve_set_values.cs1.independent['time'] = [100, 200, 300]
        time = self.record.curve_sets['cs1']['independent']['time']
        self.assertListEqual([100, 200, 300], time['value'])
        self.assertListEqual(['t1', 't2'], time['tags'])
        self.assertEqual('ms', time['units'])

    def test_setitem_existing_dependent(self):
        """Verify attribute setting for existing dependent curves sets the
        right value without changing other attributes."""
        self.record.curve_set_values.cs1['temperature'] = [100, 200, 300]
        temp = self.record.curve_sets['cs1']['dependent']['temperature']
        self.assertListEqual([100, 200, 300], temp['value'])
        self.assertListEqual(['t3', 't4'], temp['tags'])
        self.assertEqual('K', temp['units'])

    def test_setitem_existing_dependent_in_specific_set(self):
        """Verify attribute setting for existing dependent curves
        (specified via .dependent) sets the right value without changing
        other attributes."""
        self.record.curve_set_values.cs1.dependent['temperature'] = [100, 200, 300]
        temp = self.record.curve_sets['cs1']['dependent']['temperature']
        self.assertListEqual([100, 200, 300], temp['value'])
        self.assertListEqual(['t3', 't4'], temp['tags'])
        self.assertEqual('K', temp['units'])

    def test_setitem_new_dependent(self):
        """Verify attribute setting for a new dependent curve creates the
        corresponding curve."""
        self.record.curve_set_values.cs1['new_curve'] = [100, 200, 300]
        new_curve = self.record.curve_sets['cs1']['dependent']['new_curve']
        self.assertListEqual([100, 200, 300], new_curve['value'])
        self.assertNotIn('tags', new_curve)
        self.assertNotIn('units', new_curve)

    def test_setitem_new_dependent_in_specific_set(self):
        """Verify attribute setting for a new dependent curve (set via
        .dependent) creates the corresponding curve."""
        self.record.curve_set_values.cs1.dependent['new_curve'] = [100, 200, 300]
        new_curve = self.record.curve_sets['cs1']['dependent']['new_curve']
        self.assertListEqual([100, 200, 300], new_curve['value'])
        self.assertNotIn('tags', new_curve)
        self.assertNotIn('units', new_curve)

    def test_setitem_new_independent_in_specific_set(self):
        """Verify attribute setting for a new dependent curve (set via
        .independent) creates the corresponding curve."""
        self.record.curve_set_values.cs1.independent['new_curve'] = [100, 200, 300]
        new_curve = self.record.curve_sets['cs1']['independent']['new_curve']
        self.assertListEqual([100, 200, 300], new_curve['value'])
        self.assertNotIn('tags', new_curve)
        self.assertNotIn('units', new_curve)

    def test_delitem_existing_curve_set(self):
        """Verify deleting existing curve sets removes them."""
        self.assertIn('cs1', self.record.curve_sets)
        del self.record.curve_set_values['cs1']
        self.assertNotIn('cs1', self.record.curve_sets)

    def test_delitem_missing_curve_set(self):
        """Verify deleting missing curve sets raises KeyError."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        values = self.record.curve_set_values
        with self.assertRaises(KeyError):
            del values['no_such_curve_set']

    def test_delitem_existing_independent(self):
        """Verify deleting existing independent curves removes them."""
        self.assertIn('time', self.record.curve_sets['cs1']['independent'])
        del self.record.curve_set_values.cs1['time']
        self.assertNotIn('time', self.record.curve_sets['cs1']['independent'])

    def test_delitem_existing_independent_in_specific_set(self):
        """Verify deleting existing independent curves via .independent removes them."""
        self.assertIn('time', self.record.curve_sets['cs1']['independent'])
        del self.record.curve_set_values.cs1.independent['time']
        self.assertNotIn('time', self.record.curve_sets['cs1']['independent'])

    def test_delitem_existing_dependent(self):
        """Verify deleting existing dependent curves removes them."""
        self.assertIn('energy', self.record.curve_sets['cs1']['dependent'])
        del self.record.curve_set_values.cs1['energy']
        self.assertNotIn('energy', self.record.curve_sets['cs1']['dependent'])

    def test_delitem_existing_dependent_in_specific_set(self):
        """Verify deleting existing dependent curves via .dependent removes them."""
        self.assertIn('energy', self.record.curve_sets['cs1']['dependent'])
        del self.record.curve_set_values.cs1.dependent['energy']
        self.assertNotIn('energy', self.record.curve_sets['cs1']['dependent'])

    def test_delitem_missing(self):
        """Verify deleting missing curves raises KeyError."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs1 = self.record.curve_set_values.cs1
        with self.assertRaises(KeyError):
            del cs1['no_such_key']
        with self.assertRaises(KeyError):
            del cs1.independent['no_such_key']
        with self.assertRaises(KeyError):
            del cs1.dependent['no_such_key']

    def test_delattr_existing_curve_set(self):
        """Verify deleting existing curve sets removes them."""
        self.assertIn('cs1', self.record.curve_sets)
        del self.record.curve_set_values.cs1
        self.assertNotIn('cs1', self.record.curve_sets)

    def test_delattr_missing_curve_set(self):
        """Verify deleting missing curve sets raises AttributeError."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        values = self.record.curve_set_values
        with self.assertRaises(AttributeError) as err:
            del values.no_such_curve_set
        self.assertIn('no_such_curve_set', str(err.exception))

    def test_delattr_existing_independent(self):
        """Verify deleting existing independent curves removes them."""
        self.assertIn('time', self.record.curve_sets['cs1']['independent'])
        del self.record.curve_set_values.cs1.time
        self.assertNotIn('time', self.record.curve_sets['cs1']['independent'])

    def test_delattr_existing_independent_in_specific_set(self):
        """Verify deleting existing independent curves via .independent removes them."""
        self.assertIn('time', self.record.curve_sets['cs1']['independent'])
        del self.record.curve_set_values.cs1.independent.time
        self.assertNotIn('time', self.record.curve_sets['cs1']['independent'])

    def test_delattr_existing_dependent(self):
        """Verify deleting existing dependent curves removes them."""
        self.assertIn('energy', self.record.curve_sets['cs1']['dependent'])
        del self.record.curve_set_values.cs1.energy
        self.assertNotIn('energy', self.record.curve_sets['cs1']['dependent'])

    def test_delattr_existing_dependent_in_specific_set(self):
        """Verify deleting existing dependent curves via .dependent removes them."""
        self.assertIn('energy', self.record.curve_sets['cs1']['dependent'])
        del self.record.curve_set_values.cs1.dependent.energy
        self.assertNotIn('energy', self.record.curve_sets['cs1']['dependent'])

    def test_delattr_missing(self):
        """Verify deleting missing curves raises KeyError."""
        # Get a reference out here to make sure we don't get an exception
        # from an unexpected place
        cs1 = self.record.curve_set_values.cs1
        with self.assertRaises(AttributeError):
            del cs1.no_such_key
        with self.assertRaises(AttributeError):
            del cs1.independent.no_such_key
        with self.assertRaises(AttributeError):
            del cs1.dependent.no_such_key

    def test_in(self):
        """Test checking curve sets and curves are in curve_set_values"""
        self.assertIn('cs1', self.record.curve_set_values)
        self.assertIn('cs2', self.record.curve_set_values)
        self.assertNotIn('no_such_curve_set', self.record.curve_set_values)
        self.assertIn('time', self.record.curve_set_values.cs1)
        self.assertIn('energy', self.record.curve_set_values.cs1)
        self.assertNotIn('no_such_curve', self.record.curve_set_values.cs1)
        self.assertIn('time', self.record.curve_set_values.cs1.independent)
        self.assertIn('energy', self.record.curve_set_values.cs1.dependent)
        self.assertNotIn('no_such_curve', self.record.curve_set_values.cs1.independent)
        self.assertNotIn('no_such_curve', self.record.curve_set_values.cs1.dependent)

    def test_iterate_curve_sets(self):
        """Test iterating over curve sets"""
        expected_curve_sets = ['cs1', 'cs2']
        items = iter(self.record.curve_set_values)
        self.assertIsInstance(items, types.GeneratorType)
        actual_values = {key: val for key, val in items}
        self.assertEqual(len(expected_curve_sets), len(actual_values))
        for expected in expected_curve_sets:
            self.assertIn(expected, actual_values)
            self.assertIsInstance(actual_values[expected],
                                  proxies.CurveValuesProxy)

    def test_iterate_curves(self):
        """Test iterating over curves in a curve set"""
        expected_values = {
            'time': [1, 2, 3],
            'energy': [4, 5, 6],
            'temperature': [7, 8, 9],
        }
        items = iter(self.record.curve_set_values.cs1)
        self.assertIsInstance(items, types.GeneratorType)
        actual_values = {key: val for key, val in items}
        self.assertDictEqual(actual_values, expected_values)

    def test_iterate_curves_independent(self):
        """Test iterating over independent curves in a curve set"""
        expected_values = {
            'time': [1, 2, 3],
        }
        items = iter(self.record.curve_set_values.cs1.independent)
        self.assertIsInstance(items, types.GeneratorType)
        actual_values = {key: val for key, val in items}
        self.assertDictEqual(actual_values, expected_values)

    def test_iterate_curves_dependent(self):
        """Test iterating over dependent curves in a curve set"""
        expected_values = {
            'energy': [4, 5, 6],
            'temperature': [7, 8, 9],
        }
        items = iter(self.record.curve_set_values.cs1.dependent)
        self.assertIsInstance(items, types.GeneratorType)
        actual_values = {key: val for key, val in items}
        self.assertDictEqual(actual_values, expected_values)


class LibraryValuesTest(unittest.TestCase):
    """
    Test direct value access for library data.
    """
    def setUp(self):
        self.record = Record('my_id', 'test_type')
        self.record.library_data = {
            'level_1_a': {
                'data': {
                    'k1': {'value': 'v1'},
                    'k2': {'value': 'v2'},
                },
                'library_data': {
                    'level_2_a': {
                        'curve_sets': {
                            'cs1': {
                                'independent': {
                                    'time': {'value': [1, 2, 3]}
                                },
                                'dependent': {
                                    'energy': {'value': [4, 5, 6]}
                                },
                            }
                        }
                    },
                    'level_2_b': {
                        'curve_sets': {
                            'cs1': {
                                'independent': {
                                    'time': {'value': [1, 2, 3]}
                                },
                                'dependent': {
                                    'energy': {'value': [4, 5, 6]}
                                },
                            }
                        }
                    }
                }
            },
            'level_1_b': {
                'data': {
                    'k3': {'value': 'v3'},
                },
            },
            'empty_library': {}
        }

    def test_getattr_existing(self):
        """Test __getattr__ for existing libraries"""
        self.assertIsInstance(
            self.record.library_data_values.level_1_a,
            proxies.LibraryItemsProxy)
        self.assertIsInstance(
            self.record.library_data_values.level_1_a.library_data.level_2_a,
            proxies.LibraryItemsProxy)

    def test_getattr_missing(self):
        """Test __getattr__ for missing libraries"""
        values = self.record.library_data_values
        with self.assertRaises(AttributeError):
            library = values.no_such_library
            self.fail('Should have failed, but got {}'.format(library))
        level_1_a = values.level_1_a
        with self.assertRaises(AttributeError):
            library = level_1_a.no_such_library
            self.fail('Should have failed, but got {}'.format(library))

    def test_getitem_existing(self):
        """Test __getitem__ for existing libraries"""
        self.assertIsInstance(
            self.record.library_data_values['level_1_a'],
            proxies.LibraryItemsProxy)
        self.assertIsInstance(
            self.record.library_data_values['level_1_a'].library_data['level_2_a'],
            proxies.LibraryItemsProxy)

    def test_getitem_missing(self):
        """Test __getitem__ for missing libraries"""
        values = self.record.library_data_values
        with self.assertRaises(KeyError):
            library = values['no_such_library']
            self.fail('Should have failed, but got {}'.format(library))
        level_1_a = values['level_1_a']
        with self.assertRaises(KeyError):
            library = level_1_a.library_data['no_such_library']
            self.fail('Should have failed, but got {}'.format(library))

    def test_data_present(self):
        """Test accessing existing data sections"""
        self.assertIsInstance(
            self.record.library_data_values.level_1_a.data,
            proxies.ValueProxy)
        self.assertEqual(
            'v1', self.record.library_data_values.level_1_a.data.k1)

    def test_data_missing(self):
        """Test accessing missing data sections"""
        self.assertIsInstance(
            self.record.library_data_values.empty_library.data,
            proxies.ValueProxy)
        self.record.library_data_values.empty_library.data.foo = 10
        self.assertEqual(
            10, self.record.library_data_values.empty_library.data.foo)

    def test_curve_sets_present(self):
        """Test accessing existing curve set sections"""
        self.assertIsInstance(
            self.record.library_data_values.level_1_a.library_data.level_2_a.curve_sets,
            proxies.CurveSetProxy)
        self.assertListEqual(
            [1, 2, 3],
            self.record.library_data_values.level_1_a.library_data.level_2_a.curve_sets.cs1.time)

    def test_curve_sets_missing(self):
        """Test accessing missing curve set sections"""
        self.assertIsInstance(
            self.record.library_data_values.empty_library.curve_sets,
            proxies.CurveSetProxy)
        # We can't add to curve sets through the proxy, so there is nothing
        # else to test here like there was for data.

    def test_libraries_present(self):
        """Test accessing existing library sections"""
        self.assertIsInstance(
            self.record.library_data_values.level_1_a.library_data,
            proxies.LibraryValuesProxy)
        self.assertIsInstance(
            self.record.library_data_values.level_1_a.library_data.level_2_a,
            proxies.LibraryItemsProxy)

    def test_libraries_missing(self):
        """Test accessing missing library sections"""
        self.assertIsInstance(
            self.record.library_data_values.empty_library.library_data,
            proxies.LibraryValuesProxy)
        # We can't add libraries through the proxy, so there is nothing
        # else to test here like there was for data.

    def test_delitem_existing(self):
        """Test deleting existing libraries"""
        self.assertIn('level_1_a', self.record.library_data)
        del self.record.library_data_values['level_1_a']
        self.assertNotIn('level_1_a', self.record.library_data)

    def test_delitem_missing(self):
        """Test deleting missing libraries"""
        self.assertNotIn('no_such_library', self.record.library_data)
        with self.assertRaises(KeyError):
            del self.record.library_data_values['no_such_library']

    def test_in(self):
        """Test checking whether libraries exist"""
        self.assertIn('level_1_a', self.record.library_data_values)
        self.assertIn('level_2_a', self.record.library_data_values.level_1_a.library_data)
        self.assertNotIn('no_such_library', self.record.library_data_values)
        self.assertNotIn('no_such_library', self.record.library_data_values.level_1_a.library_data)

    def test_iterate(self):
        """Test iterating over libraries"""
        expected_keys = {'level_1_a', 'level_1_b', 'empty_library'}
        for key, library_proxy in self.record.library_data_values:
            self.assertIn(key, expected_keys)
            self.assertIsInstance(library_proxy, proxies.LibraryItemsProxy)
            expected_keys.remove(key)
        self.assertSetEqual(expected_keys, set())
