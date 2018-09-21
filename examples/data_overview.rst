Example Data Sets
=================

We provide example data sets and Jupyter notebooks to illustrate use of our tools
for different types of data.  All of our current data sets were found through the
data.gov portal; however, we also plan to add examples using simple "simulations"
in the near future.

A snapshot of the original data is kept for reproducibility in the Sina source code
repository in a suitably named subdirectory of *examples*.


.. contents:: Examples
   :depth: 1


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
