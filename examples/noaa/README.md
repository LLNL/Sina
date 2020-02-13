National Oceanic and Atmospheric Administration (NOAA) Ocean Archive System Example
===================================================================================

Contents
========

- Introduction

- Dataset

  - Experiment
  - Observation
  - Quality Control
  - Relationship


- Building the Database

- References


Introduction
============

This example illustrates the definition and use of record types tailored to the
underlying experimental data.  Consequently, we do not have corresponding
sub-types defined in our schema.  It also shows how a special record type --
in this case `quality control` -- can be used to provide information about
categorical data associated with other records in the dataset.

The data for this example is from the Ocean Acidification Program (OAP) and
contains observations taken on the U.S. West Coast.

A significant part of the initial effort of building a data store is deciding
what to maintain in the database.  In this case, there is a limited amount of
available data and only a rough idea of the types of queries we might want to
perform.  Key goals of this example are to illustrate the definition and use of
custom data types, a variety of Sina queries, and Jupyter Notebook features
such as visualizing the metadata and accessing the contents of files.


Dataset
=======

The CSV file contains rows with data that includes the experiment, observation
information (e.g., location, time), measurements, and quality control ratings
on selected measurements.  The meanings of the quality control ratings were
described on the web site and records added for completeness.  The table below
summarizes the types of data we added to the Sina file and, therefore, the
database.

| Entry Type | Record Type | Number | Record Name     |
|:----------:|:-----------:|:------:|:----------------|
| Record     | `exp`       | 1      | Experiment      |
| Record     | `obs`       | 1,520  | Observation     |
| Record     | `qc`        | 6      | Quality Control |
| Relation   | n/a         | 1,520  | Relationship    |

Each type of record is described below.

Experiment
----------
There is a single  *experiment* record that corresponds to an experiment,
`EXPOCODE` (or experiment identifier), in the source file.  Since it is the
only experiment in the dataset, the relevant files - data (`CSV`), metadata
(`CSV`), Readme (`txt`), two emails (`txt`), a journal (`txt`), a
latitude-longitude data file (`txt`), and a map (`jpg`) - are copied by the
converter into a `files` subdirectory of the target directory with their paths
included in the record.  This is done to allow subsequent visualizations of
their contents.

Observation
-----------
Each *observation* record corresponds to a row in the `CSV` file.  The
observation identifier is a composite of the data's Section Id, Line, Station,
Cast, and Bottle.  The record's contents, which are also written by the
converter to an observation data file, include: depth, pressure, temperature,
oxygen, and pH.

Quality Control
---------------
Each *quality control* record, whose identifier is the quality control value
associated with selected observation data, has an associated description as
its value entry.

Relation
--------
These entries map the experiment to all associated observations, one entry per
experiment-observation pair.


Building the Database
=====================

The converter script - `noaa_csv_to_sina.py` - creates the schema-compliant JSON
file from the example dataset for ingestion into the database using `sina`
at the command line. The script also creates and copies files into a `files`
target subdirectory to allow for examples that extract file paths from the
database for viewing their contents.

Once the data is downloaded, you can proceed to create the files and database.
These instructions make the following assumptions:

- the downloaded CSV file resides in the current directory;
- `SINA_SRC` is the path name of the root directory of a clone of the Sina
  repository;
- `DEST_DIR` is the path to the root destination directory for the output; and
- you activated the virtual environment, `venv`, where `sina` is installed.

First untar the archive file from the web:

    (venv) $ tar xvfz 0123467.2.2.tar.gz

This command builds a `0123467` subdirectory containing background and data
files.  The converter was written to extract the data from a particular `CSV`
file.

Run the converter by entering the following:

    (venv) $ python $SINA_SRC/examples/noaa/noaa_csv_to_sina.py \
             0123467/2.2/data/1-data/WCOA11-01-06-2015_data.csv $DEST_DIR

Now you can ingest the data into an SQLite database as follows:

    (venv) $ sina ingest -d $DEST_DIR/noaa.sqlite --source-type json \
             --database-type sql $DEST_DIR/files/WCOA11-01-06-2015.json

The `DEST_DIR` should now contain the `noaa.sqlite` database and a `files`
subdirectory with associated background materials.  You can now run our
example Jupyter notebooks and or write your own queries against the database.


References
==========

We pulled the most recently published version of the data in August 2018, which
 was titled 123467.2.2.tar.gz.  You can find out more about this example and
 download the original files yourself by following the links below.

- Data.gov. "Dissolved Inorganic Carbon..." (2015). Retrieved from
  https://catalog.data.gov/dataset/dissolved-inorganic-carbon-total-alkalinity-ph-temperature-salinity-and-other-variables-collect

- NOAA National Centers for Environmental Information. (Download).
  (January 7, 2015). Retrieved from
  https://www.nodc.noaa.gov/cgi-bin/OAS/prd/accession/download/123467



Updated: 02/27/2019
