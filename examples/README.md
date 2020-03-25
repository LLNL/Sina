Overview
========

Sina includes a collection of open data sets and related files (Jupyter notebooks,
scripts, converters, etc) demonstrating how the tool and schema are used.

To get started with notebooks, you'll need to run `getting_started.ipynb` or
else manually create a Jupyter kernel. For basic functionality, see `basic_usage.ipynb`, 
which acts as an interactive tutorial not bound to a data set. From there you can explore 
the example data sets and their related notebooks.


Example Layout
==============

Each example set lives in its own `<dataset_name>/` subdirectory and includes a
few basic parts:

 - `README` file
 - dataset converter(s) (`<dataset_name>_<orig_format>_to_<dest_format>.py`)
 - database creation script (`build_db.sh`)
 - one or more example Jupyter notebooks (`<dataset_name>_<notebook_topic>.ipynb`)

The raw data for each set lives separately in `raw_data/`. You shouldn't need to touch this--run
the database creation script to turn it into something Sina can work with, then
launch a notebook of your choosing, or consult the README for additional information about
the set itself (such as its source, layout, and background). The converter may be a good
resource if you're interested in converting data into a Sina format.


Included Sets
=============

All of our current data sets were found through the data.gov portal; however, we also 
plan to add examples using simple "simulations".


Fukushima Incident Aerial Measurement System (AMS)
--------------------------------------------------

This data set consists primarily of radiation measurements taken after a nuclear
accident at the Daiichi Nuclear Power Plant on March 11, 2011.  The incident
resulted from an earthquake followed by a tsunami.  The data were captured
during three separate flights in April and May 2011. A total of 32,436
observations were made.

This example defines four custom record types:  experiments, observations,
source, and units.  One experiment record appears for every flight.  Each
observation is a separate record.  There is one source record to hold the
file paths for the original data and data dictionary.  Finally, units records
are used for efficiently representing the values instead of having each
observation have its own set of identical, optional units values.

* **Data Type:** Observations
* **Examples Subdirectory:** fukushima
* **Original Data:** fukushima.tgz
* **References:**

 - NIH. "Lessons Learned from the Fukushima Nuclear Accident for Improving
   Safety of U.S. Nuclear Plants." (2014).
   https://www.ncbi.nlm.nih.gov/books/NBK253923/.
 - DOE. "Radiation Monitoring Data from Fukushima Area." (2011).
   https://www.energy.gov/downloads/radiation-monitoring-data-fukushima-area.
 - DOE. "Supplemental Environmental Monitoring Data Sets from DOE/NNSA's Fukushima
   Response Efforts." (2011).
   https://www.energy.gov/downloads/radiation-monitoring-data-fukushima-area.
 - Data.gov. "US DOE NNSA Response to 2011 Fukushima Incident: At-sea Aerial
   Data." (Download). (October 2, 2014).
   https://catalog.data.gov/dataset/us-doe-nnsa-response-to-2011-fukushima-incident-at-sea-aerial-data


National Oceanic and Atmospheric Administration (NOAA) Ocean Archive System
---------------------------------------------------------------------------

This data set is an archive of data covering pH, temperature, salinity, etc. of
ocean water collected along the western coast of the United States. A total of
1520 observations were taken in August 2011 consisting of 1450 samples with ~10%
measured twice for quality assurance.  Study types are listed as "CTD profile"
and "discrete sampling".

This example defines three custom record types:  experiments, observations, and
quality control.  There is one experiment record since the data represents a
single cruise.  The record contains paths to a number of files associated with
the data including the original data and metadata CSV files and a map.  Each
observation is a separate record.  Finally, quality control records contain
the QC values associated with some of the observation data and their
descriptions.

* **Data Type:** Observations
* **DOI (NCEI):** 0.7289/V5JQ0XZ1
* **Examples Subdirectory:** noa
* **Original Data:** noaa.tar.gz
* **References:**

 - Data.gov. "Dissolved Inorganic Carbon..." (2015).
   https://catalog.data.gov/dataset/dissolved-inorganic-carbon-total-alkalinity-ph-temperature-salinity-and-other-variables-collect
 - NOAA National Centers for Environmental Information. (Download). (January 7, 2015).
   https://www.nodc.noaa.gov/cgi-bin/OAS/prd/accession/download/123467


Adding More Sets
================

If you plan to add another set, then in addition to making sure the aforementioned files
are included and that the data is fine for general release, please keep the following
in mind:


Naming Conventions
------------------

Stick to the formats explained in the "Layout and Usage" section. When in doubt, check
the existing sets. Leading with the dataset name is useful due to the existence of general
notebooks/converters--most of the example files are only written to work with a specific dataset.


README
------

Each example is required to have a README.md file that includes:

1. a description of the dataset;
1. a description of the records extracted from the dataset;
1. a description of the process for building the database; and
1. references that include attribution to the source of the data, including links and/or copyright information.

*It is critical that the README.md file includes appropriate attribution.*
For open datasets, this mean there's a URL to the data source. Data
collected by running open source applications, such as LLNL's proxy applications,
include the appropriate attribution. For 
example, a dataset based on running Lulesh must have a README.md file that
includes the LLNL-CODE-461231 release number.


Converter
---------

The converter should take the raw source data and convert it to a file that Sina can work
with. Naming is important: the example name `fukushima_csv_to_sina.py` identifies the script
as a converter for the Fukushima dataset.  It also indicates the data comes from a `CSV` file
and is converted to a `Sina schema` file.


Build Script
------------

The build script is primarily intended for automated deployment to a shared space on 
LLNL's Livermore Computing systems to allow users to explore the data using the example
notebooks, though it can also be used to build a local copy of the example database. Each script,
in essence, uses the converter to transform raw data to something Sina recognizes, then uses
Sina to ingest the data into a database.


Notebooks
---------

Any notebook created is automatically included in Sina's tests, though only as far as making sure
no errors (or style issues) are found while running. Be sure to run the tests! Beyond this, take
a look at the existing notebooks for an idea on how to create new ones--since each notebook is
essentially a tutorial, adding explanations and plenty of comments is valuable.
