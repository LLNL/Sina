"""Demonstrate a math-based Sina SQL query."""

import os

from sina.datastores.sql_schema import Scalar
from sina.datastores.sql import DAOFactory

DATABASE = "somefile.sqlite"
# List scalars alphabetically
SCALARS_OF_INTEREST = ["energy", "volume"]
# Math to perform is specified on line 34

TARGET_DB = ("{}/{}"
             .format(os.path.dirname(os.path.abspath(__file__)), DATABASE))

# This uses 2 queries regardless of the number of scalars
inst = DAOFactory(db_path=DATABASE)

list_of_result_tuples = (inst.session.query(Scalar.value, Scalar.record_id).
                         filter(Scalar.name.in_(SCALARS_OF_INTEREST)).
                         order_by(Scalar.record_id, Scalar.name).all())

for index in range(0, len(list_of_result_tuples), len(SCALARS_OF_INTEREST)):
    energy_val, record_id = list_of_result_tuples[index]
    volume_val, record_id_check = list_of_result_tuples[index+1]
    energy_val = float(energy_val)
    volume_val = float(volume_val)

    if record_id != record_id_check:
        raise ValueError("Record {} and {} differ in available scalars"
                         .format(record_id, record_id_check))

    if (energy_val + volume_val/energy_val) > 10:
        print(str(record_id))
