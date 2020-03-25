#!/usr/bin/env python
"""
Example CSV-to-Sina converter using freely available data and Sina's model module.

This module converts the NOAA data to a file following the Sina schema AND generates files, one
per observation, in order to support demonstrations of different capabilities
using Jupyter Notebook examples.

Unlike the Fukushima converter, this one uses Sina objects directly--if you'd like an example of
converting CSV to Sina's JSON format with no reliance on Sina, check out the Fukushima converter!

The data we're most interested in and its column (count from 1) in the CSV:
    1: experiment code
    2: section id
    3: line
    4: station
    5: cast
    6: bottle
   12: bottle depth
   13: pressure (decibars)
   14: CTD T C ITS-90
   19: CTD OXY micromol/kg (available oxygen)
   20: Bot 02 micromol/kg
   21: Bot_02_QC
   31: pH total meas 25 degrees C
   32: pH_QC

 where
      1 is the equivalent of a study/purpose of the database/root dir
   2- 6 form the observational equivalent of a run (so is the id)
  19-21 and 31-32 are data values

 Note:
   CTD = Conductivity-Temperature-Depth
   QC values are:
      2 = good value
      3 = questionable value
      4 = bad value
      5 = value not reported
      6 = mean of replicated measurements
      9 = sample not drawn

For more info about this dataset, see the README.
"""
from __future__ import print_function

import argparse
import csv
import json
import os
import shutil

from sina.model import Record, Relationship

# Relative paths and tags for additional files
SUPPLEMENTAL_FILES = [
    ('WCOA11-01-06-2015_metadata.csv', 'metadata', 'text/csv'),
    ('../../NODC-Readme.txt', 'readme', 'text/plain'),
    ('../../about/0-email.txt', 'email', 'text/plain'),
    ('../../about/1-email.txt', 'email', 'text/plain'),
    ('../../about/journal.txt', 'journal', 'text/plain'),
    ('../../about/0123467_lonlat.txt', 'coordinates', 'text/plain'),
    ('../../about/0123467_map.jpg', 'map', 'image/jpeg'),
    ]

# Expected name for the data CSV
CSV_NAME = 'WCOA11-01-06-2015_data.csv'

# Name of the Sina file we will generate
sina_filename = 'WCOA11-01-06-2015.json'

# Quality control values and meanings
QC_DATA = [
    ('2', 'good value'),
    ('3', 'questionable value'),
    ('4', 'bad value'),
    ('5', 'value not reported'),
    ('6', 'mean of replicated measurements'),
    ('9', 'sample not drawn')
]

STATUS_INTERVAL = 100  # How many runs between status updates if --show-status mode is on
SEPARATOR_LENGTH = 12  # How much buffer whitespace to use when aligning our observation files

# There's a lot of extra information in each observation row. We take only what's specified here.
# The source file uses ISO 8859-1 special characters in its header so, to keep things simple, we
# use column number instead of name.
# Values are a replacement name, hopefully more understandable.
DESIRED_OBS_VALUES = {11: "depth", 12: "press", 13: "temp", 18: "ctd_oxy",
                      19: "o2", 20: "o2_qc", 30: "ph", 31: "ph_qc"}

# Some of the above have units:
UNITS = {"depth": "meters", "press": "decibars", "temp": "C",
         "ctd_oxy": "micromol/kg", "o2": "micromol/kg"}


def process_data(dataset_csv, destination_dir, show_status=False):
    """
    Process the NOAA data.

    :param dataset_csv: path to the NOAA CSV file. Make sure you don't move things after
                        extracting the .tgz, as we're relying on its structure to grab some
                        supplemental files.
    :param destination_dir: destination data directory (i.e. path to where the NOAA
                            files and data are to be written). Everything will be written to a
                            "files" subdirectory.
    :param show_status: Whether to print status markers
    """
    # Sanity checks
    if not os.path.exists(dataset_csv):
        raise ValueError('Expected the data set filename ({}) to exist'.
                         format(dataset_csv))
    elif not os.path.isfile(dataset_csv):
        raise ValueError('Expected the data set filename ({}) to be a file'.
                         format(dataset_csv))
    elif not dataset_csv.endswith(CSV_NAME):
        raise ValueError('Expected a CSV data set filename ({}) ending {}'.
                         format(dataset_csv, CSV_NAME))

    input_csv_path = os.path.realpath(dataset_csv)

    # Create our output directory if it doesn't already exist
    output_dir = os.path.realpath(os.path.join(destination_dir, 'files'))
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Make convenient copies of our source data and supplemental files
    files_to_copy = [supplemental_file_info[0] for supplemental_file_info in SUPPLEMENTAL_FILES]
    files_to_copy.append(input_csv_path)
    for filename in files_to_copy:
        shutil.copy(os.path.realpath(os.path.join(os.path.dirname(dataset_csv), filename)),
                    output_dir)

    # Process the NOAA CSV itself
    sina_data = NoaaData(output_dir)
    try:
        source_csv = open(input_csv_path, "r", newline='', encoding='ISO-8859-1')  # Py3
    except TypeError:
        source_csv = open(input_csv_path, "rb")  # Py2

    with source_csv as csv_data:
        csv_reader = csv.reader(csv_data)
        next(source_csv) # Skip the header
        if show_status:
            print('Processing (. = {} rows): '.format(STATUS_INTERVAL), end='')
        last_exp_id = ''  # If there was more than 1 experiment, we'd expect them to be sequential
        for row_num, row in enumerate(csv_reader):
            if len(row[0]) > 0:
                exp_id = row[0]
                obs_id = '-'.join(row[1:6])
                if exp_id != last_exp_id:
                    last_exp_id = exp_id
                    exp_dir = os.path.join(destination_dir, exp_id)
                    if not os.path.isdir(exp_dir):
                        os.makedirs(exp_dir)
                    sina_data.add_experiment(exp_id)

                sina_data.add_relationship(exp_id, obs_id)

                data = {name: row[offset] for offset, name in DESIRED_OBS_VALUES.items()}

                # Each observation gets its own file for use with the notebooks
                # This is essentially a replica of the CSV row.
                obs_filename = os.path.join(exp_dir, 'obs_{}_data.txt'.format(row_num))
                with open(obs_filename, 'w') as obs_file:
                    for name, value in data.items():
                        units_str = " ({})".format(UNITS[name]) if name in UNITS.keys() else ""
                        obs_file.write("{name}{sep}= {val}{units}\n"
                                       .format(name=name, sep=' '*(SEPARATOR_LENGTH-len(name)),
                                               val=value, units=units_str))

                sina_data.add_observation(obs_id, obs_filename, data)

            if show_status and (row_num % STATUS_INTERVAL) == 0:
                print('.', end='')
    source_csv.close()

    sina_data.dump()


# --------------------------------- CLASSES ---------------------------------
class NoaaData(object):
    """
    Sina data class for the NOAA metadata.
    """
    def __init__(self, source_dir):
        """
        Get our first Records created and set up initial info.

        :param source_dir: path to the "files" subdirectory we create during conversion.
                           Because we've already copied important files into there, it acts as both
                           source and destination.
        """
        self.source_dir = source_dir
        # We start off with a few Records detailing how the quality control numbers work.
        self.records = [Record(qid, "qc", data={"desc": {"value": desc}}) for qid, desc in QC_DATA]
        self.relationships = []

    def add_experiment(self, experiment_id):
        """
        Add an experiment Record.

        :param experiment_id: experiment id string
        """
        exp_files = {os.path.join(self.source_dir, CSV_NAME): {"mimetype": "text/csv",
                                                               "tags": ["data"]}}
        for extra_file, tag, mimetype in SUPPLEMENTAL_FILES:
            extra_path = os.path.join(self.source_dir, os.path.basename(extra_file))
            exp_files[extra_path] = {"mimetype": mimetype, "tags": [tag]}
        self.records.append(Record(experiment_id, "exp", files=exp_files))

    def add_relationship(self, exp_id, obs_id):
        """
        Add an experiment-to-observation Relationship (the only kind in this dataset).

        :param exp_id: experiment id string
        :param obs_id: observation id string
        """
        self.relationships.append(Relationship(subject_id=exp_id,
                                               predicate="contains",
                                               object_id=obs_id))

    def add_observation(self, obs_id, obs_filename, data):
        """
        Add an observation Record.

        :param obs_id: the id of the observation to create
        :param obs_filename: the file that contains its data (and only its data)
        :param data: a dictionary of datum_name: val that we want to assign to this observation.
        """
        obs_record = Record(obs_id, "obs", files={obs_filename: {"mimetype": "text/plain"}})
        for name, val in data.items():
            if name in ("o2_qc", "ph_qc"):
                obs_record.add_data(name, val, tags=["qc"])
            else:
                obs_record.add_data(name, float(val), units=UNITS.get(name, None))
        self.records.append(obs_record)

    def dump(self):
        """
        Write the data to file.
        """
        json_document = {"records": [rec.raw for rec in self.records],
                         "relationships": [rel.to_json_dict() for rel in self.relationships]}
        with open(os.path.join(self.source_dir, sina_filename), 'w') as outfile:
            json.dump(json_document, outfile)


# ----------------------------------- MAIN -----------------------------------
def main():
    """Collect args from user (like the destination for written files) and run."""
    parser = argparse.ArgumentParser(
        description='Convert selected NOAA Ocean Archive System dataset from '
                    'CSV to a Sina file. Full paths will be written to the '
                    'file to facilitate subsequent access from Jupyter '
                    'notebooks.')

    parser.add_argument('-s', '--show-status', action='store_true',
                        help='Display a dot for every {} lines processed'.
                             format(STATUS_INTERVAL))

    parser.add_argument('csv_pathname',
                        help='The pathname to the CSV file, which needs to '
                             'end in WCOA11-01-06-2015_data.csv.')

    parser.add_argument('dest_dirname',
                        help='The directory to write the Sina file to. Will be created '
                             'if it doesn\'t exist.')

    args = parser.parse_args()

    process_data(args.csv_pathname, args.dest_dirname, args.show_status)


if __name__ == "__main__":
    main()
