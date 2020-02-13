Fukushima Incident Aerial Measurement Systems (AMS) Example
===========================================================

Contents
========

- Introduction

- Dataset

  - Experiment
  - Observation
  - Source
  - Units
  - Relationship


- Building the Database

- References


Introduction
============

This example illustrates the definition and use of record types tailored to the 
underlying experimental data.  Consequently, we do not have corresponding 
sub-types defined in our schema.  It also shows the definition of a record
type to capture information about the `units` associated with this dataset.

The data used here was taken from the DOE/NNSA's Supplemental Environmental 
Monitoring of the Fukushima Response on three days in April and May of 2011.  
The raw, validated data was taken using "an array of large thallium activated 
sodium iodide (NaI(T)) crystals" from a fixed-wing aircraft.

The monitoring effort was in response to the nuclear power plant disaster 
resulting from an earthquake and subsequent tsunami on March 11, 2011. 


Dataset
=======

The CSV file contains data from observations collected on three different 
dates: April 5th, April 18th, and May 9th.  Fields include a time stamp,
location, altitude, and gross count.  The table below summarizes the types of
data we added to the Sina file and, therefore, the database.

| Entry Type | Record Type | Number | Record Name  |
|:----------:|:-----------:|:------:|:-------------|
| Record     | `exp`       | 3      | Experiment   |
| Record     | `obs`       | 32,436 | Observation  |
| Record     | `source`    | 1      | Source       |
| Record     | `units`     | 5      | Units        |
| Relation   | n/a         | 32,436 | Relationship |

Each type of record is described below.

Experiment
----------
Each *experiment* record corresponds to a data collection date.  The converter
creates a separate CSV file for each date so they could be used in example
queries.

Observation
-----------
Each *observation* record holds key data associated with each measurement taken:
date, time, latitude, longitude, altitudes, collection live times, and 
normalized gross counts.

Source
------
There is a single *source* record to contain the original data and data
dictionary files.

Units
-----
Each *units* record holds the measurement (as the id) and data for the
associated units and description.  The idea is to minimize the duplication of
unit values across observations since the units for each measurement are fixed
for the entire dataset.

Relation
--------
These entries map the experiment to all associated observations, one entry per
experiment-observation pair.


Building the Database
=====================

The converter script - `fukushima_csv_to_sina.py` - creates the schema-compliant
JSON file from the example dataset for ingestion into the database using `sina`
at the command line.  The script also creates and copies files into a `files` 
target subdirectory to allow for examples that extract file paths from the 
database for viewing their contents.

Once the data is downloaded, you can proceed to create the files and database.
These instructions make the following assumptions:

- the downloaded CSV file resides in the current directory;
- `SINA_SRC` is the pathname of the root directory of a clone of Sina 
  repository; 
- `DEST_DIR` is the path to the root destination directory for the output; and
- you activated the virtual environment, `venv`, where `sina` is installed.

Given the input file is in the current directory, enter the following:

    (venv) $ python $SINA_SRC/examples/fukushima/fukushima_csv_to_sina.py \
              ./AMS\ C12\ Sea\ Data.csv $DEST_DIR

Now you can ingest the data into an SQLite database as follows:

    (venv) $ sina ingest -d $DEST_DIR/fukushima.sqlite --source-type json \
             --database-type sql $DEST_DIR/files/AMS_C12_SeaData.json

The `DEST_DIR` should now contain the `fukushima.sqlite` database and a `files`
subdirectory with associated background materials.  You can now run our
example Jupyter notebooks and or write your own queries against the database.


References
==========

- NIH. "Lessons Learned from the Fukushima Nuclear Accident for Improving
  Safety of U.S. Nuclear Plants." (2014).  Retrieved from
  https://www.ncbi.nlm.nih.gov/books/NBK253923/.

- DOE. "Radiation Monitoring Data from Fukushima Area." (2011). Retrieved from
  https://www.energy.gov/downloads/radiation-monitoring-data-fukushima-area.

- DOE. "Supplemental Environmental Monitoring Data Sets from DOE/NNSA's
  Fukushima Response Efforts." (2011). Retrieved from
  https://www.energy.gov/downloads/supplemental-environmental-monitoring-data-sets-doennsas-fukushima-response-efforts.

- Data.gov. "US DOE NNSA Response to 2011 Fukushima Incident: At-sea Aerial
  Data." (2017).  Retrieved from 
  https://catalog.data.gov/dataset/us-doe-nnsa-response-to-2011-fukushima-incident-at-sea-aerial-data.



Updated: 02/27/2019
