#!/usr/bin/env python
"""
Example CSV-to-Mnoda converter using freely available data.

This module converts the NOAA data to a Mnoda file AND generates files, one
per observation, in order to support demonstrations of different capabilities
using Jupyter Notebook examples.

The following is a list of the relevant column number-value pairings:
    1: expocode (experiment?)
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
  19-21 are data values
  31-32 are more data values
 and
   each line becomes a separate file within the observation directory

 Note:
   CTD = Conductivity-Temperature-Depth
   QC values are:
      2 = good value
      3 = questionable value
      4 = bad value
      5 = value not reported
      6 = mean of replicated measurements
      9 = sample not drawn

Data Source: https://catalog.data.gov/dataset/\
    dissolved-inorganic-carbon-total-alkalinity-ph-\
    temperature-salinity-and-other-variables-collect
 with direct download link:
    https://www.nodc.noaa.gov/cgi-bin/OAS/prd/accession/download/123467
"""

import argparse
import csv
import json
import os
import shutil
import sys
import traceback


# Relative paths and tags for additional files
MORE_FILES = [
    ('WCOA11-01-06-2015_metadata.csv', 'metadata', 'text/csv'),
    ('../../NODC-Readme.txt', 'readme', 'text/plain'),
    ('../../about/0-email.txt', 'email', 'text/plain'),
    ('../../about/1-email.txt', 'email', 'text/plain'),
    ('../../about/journal.txt', 'journal', 'text/plain'),
    ('../../about/0123467_lonlat.txt', 'coordinates', 'text/plain'),
    ('../../about/0123467_map.jpg', 'map', 'image/jpeg'),
    ]

# Name of the data CSV file provided by NOAA
DATA_FN = 'WCOA11-01-06-2015_data.csv'

# Name of the Mnoda file we will generate
MNODA_FN = 'WCOA11-01-06-2015.json'

# Quality control values and meanings
QC_DATA = [
    (2, 'good value'),
    (3, 'questionable value'),
    (4, 'bad value'),
    (5, 'value not reported'),
    (6, 'mean of replicated measurements'),
    (9, 'sample not drawn')
]

# Observation data file format
DATA_FMT = """\
obs_id      = %s
depth       = %s
depth_units = meters
press       = %s
press_units = decibars
ctd_temp    = %s
temp_units  = C
ctd_oxy     = %s
oxy_units   = micromol/kg
o2          = %s
o2_units    = micromol/kg
o2_qc       = %s
ph          = %s
ph_qc       = %s
"""


def process_data(dataset_fn, dest_dn):
    """
    Process the NOAA data.

    :param dataset_fn: qualified name of the NOAA CSV file
    :param dest_dn: destination data directory (i.e., path to where the NOAA
                    files and data are to be written
    """
    if not os.path.exists(dataset_fn):
        raise ValueError('Expected the data set filename (%s) to exist' %
                         dataset_fn)
    elif not os.path.isfile(dataset_fn):
        raise ValueError('Expected the data set filename (%s) to be a file' %
                         dataset_fn)
    elif not dataset_fn.endswith(DATA_FN):
        raise ValueError('Expected a CSV data set filename (%s) ending %s' %
                         (dataset_fn, DATA_FN))

    # Make sure the files subdirectory exists in the destination directory
    files_dn = os.path.realpath(os.path.join(dest_dn, 'files'))
    if not os.path.isdir(files_dn):
        os.makedirs(files_dn)

    # Copy the data and metadata files to the destination so they will be
    # available to the user in the destination directory
    input_fn = os.path.realpath(dataset_fn)
    shutil.copy(input_fn, files_dn)
    for extra_fn, _tag, _mtype in MORE_FILES:
        shutil.copy(os.path.realpath(os.path.join(os.path.dirname(input_fn),
                                                  extra_fn)), files_dn)

    # Now process the NOAA data CSV file
    mdata = NoaaData(files_dn)
    with open(input_fn, "r") as ifd:
        last_exp = ''

        rdr = csv.reader(ifd, delimiter=',')
        try:
            for i, row in enumerate(rdr):
                if i > 0 and len(row[0]) > 0:
                    exp = row[0]
                    if exp != last_exp:
                        exp_dn = os.path.join(files_dn, exp)
                        if not os.path.isdir(exp_dn):
                            os.makedirs(exp_dn)
                        last_exp = row[0]
                        mdata.add_exp(exp)

                    oid = '-'.join(row[1:6])

                    # Add the relation between the experiment and observation
                    mdata.add_exp2obs(exp, oid)

                    # Extract the observation data
                    depth, press, temp = row[11:14]
                    oxy, o2, o2_qc = row[18:21]
                    ph, ph_qc = row[30:32]

                    # Write the observation data to a file
                    obs_dir = os.path.join(files_dn, exp, 'obs%05d' % i)
                    if not os.path.isdir(obs_dir):
                        os.makedirs(obs_dir)

                    obs_fn = os.path.join(obs_dir, 'obs-data.txt')
                    with open(os.path.join(obs_fn), 'w') as ofd:
                        ofd.write(DATA_FMT % (oid, depth, press, temp, oxy, o2,
                                              o2_qc, ph, ph_qc))

                    # Add the observation data (and create the example file)
                    mdata.add_obs(oid, obs_fn, depth, press, temp, oxy, o2,
                                  o2_qc, ph, ph_qc)

        except csv.Error, ce:
            print("ERROR: %s: line %s: %s" % (dataset_fn, rdr.line_num,
                                              str(ce)))
            sys.exit(1)

        except Exception, exc:
            print("ERROR: %s: line %s: %s: %s" % (dataset_fn, rdr.line_num,
                                                  exc.__class__.__name__,
                                                  str(exc)))
            traceback.print_exc()
            sys.exit(1)

    mdata.write()


# --------------------------------- CLASSES ---------------------------------
class NoaaData(object):
    """
    Mnoda data class for the NOAA metadata.
    """
    def __init__(self, files_dn):
        """
        Data constructor.

        :param files_dn: pathname to the root of the noaa data directory
        """
        self.files_dn = files_dn
        self.recs = []
        self.rels = []

        for (qid, desc) in QC_DATA:
            self.recs.append({
                "type": "qc",
                "id": qid,
                "data": [{"name": "desc", "value": desc}, ],
                })

    def add_exp(self, exp):
        """
        Add an experiment record.

        :param exp: experiment id string
        """
        lfiles = []
        lfiles.append({"uri": os.path.join(self.files_dn, DATA_FN),
                       "mimetype": "text/csv",
                       "tags": ["data"]})

        for extra_fn, tag, mtype in MORE_FILES:
            lfiles.append({"uri": os.path.join(self.files_dn,
                                               os.path.basename(extra_fn)),
                           "mimetype": mtype, "tags": [tag]})

        self.recs.append({
            "type": "exp",
            "id": exp,
            "files": lfiles
            })

    def add_exp2obs(self, exp, obs):
        """
        Add an experiment-to-observation relationship.

        :param exp: experiment id string
        :param obs: observation id string
        """
        self.rels.append({
            "subject": exp,
            "predicate": "contains",
            "object": obs,
            })

    def add_obs(self, oid, obs_fn, depth, press, temp, oxy, o2, o2_qc, ph,
                ph_qc):
        """
        Add the observation data.

        :param oid: observation id string
        :param obs_fn: observation file name
        :param depth: bottle depth string (in meters)
        :param press: pressure (in decibars)
        :param temp: CTD temperature (in C)
        :param oxy:  CTD, or available, oxygen (in micromol/kg)
        :param o2: bottle o2 (in micromol/kg)
        :param o2_qc: bottle o2 quality control
        :param ph:  pH total measured 25 degrees C
        :param ph_qc: pH quality control
        """
        # Add the observation record
        self.recs.append({
            "type": "obs",
            "id": oid,
            "files": [
                {"uri": obs_fn, "mimetype": "text/plain"},
                ],
            "data": [
                {"name": "depth", "value": float(depth), "units": "meters"},
                {"name": "press", "value": float(press), "units": "decibars"},
                {"name": "temp", "value": float(temp), "units": "C"},
                {"name": "ctd_oxy", "value": float(oxy),
                 "units": "micromol/kg"},
                {"name": "o2", "value": float(o2), "units": "micromol/kg"},
                {"name": "o2_qc", "value": int(o2_qc), "tags": ["qc"]},
                {"name": "ph", "value": float(ph)},
                {"name": "ph_qc", "value": int(ph_qc), "tags": ["qc"]},
                ],
            })

    def write(self):
        """
        Write the data to the mnoda file.
        """
        if len(self.recs) > 0:
            mnoda = {'records': self.recs}
            if len(self.rels) > 0:
                mnoda['relationships'] = self.rels
        else:
            mnoda = {}

        with open(os.path.join(self.files_dn, MNODA_FN), 'w') as ofd:
            json.dump(mnoda, ofd, indent=4, separators=(',', ': '),
                      sort_keys=True)


# ----------------------------------- MAIN -----------------------------------
def main():
    '''
    Allow the user to provide the dataset file name and destination data
    directory name.
    '''
    parser = argparse.ArgumentParser(
        description='Convert selected NOAA Ocean Archive System dataset from '
                    'CSV to a Mnoda file. Full paths will be written to the '
                    'file to facilitate subsequent access from Jupyter '
                    'notebooks.')

    parser.add_argument('csv_pathname',
                        help='The pathname to the CSV file, which needs to '
                             'end in WCOA11-01-06-2015_data.csv.')

    parser.add_argument('dest_dirname',
                        help='The pathname to the destination noaa data '
                             'directory to which the Mnoda and observation '
                             'files are to be written.  The directory will be '
                             'created if it does not exist.')

    args = parser.parse_args()

    # Process the NOAA data.
    process_data(args.csv_pathname, args.dest_dirname)


if __name__ == "__main__":
    main()
