"""Unit tests for the SQL RecordDAOGetList portion of the DAO structure."""

import unittest

import sina.datastores.sql as sina_sql
from sina.utils import DataRange, ListQueryOperation
from sina.model import Record


class TestSQLRecordDAOGetList(unittest.TestCase):
    """Unit tests for the SQL.RecordDAO.get_list portion of the DAO."""

    def setUp(self):
        """Set up data for testing get_list."""
        factory = sina_sql.DAOFactory()
        self.record_dao = factory.createRecordDAO()
        data = {"eggs": {"value": [0, 1, 2, 3]}}
        data_2 = {"eggs": {"value": [1, 2, 3, 4, 5]}}
        data_3 = {"eggs": {"value": [4, 5, 6, 7]}}
        data_4 = {"spam": {"value": ["awesome", "canned", "zebra"]}}
        data_5 = {"spam": {"value": ["fried", "toasted", "zebra"]}}
        data_6 = {"spam": {"value": ["tree", "honey"]}}
        self.record_1 = Record(id="rec_1", type="sample", data=data)
        self.record_2 = Record(id="rec_2", type="sample", data=data_2)
        self.record_3 = Record(id="rec_3", type="sample", data=data_3)
        self.record_4 = Record(id="rec_4", type="sample", data=data_4)
        self.record_5 = Record(id="rec_5", type="sample", data=data_5)
        self.record_6 = Record(id="rec_6", type="sample", data=data_6)
        self.record_dao.insert_many(
            [self.record_1, self.record_2, self.record_3,
             self.record_4, self.record_5, self.record_6])

    def test_get_list_all_scal_dr(self):
        """
        Given a list of scalar DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of scalars DataRanges.
        """
        self.list_to_check = [DataRange(0, 2), DataRange(3, 6)]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_2.id in records)
        self.assertTrue(self.record_1.id in records)
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_1.id].raw, self.record_1.raw)
        self.assertEqual(records_to_check[self.record_2.id].raw, self.record_2.raw)

    def test_get_list_all_scalars_scal_dr(self):
        """
        Given a list of scalars/DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of scalars and DataRanges.
        """
        self.list_to_check = [DataRange(0, 3), 4]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 1)
        self.assertEqual(records, [self.record_2.id])
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        self.assertEqual(records[0].raw, self.record_2.raw)

    def test_get_list_all_string_dr(self):
        """
        Given a list of string DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of string DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="c", max_inclusive=True)]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 1)
        self.assertEqual(records, [self.record_4.id])
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        self.assertEqual(records[0].raw, self.record_4.raw)

    def test_get_list_all_string_str_dr_mixed(self):
        """
        Given a list of strings/DataRanges and a datum name, we correctly get all Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing all of the given list
        of strings and DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="g", max_inclusive=True), "zebra"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_4.id in records)
        self.assertTrue(self.record_5.id in records)
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ALL))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_4.id].raw, self.record_4.raw)
        self.assertEqual(records_to_check[self.record_5.id].raw, self.record_5.raw)

    def test_get_list_all_empty_list(self):
        """Given an empty list, we should raise a ValueError."""
        self.list_to_check = []
        with self.assertRaises(ValueError) as context:
            list(self.record_dao.get_list(
                datum_name="spam",
                list_of_contents=self.list_to_check,
                ids_only=True,
                operation=ListQueryOperation.ALL))
        self.assertIn('Must supply at least one entry in list_of_contents for',
                      str(context.exception))

    def test_get_list_all_no_results_string(self):
        """Given a list of data that match no Records, we return no Records."""
        self.list_to_check = ["rhino"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ALL))
        self.assertEqual(len(records), 0)

    def test_get_list_any_scal_dr(self):
        """
        Given a list of scalar DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of scalars DataRanges.
        """
        self.list_to_check = [DataRange(0, 2), DataRange(4, 6)]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 3)
        self.assertTrue(self.record_3.id in records)
        self.assertTrue(self.record_2.id in records)
        self.assertTrue(self.record_1.id in records)
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1],
                            records[2].id: records[2]}
        self.assertEqual(records_to_check[self.record_1.id].raw, self.record_1.raw)
        self.assertEqual(records_to_check[self.record_2.id].raw, self.record_2.raw)
        self.assertEqual(records_to_check[self.record_3.id].raw, self.record_3.raw)

    def test_get_list_any_scalars_scal_dr(self):
        """
        Given a list of scalars/DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of scalars and DataRanges.
        """
        self.list_to_check = [DataRange(4, 5), 7]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_2.id in records)
        self.assertTrue(self.record_3.id in records)
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_2.id].raw, self.record_2.raw)
        self.assertEqual(records_to_check[self.record_3.id].raw, self.record_3.raw)

    def test_get_list_any_string_dr(self):
        """
        Given a list of string DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of string DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="c", max_inclusive=True),
                              DataRange(min="d", max="g", max_inclusive=True)]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_4.id in records)
        self.assertTrue(self.record_5.id in records)
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_4.id].raw, self.record_4.raw)
        self.assertEqual(records_to_check[self.record_5.id].raw, self.record_5.raw)

    def test_get_list_any_string_str_dr_mixed(self):
        """
        Given a list of strings/DataRanges and a datum name, we correctly get any Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing any of the given list
        of strings and DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="c", max_inclusive=True),
                              "honey"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 2)
        self.assertTrue(self.record_4.id in records)
        self.assertTrue(self.record_6.id in records)
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            operation=ListQueryOperation.ANY))
        records_to_check = {records[0].id: records[0],
                            records[1].id: records[1]}
        self.assertEqual(records_to_check[self.record_4.id].raw, self.record_4.raw)
        self.assertEqual(records_to_check[self.record_6.id].raw, self.record_6.raw)

    def test_get_list_any_empty_list(self):
        """Given an empty list, we should raise a ValueError."""
        self.list_to_check = []
        with self.assertRaises(ValueError) as context:
            list(self.record_dao.get_list(
                datum_name="spam",
                list_of_contents=self.list_to_check,
                ids_only=True,
                operation=ListQueryOperation.ANY))
        self.assertIn('Must supply at least one entry in list_of_contents for',
                      str(context.exception))

    def test_get_list_any_no_results_string(self):
        """Given a list of data that match no Records, we return no Records."""
        self.list_to_check = ["rhino"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ANY))
        self.assertEqual(len(records), 0)

    def test_get_list_only_scal_dr(self):
        """
        Given a list of scalar DataRanges and a datum name, we correctly get Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing only the given list
        of scalars DataRanges.
        """
        self.list_to_check = [DataRange(0, 2), DataRange(4, 6)]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=False,
            operation=ListQueryOperation.ONLY))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].raw, self.record_2.raw)

    def test_get_list_only_scalars_scal_dr(self):
        """
        Given a list of scalars/DataRanges and a datum name, we correctly get Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing only the given list
        of scalars and DataRanges.
        """
        self.list_to_check = [DataRange(4, 6, max_inclusive=True), 7]
        records = list(self.record_dao.get_list(
            datum_name="eggs",
            list_of_contents=self.list_to_check,
            ids_only=False,
            operation=ListQueryOperation.ONLY))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].raw, self.record_3.raw)

    def test_get_list_only_string_dr(self):
        """
        Given a list of string DataRanges and a datum name, we correctly get Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing only the given list
        of string DataRanges.
        """
        self.list_to_check = [DataRange(min="a", max="f", max_inclusive=True),
                              DataRange(min="y", max="zebra", max_inclusive=True)]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=False,
            operation=ListQueryOperation.ONLY))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].raw, self.record_4.raw)

    def test_get_list_only_string_str_dr_mixed(self):
        """
        Given a list of strings/DataRanges and a datum name, we correctly get Records.

        A record will be included in the return if the corresponding datum name
        in that record has a value of a list containing only the given list
        of strings and DataRanges.
        """
        self.list_to_check = [DataRange(min="q", max="u", max_inclusive=True),
                              "honey"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=False,
            operation=ListQueryOperation.ONLY))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].raw, self.record_6.raw)

    def test_get_list_only_no_results_string(self):
        """Given a list of data that match no Records, we return no Records."""
        self.list_to_check = ["rhino"]
        records = list(self.record_dao.get_list(
            datum_name="spam",
            list_of_contents=self.list_to_check,
            ids_only=True,
            operation=ListQueryOperation.ONLY))
        self.assertEqual(len(records), 0)
