Overview
========

This file summarizes the major changes in each version of Sina. For a full list,
see the commit log at:
https://lc.llnl.gov/bitbucket/projects/SIBO/repos/sina/commits?until=master

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

1.0
===
- Initial Release
