"""
Contains classes for creating proxy objects to simplify access for common
use cases in complex data structures.
"""

import six


class ValueProxy(object):
    """
    Provides a proxy view into the "value" field of standard Sina dictionaries.
    This proxy view allows fields to be accessed via attribute access as well
    as via subscripting.

    End users should not create this class directly. Instead, they should
    access it via properties on Records.

    Example usage::

        record = Record(...)
        # Sets record.data['my_field']['value'] to 10, regardless of whether
        # 'my_field' currently exists.
        record.data_values.my_field = 10

        # Gets record.data['my_field']['value'], raising a KeyError if it
        # doesn't exist.
        my_field_value = record.data_values.my_field

        # You can also use subscript operators:
        record.data_values['my_field'] = 10
        my_field_value = record.data_values['my_field']

        # You can check whether an item exists
        my_field_is_present = 'my_field' in record.data_values

        # You can iterate over the values. Note that the values are the
        # "value" fields in the record.data items.
        for key, value in record.data_values:
            print(key, value)
    """
    def __init__(self, proxied_dict):
        """
        Create a new ValueProxy which proxies the entries in the given
        dictionary.

        :param proxied_dict: the dictionary to proxy. Existing entries' values
         must be dictionaries conform to the Sina convention of having a
         "value" field.
        """
        # Don't want to trigger the local __setattr__, so call the one
        # in the parent class
        super(ValueProxy, self).__setattr__(
            '_ValueProxy__proxied_dict', proxied_dict)

    def __getattr__(self, item):
        """
        Get the given item.

        :param item: the name of the attribute
        :return: the value of the attribute
        :raises AttributeError: if the attribute does not exist.
        """
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        """
        Set the given attribute. If it already exists, tags and units will
        be left alone. Otherwise, they will not be set.

        :param key: the name of the new item
        :param value: the value of the new item
        """
        self[key] = value

    def __getitem__(self, item):
        """
        Get the given item.

        :param item: the name of the attribute
        :return: the value of the attribute
        :raises KeyError: if the attribute does not exist.
        """
        return self.__proxied_dict[item]['value']

    def __setitem__(self, key, value):
        """
        Set the given attribute. If it already exists, tags and units will
        be left alone. Otherwise, they will not be set.

        :param key: the name of the new item
        :param value: the value of the new item
        """
        if key in self.__proxied_dict:
            self.__proxied_dict[key]['value'] = value
        else:
            self.__proxied_dict[key] = {
                'value': value,
            }

    def __delitem__(self, key):
        """
        Delete the given item.

        :param key: the name of the item
        :raises KeyError: if the item does not exist
        """
        del self.__proxied_dict[key]

    def __delattr__(self, key):
        """
        Delete the given item.

        :param key: the name of the item
        :raises AttributeError: if the item does not exist
        """
        try:
            del self.__proxied_dict[key]
        except KeyError:
            raise AttributeError(key)

    def __contains__(self, item):
        """
        Check whether the given item is in the proxied dictionary.

        :param item: the item to check
        :return: whether the item exists
        """
        return item in self.__proxied_dict

    def __iter__(self):
        """
        Iterate over the key, value pairs.

        :return: a generator that iterates over the keys and "value" fields
         of the proxied dictionary
        """
        for key, val in six.iteritems(self.__proxied_dict):
            yield key, val['value']


class CurveSetProxy(object):
    """
    Provides a proxy to access the curve sets (and eventually curve values)
    in a record via attribute and subscript access.

    Example usage::

        record = get_record_from_somewhere()

        # Get the values of curve "time" in curve set "cs1" via an attribute
        time_values = record.curve_set_values.cs1.time

        # Get the values of curve "time" in curve set "cs1" via subscripting
        time_values = record.curve_set_values['cs1']['time']

        # You can be explicit about whether the curve a dependent curve or
        # an independent one.
        time_values = record.curve_set_values.cs1.independent.time
        energy_values = record.curve_set_values.cs1.dependent.energy

        # Setting values is possible, too.
        record.curve_set_values.cs1.independent.time = [1, 2, 3]
        record.curve_set_values.cs1.dependent.energy = [1, 2, 3]

        # You can check whether a curve set or a curve exists.
        my_curve_set_is_present = 'my_curve_set' in record.curve_set_values
        my_curve_is_present_in_cs1 = 'my_curve' in record.curve_set_values.cs1

        # You can iterate over curve sets and values. Note that the values
        # are the "value" fields in the record.curve_set items.
        for curve_set in record.curve_set_values:
            for curve, values in record.curve_set_values[curve_set]:
                print('Curve set {} contains curve {} with values {}'.format(
                    curve_set, curve, values))
    """
    def __init__(self, proxied_dict):
        """
        Create a new CurveSetProxy which proxies the given dictionary.

        :param proxied_dict: the dictionary to proxy. Existing entries' values
         must be dictionaries conform to the Sina convention of having a
         "value" field.
        """
        # Don't want to trigger the local __setattr__, so call the one
        # in the parent class
        super(CurveSetProxy, self).__setattr__(
            '_CurveSetProxy__proxied_dict', proxied_dict)

    def __getattr__(self, item):
        """
        Get the given item.

        :param item: the name of the attribute
        :return: the curve set named by the attribute
        :raises KeyError: if the curve set does not exist.
        """
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def __setattr__(self, key, value):
        """
        Always fails. Adding curve sets this way is not allowed.

        :param key: the name of the new item
        :param value: the value of the new item
        :raise TypeError: always
        """
        raise TypeError('Cannot add curve sets this way. Instead, use Record.add_curve_set()')

    def __getitem__(self, item):
        """
        Get the given item.

        :param item: the name of the item
        :return: the curve set named by the item
        :raises KeyError: if the curve set does not exist.
        """
        # import here to avoid circular dependency
        # pylint: disable=cyclic-import
        from sina.model import CurveSet
        return CurveValuesProxy(CurveSet(item, raw=self.__proxied_dict[item]))

    def __delitem__(self, key):
        """
        Delete the specified curve set

        :param key: the name of the curve set
        :raises KeyError: if the curve set does not exist
        """
        del self.__proxied_dict[key]

    def __delattr__(self, key):
        """
        Delete the specified curve set

        :param key: the name of the curve set
        :raises AttributeError: if the curve set does not exist
        """
        try:
            del self.__proxied_dict[key]
        except KeyError:
            raise AttributeError(key)

    def __contains__(self, item):
        """
        Check whether the given item is a curve set.

        :param item: the item to check
        :return: whether the item exists
        """
        return item in self.__proxied_dict

    def __iter__(self):
        """
        Iterate over the curve sets

        :return: a generator that iterates over the curve set names and
         associated CurveValueProxy objects
        """
        for key in self.__proxied_dict:
            yield key, self[key]


class CurveValuesProxy(object):
    """
    A proxy over the values in a specific curve set. See CurveSetProxy
    for examples of how to get these from a record.
    """
    def __init__(self, curve_set):
        """
        Create a new CurveValueProxy which proxies the entries in the given
        dictionary.

        :param curve_set: the curve set to proxy.
        """
        # Don't want to trigger the local __setattr__, so call the one
        # in the parent class
        super(CurveValuesProxy, self).__setattr__(
            '_CurveValuesProxy__curve_set', curve_set)

    @property
    def dependent(self):
        """Get a ValueProxy to the dependent curves in this curve set"""
        return ValueProxy(self.__curve_set['dependent'])

    @property
    def independent(self):
        """Get a ValueProxy to the independent curves in this curve set"""
        return ValueProxy(self.__curve_set['independent'])

    def __getattr__(self, item):
        """
        Get the values of the specified curve. It can be either a dependent
        or independent curve.

        :param item: the name of the curve
        :return: the values of the curve
        :raises AttributeError: if the curve does not exist
        """
        return self.__curve_set.get(item)['value']

    def __setattr__(self, key, value):
        """
        Set the value of the specified curve. If the curve exists, the value
        will be replaced. Otherwise, a new dependent curve with the given
        name will be created.

        :param key: the name of the new curve
        :param value: the value of the new curve
        """
        for section in 'independent', 'dependent':
            raw_curve = self.__curve_set.raw[section].get(key)
            if raw_curve:
                break
        else:
            raw_curve = self.__curve_set.raw['dependent'][key] = {}

        # Wrap the value in a list() to convert numpy lists and other
        # list-like objects.
        raw_curve['value'] = list(value)

    def __getitem__(self, item):
        """
        Get the values of the specified curve. It can be either a dependent
        or independent curve.

        :param item: the name of the curve
        :return: the values of the curve
        :raises KeyError: if the curve does not exist
        """
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def __setitem__(self, key, value):
        """
        Set the value of the specified curve. If the curve exists, the value
        will be replaced. Otherwise, a new dependent curve with the given
        name will be created.

        :param key: the name of the new curve
        :param value: the value of the new curve
        """
        setattr(self, key, value)

    def __delitem__(self, key):
        """
        Delete the given curve.

        :param key: the name of the curve
        :raises KeyError: if the item does not exist
        """
        for section in 'independent', 'dependent':
            if self.__curve_set.raw[section].pop(key, None):
                break
        else:
            raise KeyError('No curve named {}'.format(key))

    def __delattr__(self, key):
        """
        Delete the given curve.

        :param key: the name of the curve
        :raises AttributeError: if the item does not exist
        """
        try:
            del self[key]
        except KeyError:
            raise AttributeError(key)

    def __contains__(self, item):
        """
        Check whether the given curve exists.

        :param item: the curve to check
        :return: whether the curve exists
        """
        return (item in self.__curve_set.raw['independent']
                or item in self.__curve_set.raw['dependent'])

    def __iter__(self):
        """
        Iterate over the key, value pairs in the independent and dependent
        curves.

        :return: a generator that iterates over the keys and "value" fields
         of the curves
        """
        for section in 'independent', 'dependent':
            for key, val in six.iteritems(self.__curve_set.raw[section]):
                yield key, val['value']


class LibraryValuesProxy(object):
    """
    A proxy over the library_data section of records (or nested libraries)
    which allows subscript and attribute access to the libraries.

    Allows read access to the libraries. The "data" and "curve_sets" sections
    of individual libraries can then be modified following the same rules as
    for those sections of records when accessed via "data_values" and
    "curve_set_values".
    """
    def __init__(self, raw_libraries):
        """
        Create a new LibraryValuesProxy.

        :param raw_libraries: the dictionary for the libraries section of
         either a record or a nested library.
        """
        self.__raw_libraries = raw_libraries

    def __getattr__(self, library_name):
        """
        Access a library with the given name.

        :param library_name: the name of the library
        :return: a LibraryItemsProxy for the given library
        """
        try:
            return self[library_name]
        except KeyError:
            raise AttributeError('No library named "{}"'.format(library_name))

    def __getitem__(self, library_name):
        """
        Access a library with the given name.

        :param library_name: the name of the library
        :return: a LibraryItemsProxy for the given library
        """
        return LibraryItemsProxy(self.__raw_libraries[library_name])

    def __delitem__(self, library_name):
        """
        Delete the given library.

        :param library_name: the name of the library to delete.
        """
        del self.__raw_libraries[library_name]

    def __contains__(self, library_name):
        """
        Check whether the given library exists.

        :param library_name: the name of the library.
        :return: whether the library exists
        """
        return library_name in self.__raw_libraries

    def __iter__(self):
        """
        Iterate over the libraries.

        :return: a generator over (name, LibraryItemsProxy) pairs of all the
         libraries contained by this proxy.
        """
        for key, val in six.iteritems(self.__raw_libraries):
            yield key, LibraryItemsProxy(val)


class LibraryItemsProxy(object):
    """
    A proxy to get the values of the different sections of a "library_data"
    section of a record or nested library.
    """
    def __init__(self, raw_library_data):
        """
        Create a LibraryItemsProxy.

        :param raw_library_data: the raw dictionary of library whose data
         to proxy
        """
        self.__raw_library_data = raw_library_data

    @property
    def data(self):
        """
        Access the values of the data in this library.

        :return: a ValueProxy over the data in the library.
        """
        return ValueProxy(self.__ensure_section_exists('data'))

    @property
    def curve_sets(self):
        """
        Access the values of the curve_set in this library.

        :return: a CurveSetProxy over the curve sets in the library.
        """
        return CurveSetProxy(self.__ensure_section_exists('curve_sets'))

    @property
    def library_data(self):
        """
        Access the values of the library_data in this library.

        :return: a LibraryValuesProxy over the nested libraries in the library.
        """
        return LibraryValuesProxy(self.__ensure_section_exists('library_data'))

    def __ensure_section_exists(self, section_name):
        """
        Ensures a section with the given name exists, creating it if necessary.

        :param section_name: the name of the section
        :return: the section, whether it existed or was newly-created
        """
        if section_name not in self.__raw_library_data:
            self.__raw_library_data[section_name] = {}
        return self.__raw_library_data[section_name]
