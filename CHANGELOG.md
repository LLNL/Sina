Overview
========

This file summarizes the major changes in each version of Sina. For a full list,
see the commit log at:
https://lc.llnl.gov/bitbucket/projects/SIBO/repos/sina/commits?until=master

1.9.1
=====
- Added infrastructure for PyPI release
- Added hotfix to properly recognize sqlite :memory: dbs.

1.9
===
- Enhanced API by adding new higher-level DataStore class to hide DAOs
- Added curve sets
- Improved MySQL pooling behavior for many-node setups
- Added new queries (get all records, check if record exists)
- Improved efficiency of get() for large lists
- Made C++ tests optional and off by default, other minor build improvements

1.8
===
- Improved SQL support for long string data
- Changed C++ component to write JSON with Conduit instead of nlohmann_json
- Add querying on mimetype
- Fixed bug with building C++ component on OSX
- Fixed bug preventing insertion of empty lists

1.7
===
- Added support for MySQL access
- Improved support for Sonar machines
- Updated tutorial resources and README
- Overhauled storage of scalar lists
- Merged functions with "_many()" variants
  - Instead of ex: insert_many(my_list), use insert(my_list))
- Bugfixes

1.6
===
- Added support for Adiak to Sina C++
- Made Sina compatible with Python 3.7
- Added get_available_types(), get_having_min(), and get_having_max()
- added set_data() and related Record QoL methods
- Renamed Mnoda JSON to Sina JSON

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
