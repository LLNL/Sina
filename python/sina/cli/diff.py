"""Contains additional tools for use from the command line."""
from __future__ import print_function
import logging

# Disable pylint checks for optional modules
import deepdiff  # pylint: disable=import-error
from texttable import Texttable  # pylint: disable=import-error

logging.basicConfig()
LOGGER = logging.getLogger(__name__)


def print_diff_records(record_one, record_two,  # pylint: disable=R0914
                       significant_digits=None):
    """
    Print a table showing the difference between two Records.

    :param record_one: The first record to compare.
    :param record_two: The second record to compare.
    :param significant_digits: int >= 0, default None. Digits after the
                               decimal point.
    """
    LOGGER.debug("Diffing Records %s and %s.", record_one, record_two)
    deep_diff = deepdiff.DeepDiff(record_one.raw,
                                  record_two.raw,
                                  significant_digits=significant_digits,
                                  verbose_level=2,
                                  view='tree')

    def get_diff_attribute(name):
        """Get an attribute from the diff object."""
        return (list(zip(deep_diff[name]))
                if name in deep_diff else [])

    titles = ['key', record_one.id, record_two.id]
    values_changed = get_diff_attribute('values_changed')
    type_changes = get_diff_attribute('type_changes')
    iterable_item_removed = get_diff_attribute('iterable_item_removed')
    iterable_item_added = get_diff_attribute('iterable_item_added')
    dict_item_removed = get_diff_attribute('dictionary_item_removed')
    dict_item_added = get_diff_attribute('dictionary_item_added')
    set_item_added = get_diff_attribute('set_item_added')
    set_item_removed = get_diff_attribute('set_item_removed')
    attribute_added = get_diff_attribute('attribute_added')
    attribute_removed = get_diff_attribute('attribute_removed')
    repetition_change = get_diff_attribute('repetition_change')
    data = (values_changed +
            type_changes +
            iterable_item_removed +
            iterable_item_added +
            dict_item_removed +
            dict_item_added +
            set_item_added +
            set_item_removed +
            attribute_added +
            attribute_removed +
            repetition_change)
    data_list = []
    for datum in data:
        key = datum[0].path().strip('root')
        if key == "['id']":
            continue
        id_one_output = datum[0].t1
        id_two_output = datum[0].t2
        data_list.append([key, id_one_output, id_two_output])
    data_list.sort()
    data_list = [titles] + data_list
    table = Texttable()
    table.set_cols_align(['c', 'c', 'c'])
    table.set_cols_valign(['m', 'm', 'm'])
    table.add_rows(data_list)
    print(table.draw() + '\n')
