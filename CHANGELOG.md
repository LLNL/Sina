Overview
========

This file summarizes the major changes in each version of Sina. For a full list,
see the commit log at:
https://lc.llnl.gov/bitbucket/projects/SIBO/repos/sina/commits?until=master

1.5
===
- Made Cassandra, Jupyter, and some cli tools optional
- Added license files
- Added Pylint to tests, made project Pylint compliant
- Made Python 3 the default for the deployed virtual env
- Reorganized modules for usability (separated out CLI module, etc)

1.4
===
- Added list support to Record data
- Added support for querying on list data
- Added new example notebooks (basic Sina usage and Record comparison)
- Replaced ScalarRanges with the more flexible and powerful DataRanges
- Added data_query(), the core method for finding Records based on data
- Added Record comparison
- Merged in Mnoda CPP
- Cleaned and clarified Makefile
- Introduced ability to delete Records

1.3
===
- Switched to storing data as a dictionary (JSON object)
- Added Record validation on insert
- Added ids_only mode for efficiency/filter combination
- Began returning generators for get(), get_many(), etc.
- Jupyter changes:

  - Improved Fukushima dataset documentation
  - Added new Fukushima example for subsecting large data sets
  - Various example notebook cleanups
  - Made many improvements to notebook testing/validation

- Standardized using Sina virtual environment for non-bash shells

1.2
===
- Introduced Sina's Jupyter functionality

  - Added NOAA notebooks and converter
  - Added Fukushima notebooks and converter
  - Added getting_started notebook for kernel config

- Added FAQ and reworked documentation
- Renamed "values" to "data" for record (my_rec.data)

1.1
===
- Added Python 3 compatibility
- Added ability to store units in data entries
- Added ability to store tags for files
- Made application a required field for runs
- Streamlined deployment
- Parallelizes Cassandra ingestion
- Started batching in Cassandra ingestion
- Various QoL changes to ScalarRanges
- Added script to create tarball for use with Spack (C++)
- Switched to nlohmann JSON library (C++)


1.0
===
- Initial Release
