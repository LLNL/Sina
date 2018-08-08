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
  19-21 are values
  31-32 are more values
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
"""

import csv
import json
import os
import pprint
import sys
import traceback


# Current working directory, which is assumed to be the extraction root
CWD = os.getcwd()

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

# Observation data file name
DATA_FN = 'obs-data.txt'

# The path to the data from data.gov
DATASET_FN = os.path.join(CWD,
    "0123467/2.2/data/1-data/WCOA11-01-06-2015_data.csv")

# Data extraction target directory
FILES_DIR = os.path.join(CWD, 'files')

# Quality control values and meanings
QC_DATA = [
  (2, 'good value'),
  (3, 'questionable value'),
  (4, 'bad value'),
  (5, 'value not reported'),
  (6, 'mean of replicated measurements'),
  (9, 'sample not drawn')
]


# --------------------------------- CLASSES ---------------------------------
class NoaaData(object):
    """ 
    Mnoda data class for the NOAA metadata.
    """
    def __init__(self, input_fn):
        self.input_fn = input_fn
        self.output_fn = os.path.join(FILES_DIR, 'WCOA11-01-06-2015.json')
        self.recs = []
        self.rels = []

        for (qid, desc) in QC_DATA:
            self.recs.append({
                "type": "qc",
                "id": qid,
                "values": [ {"name": "desc", "value": desc}, ],
                })

        return

    
    def addExp(self, exp):
        """
        Add an experiment record.

        :param exp: experiment id string
        """
        self.recs.append({
            "type": "exp",
            "id": exp,
            "files": [
                {"uri": self.input_fn, "mimetype": "text/csv"},
                ]
            })
        return


    def addExp2Obs(self, exp, obs):
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
        return


    def addObs(self, oid, obsfn, depth, press, temp, oxy, o2, o2_qc, ph, ph_qc):
        """
        Add the observation data.

        :param oid: observation id string
        :param obsfn: observation file name
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
                {"uri": obsfn, "mimetype": "text/plain"}, 
                ],
            "values": [
                {"name": "depth", "value": float(depth), "units": "meters"},
                {"name": "press", "value": float(press), "units": "meters"},
                {"name": "temp", "value": float(temp), "units": "C"},
                {"name": "ctd_oxy", "value": float(oxy),
                    "units": "micromol/kg"},
                {"name": "o2", "value": float(o2), "units": "micromol/kg"},
                {"name": "o2_qc", "value": int(o2_qc), "tags": ["qc"]},
                {"name": "ph", "value": float(ph)},
                {"name": "ph_qc", "value": int(ph_qc), "tags": ["qc"]},
                ],
            })
        return


    def write(self):
        """
        Write the data to the mnoda file.
        """
        if len(self.recs) > 0:
            mnoda = {'records': self.recs}
            if len(self.rels) > 0:
                mnoda['relationships'] = self.rels

            with open(self.output_fn, 'w') as ofd:
                # Pretty-printing not supported with ingester?
                json.dump(mnoda, ofd, indent=4, separators=(',', ': '),
                    sort_keys=True)
                #json.dump(mnoda, ofd, separators=(',', ': '),
                #    sort_keys=True)
        return



# ----------------------------------- MAIN -----------------------------------
def main():
    """ Process the hard-coded path to the NOAA data. """
    mdata = NoaaData(DATASET_FN)

    with open(DATASET_FN, "r") as ifd:
        lastExp = ''
        sdir = FILES_DIR

        rdr = csv.reader(ifd, delimiter=',')
        try:
            for i, row in enumerate(rdr):
                if i > 0 and len(row[0]) > 0:
                    exp = row[0]
                    if exp != lastExp:
                        sdir = os.path.join(FILES_DIR, exp)
                        if not os.path.isdir(sdir):
                            os.makedirs(sdir)
                        lastExp = row[0]
                        mdata.addExp(exp)

                    oid = '-'.join(row[1:6])

                    # Add the relation between the experiment and observation
                    mdata.addExp2Obs(exp, oid)

                    # Extract the observation data
                    depth, press, temp = row[11:14]
                    oxy, o2, o2_qc = row[18:21]
                    ph, ph_qc = row[30:32]

                    # Write the observation data to a file
                    pdir = os.path.join(FILES_DIR, exp, 'obs%05d' % i)
                    if not os.path.isdir(pdir):
                        os.makedirs(pdir)

                    obsfn = os.path.join(pdir, DATA_FN)
                    with open(os.path.join(obsfn), 'w') as ofd:
                        ofd.write(DATA_FMT % (oid, depth, press, temp, oxy, o2,
                            o2_qc, ph, ph_qc))

                    # Add the observation data (and create the example file)
                    mdata.addObs(oid, obsfn, depth, press, temp, oxy, o2, o2_qc,
                        ph, ph_qc)

        except csv.Error, ce:
            print("ERROR: %s: line %s: %s" % (DATASET_FN, rdr.line_num,
                str(ce)))
            sys.exit(1)

        except Exception, exc:
            print("ERROR: %s: line %s: %s: %s" % (DATASET_FN, rdr.line_num,
                exc.__class__.__name__, str(exc)))
            traceback.print_exc()
            sys.exit(1)

    mdata.write()


if __name__ == "__main__":
  main()
