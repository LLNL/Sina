"""Demonstrate a math-based Sina Cassandra query."""

import sina.datastores.cass_schema as cass_schema

KEYSPACE = "all"
scalar_1_name = "energy"
scalar_2_name = "volume"
# Math to perform is specified on line 19

cass_schema.form_connection(KEYSPACE)

energies = list(cass_schema.ScalarFromRecord.objects
                .filter(name=scalar_1_name)
                .values_list('value', 'record_id').allow_filtering())
volumes = list(cass_schema.ScalarFromRecord.objects
               .filter(name=scalar_2_name)
               .values_list('value', 'record_id').allow_filtering())

for energy_entry, volume_entry in zip(energies, volumes):
    energy, record_id = energy_entry
    volume, record_id_check = volume_entry
    if record_id != record_id_check:
        raise ValueError("Record {} and {} differ in available scalars"
                         .format(record_id, record_id_check))
    if (energy + (volume / energy) > 10):
        print(record_id)
