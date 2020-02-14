National Oceanic and Atmospheric Administration (NOAA) Ocean Archive System Example
===================================================================================

This example illustrates the definition and use of Sina record types tailored to the
underlying experimental data. It also shows how a special record type --
in this case `quality control` -- can be used to provide information about
categorical data associated with other records in the dataset.

The data for this example is from the Ocean Acidification Program (OAP) and
contains observations taken on the U.S. West Coast.


Dataset
=======

This data set is an archive of data covering pH, temperature, salinity, etc. of
ocean water collected along the western coast of the United States. A total of
1520 observations were taken in August 2011 consisting of 1450 samples with ~10%
measured twice for quality assurance.  Study types are listed as "CTD profile"
and "discrete sampling". 

The CSV file contains rows with data that includes these observations, their
metadata (e.g., location, time), measurements, parent experiments, and quality control ratings
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

This example defines three custom record types:  experiments, observations, and
quality control. Each type of record is described below.

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

Relationships
-------------
Sina Relationships are used in this set to map the experiment record to all
associated observation records, one relationship per experiment-observation pair.


Building the Database
=====================

If you're working on the LC, a completed database should be available alongside
the Sina virtual environment & wheels. If you would like to create your own local
copy, simply run the `build_db.sh` script after `source`ing a virtual environment
that has Sina installed (see the project-level README). The script creates both 
a database (`data.sqlite`) and a `files` target subdirectory including the original
dataset's files, in order to allow for examples that extract file paths from the 
database for viewing their contents.


References
==========

We pulled the most recently published version of the data in August 2018, which
 was titled 123467.2.2.tar.gz.  You can find out more about this example and
 download the original files yourself by following the links below.

- Data.gov. "Dissolved Inorganic Carbon..." (2015). Retrieved from
  https://catalog.data.gov/dataset/dissolved-inorganic-carbon-total-alkalinity-ph-temperature-salinity-and-other-variables-collect

- NOAA National Centers for Environmental Information. (Download).
  (January 7, 2015). DOI (NCEI): 0.7289/V5JQ0XZ1. Retrieved from
  https://www.nodc.noaa.gov/cgi-bin/OAS/prd/accession/download/123467
