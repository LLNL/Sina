#!/usr/bin/env python
"""
Example CSV-to-Mnoda converter using freely available data.

This module converts the Fukushima aerial radiolagical data to a Mnoda file.
The data consists of multiple measurements taken for a period of over an hour
on each of three separate days.

Record types are:
    exp     contain the path to a file containing observations for the flight
            date
    obs     contain selected observation information as metadata
    source  contains paths to source files
    units   contain the units and description of each measurement (with units)

Relationships associated observations to experiments.

Note that units records were created (versus adding them to each of the nearly
32.5K observation records) for efficiency.  Doing so also provides the
opportunity to illustrate the concept of "joins" across record types.

Files are created for each flight date (aka experiment) based on data
dictionary comments that each date should be treaded as a separate snapshot.

The following is a list of the relevant column number-value pairings:
    1: Time (MM/DD/YYYY HH:MM:SS AM)
    2: Latitude
    3: Longitude
    4: ALT_HAE
    5: AGL
    6: NumDet
    7: LiveuSec
    8: GC
    9: GCNORM
 where, according to the data dictionary (PDF):
      1 is the measurement GPS date and time
    2-3 is the GPS receiver location in decimal degrees
      4 is the height above the ellipsoid from the GPS receiver in meters
      5 is the height above the ground/sea in meters
      6 is the number of NaI(TI) detectors in the array, where NaI(TI) is
           thallium activated sodium iodide crystals and the arrays had 3 or
           6 crystals for a volume of 2 liters
      7 is the collection live time in microseconds
      8 is the gross counts in the detector array
      9 is the gross counts in the array, normalized by the live time, with
        results in counts per second (according to the data dictionary)

Data Source: https://catalog.data.gov/dataset/\
        us-doe-nnsa-response-to-2011-fukushima-incident-at-sea-aerial-data
"""

import argparse
import csv
import datetime
import json
import os
import shutil
import sys
import traceback


# Name of the data CSV file containing the original data
DATA_FN = 'AMS C12 Sea Data.csv'

# JSON Keys
# .. GPS altitude
KEY_ALTITUDE_GPS = "alt_hae"

# .. Ground/Sea altitude
KEY_ALTITUDE_GS = "agl"

# .. Gross Count normalized by Live time (reportedly in count per second)
KEY_GCNORM = "gcnorm"

# .. Latitude
KEY_LATITUDE = "latitude"

# .. Live time
KEY_LIVE_TIME = "live"

# .. Latitude
KEY_LONGITUDE = "longitude"


# Relative paths -- to DATA_FN directory -- and tags for additional files
MORE_FILES = [
    ('AMS C12 Sea Data Dictionary.pdf', 'data dictionary',
        'application/pdf'),
    ('amsdatamarch25udpated1-110325170504-phpapp02.pptx', 'assessment',
        'application/vnd.openxmlformats-officedocument.presentationml.'
        'presentation')
    ]

# Name of the Mnoda file we will generate
MNODA_FN = 'AMS_C12_SeaData.json'

# The units and description for each value
UNITS = [
        (KEY_LATITUDE, "degrees", "GPS location latitude"),
        (KEY_LONGITUDE, "degrees", "GPS location longitude"),
        (KEY_ALTITUDE_GPS, "meters",
            "Height above the ellipsoid from the GPS receiver"),
        (KEY_ALTITUDE_GS, "meters", "Height above the ground/sea"),
        (KEY_LIVE_TIME, "microseconds", "Collection live time"),
        (KEY_GCNORM, "cps", "Normalized gross count in count per second")]


# -------------------------------- Process Data -------------------------------
def process_data(dataset_fn, dest_dn):
    """
    Process the Fukushima data.

    :param dataset_fn: qualified name of the Fukushima CSV file
    :param dest_dn: destination data directory (i.e., path to where the
                    Fukushima files and data are to be written
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

    # Copy the data and extra file(s) to the destination so they will be
    # available to the user in the destination directory
    input_fn = os.path.realpath(dataset_fn)
    shutil.copy(input_fn, files_dn)
    for extra_fn, _, _ in MORE_FILES:
        path = os.path.join(os.path.dirname(input_fn), extra_fn)
        if os.path.isfile(path):
            shutil.copy(path, files_dn)

    # Now process the Fukushima data CSV file
    mdata = FukushimaData(files_dn)
    with open(input_fn, "r") as ifd:
        last_exp_id = ''
        header = ''
        obs = []

        creader = csv.reader(ifd, delimiter=',')
        try:
            for i, row in enumerate(creader):
                if i > 0 and len(row[0]) > 0:
                    obs_dt = datetime.datetime.strptime(row[0],
                                                        '%m/%d/%Y %I:%M:%S %p')

                    # The "experiment" is the flight date
                    exp_id = obs_dt.strftime('%Y-%m-%d')
                    if exp_id != last_exp_id:
                        if last_exp_id != '':
                            mdata.write_exp(last_exp_id, obs)
                            mdata.add_exp(last_exp_id)

                        last_exp_id = exp_id
                        obs = [header, row]
                    else:
                        obs.append(row)

                    # Add the relation between the experiment and observation
                    # .. The observation id is a reformatted date-time
                    obs_id = '-'.join([exp_id, obs_dt.strftime('%H-%M-%S')])
                    mdata.add_exp2obs(exp_id, obs_id)

                    # Add the observation data
                    mdata.add_obs(obs_id, row)

                elif i == 0:
                    header = row

            # Add last experiment and its associated observations
            if last_exp_id != '' and len(obs) > 0:
                mdata.write_exp(last_exp_id, obs)
                mdata.add_exp(last_exp_id)

        except csv.Error as cerr:
            print("ERROR: %s: line %s: %s" % (dataset_fn, creader.line_num,
                                              str(cerr)))
            sys.exit(1)

        except Exception as exc:
            print("ERROR: %s: line %s: %s: %s" % (dataset_fn, creader.line_num,
                                                  exc.__class__.__name__,
                                                  str(exc)))
            traceback.print_exc()
            sys.exit(1)

    mdata.write()


# --------------------------------- CLASSES ---------------------------------
class FukushimaData(object):
    """
    Mnoda data class for the Fukushima metadata.
    """
    def __init__(self, files_dn):
        """
        Data constructor.

        :param files_dn: pathname to the root of the Fukushima data directory
        """
        self.files_dn = files_dn
        self.recs = []
        self.rels = []
        self.add_source()
        self.add_units()

    def add_exp(self, exp_id):
        """
        Add an experiment record.

        :param exp_id: experiment id string
        """
        self.recs.append({
            "type": "exp",
            "id": exp_id,
            "files": [{"uri": self.get_exp_fn(exp_id), "mimetype": "text/csv",
                      "tags": ["data"]}]
            })

    def add_exp2obs(self, exp_id, obs_id):
        """
        Add an experiment-to-observation relationship.

        :param exp_id: experiment id string
        :param obs_id: observation id string
        """
        self.rels.append({
            "subject": exp_id,
            "predicate": "contains",
            "object": obs_id,
            })

    def add_obs(self, obs_id, row):
        """
        Add the observation data.

        :param obs_id: observation id string
        :param row:    list of observation or measurement data
        """
        # Add the observation record
        timestamp, lat, lon, alt, agl, _numdet, live, _gc, gcnorm = row
        ts = timestamp.split()
        self.recs.append({
            "type": "obs",
            "id": obs_id,
            "data": {
                "date": {"value": ts[0]},
                "time": {"value": ' '.join(ts[1:])},
                KEY_LATITUDE: {"value": float(lat)},
                KEY_LONGITUDE: {"value": float(lon)},
                KEY_ALTITUDE_GPS: {"value": float(alt)},
                KEY_ALTITUDE_GS: {"value": float(agl)},
                KEY_LIVE_TIME: {"value": float(live)},
                KEY_GCNORM: {"value": float(gcnorm)},
                },
            })

    def add_source(self):
        """
        Add the source record, which contains the original data and associated
        files.
        """
        lfiles = []
        lfiles.append({"uri": os.path.join(self.files_dn, DATA_FN),
                       "mimetype": "text/csv",
                       "tags": ["data"]})

        for extra_fn, tag, mtype in MORE_FILES:
            path = os.path.join(os.path.dirname(self.files_dn), extra_fn)
            if os.path.isfile(path):
                lfiles.append({"uri": path, "mimetype": mtype, "tags": [tag]})

        self.recs.append({
            "type": "source",
            "id": "AMS-C12",
            "files": lfiles
            })

    def add_units(self):
        """
        Add the units records since the units are consistent across all
        observations.
        """
        for units_id, units, desc in UNITS:
            self.recs.append({
                "type": "units",
                "id": units_id,
                "data": {
<<<<<<< HEAD
                    "measure": {"value": units},
                    "description": {"value": desc},
=======
                          "measure": {"value": units},
                          "description": {"value": desc}
>>>>>>> f2050b4948d958f901072538ad4908b4ded2b084
                },
            })

    def get_exp_fn(self, exp_id):
        """
        Return the file name associated with the experiment.

        :param exp_id: experiment id string
        """
        return os.path.join(self.files_dn, '%s-data.csv' % exp_id)

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

    def write_exp(self, exp_id, obs):
        """
        Write the associated observations to a flight-specific file.

        :param exp_id: experiment id string
        :param obs:    list of observations associated with the experiment
        """
        with open(self.get_exp_fn(exp_id), 'w') as ofd:
            for row in obs:
                ofd.write('%s\n' % ','.join(row))


# ----------------------------------- MAIN -----------------------------------
def main():
    '''
    Allow the user to provide the dataset file name and destination data
    directory name.
    '''
    parser = argparse.ArgumentParser(
        description='Convert Fukushima dataset from CSV to a Mnoda file.  Full'
                    'paths will be written to the file to facilitate '
                    'subsequent access from Jupyter notebooks.')

    parser.add_argument('csv_pathname',
                        help='The pathname to the CSV file, which needs to '
                             'end in %s.' % DATA_FN)

    parser.add_argument('dest_dirname',
                        help='The pathname to the destination Fukushima data '
                             'directory to which the Mnoda and observation '
                             'files are to be written.  The directory will be '
                             'created if it does not exist.')

    args = parser.parse_args()

    # Process the Fukushima data.
    process_data(args.csv_pathname, args.dest_dirname)


if __name__ == "__main__":
    main()
