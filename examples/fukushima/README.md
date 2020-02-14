Fukushima Incident Aerial Measurement Systems (AMS) Example
===========================================================

This example illustrates the definition and use of Sina record types tailored to the 
underlying experimental data. It also shows the definition of a record
type to capture information about the `units` associated with this dataset.

The data used here was taken from the DOE/NNSA's Supplemental Environmental 
Monitoring of the Fukushima Response on three days in April and May of 2011.  


Dataset
=======

This data set consists primarily of radiation measurements taken after a nuclear
accident at the Daiichi Nuclear Power Plant on March 11, 2011.  The incident
resulted from an earthquake followed by a tsunami.  The data were captured
during three separate flights: April 5th, April 18th, and May 9th. A total of 32,436
observations were taken using "an array of large thallium activated 
sodium iodide (NaI(T)) crystals" from a fixed-wing aircraft. Collected fields include a time stamp,
location, altitude, and gross count.  The table below summarizes the types of
data we added to the Sina file and, therefore, the database.

| Entry Type | Record Type | Number | Record Name  |
|:----------:|:-----------:|:------:|:-------------|
| Record     | `exp`       | 3      | Experiment   |
| Record     | `obs`       | 32,436 | Observation  |
| Record     | `source`    | 1      | Source       |
| Record     | `units`     | 5      | Units        |
| Relation   | n/a         | 32,436 | Relationship |

This example defines four custom record types:  experiments, observations,
source, and units. Each type of record is described below.

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
