Overview
========

This file summarizes the major changes in each version of Sina. For a full list,
see the commit log at:
https://lc.llnl.gov/bitbucket/projects/SIBO/repos/sina/commits?until=master

1.13
===========
- Overhauled documentation
    - Many topics are now covered in the form of Jupyter notebooks, which are run and distributed as part of the documentation
    - Outdated guides removed, new ones added, etc.
    - Reworked tutorial flow to be more user-friendly
    - Added intro to ToC to help orient users
- Removed restrictions that enforce Python 2 build compatibility
    - Sina itself is still compatible with Python 2, but the special build rules that bound it to older software versions to maintain 2 compatibility have been lifted.
- Added C++ Record function to merge another Record in as library_data (useful for host codes)
- Added new dimensions for histogram (2D "Heatmap") and scatter plot (optional z and colorbar)
- Added new visualizations, such as violin and CDF plots
- Fixed a bug wherein a visualizer would not properly pass down its id_pool
- QoL for operating on individual records (namely Record.to_file for single Record post-processing).

1.12
============
- Added a visualization module, sina.visualization, that creates matplotlib visualizations directly from Sina DataStores
    - Includes interactive mode for live configuration of data
    - Initial module includes scatter plots, line plots, histograms, and surface plots
    - For full features and functionality, see documentation
- Added ways to simplify access to the values of data and curves via
  attribute-style and subscript-style access to Records.

    - `sina.model.Record.data_values` allows direct access to data items.
      For example, you can write `my_field = my_record.data_values.my_field` to
      access the value of `my_field`.
    - `sina.model.Record.curve_set_values` allow direct access to curve sets.
      For example, `my_record.curve_set_values.my_curve_set.temperature = [1, 2, 3]`
      sets the values for `temperature` in curve set `my_curve_set`.
- Added new query: DataStore.records.get_curve_set_names()
- Added filter_constants to DataStore.records.data_names(): filters out data whose values don't change between Records
- Improved usage of DataStore.records.find() with a large id_pool 
- Made update() properly available as DataStore.records.update()
- Reduced max string column size to 15k to fit updated LC row length requirements
- Updated documentation, including fix to schema docs and example of loading Records from multiple files
- Fixed a bug wherein update() calls would not delete removed attributes
- Fixed a bug where 0 was treated as false in DataRanges
- Explicitly remove local_id field from ingested Records 
- Various internal test/build improvements, such as correct deallocation of node post-test 

1.11
====
- Added load_records() and load_sole_record() functions.
- Added QoL for CurveSets and Curves
- Improved functionality of find():
    - Functionality with no filters specified
    - mimetype filter
- Added initial support for query negation logic
    - Added NOT functionality for type queries
- Fixed a memory leak in AdiakWriter
- Made DAO protected in data stores
- Fixed issue with update() where Relationships weren't preserved
- Fixed issue with DataRange handling of zero in SQL

1.10
====
- Added a new section to Records, library_data
- Added a new query, find(), which unifies several existing queries
- Added sina.connect(), which introduces read-only datastores
- Added the ability to delete all contents of a datastore
- Added a function for deleting Files from Records
- Added id_pool support to several existing queries
- Fix several misc. Cassandra bugs
- Expanded URI query to utilize has_any and has_all

1.9.5
=====
- Fixed a bug in C++ add() methods
- Set version of importlib_metadata for compatibility with python2
- Improve docs and test for update() routine
- Add a basic QoL method for updating Records
- Make deployed tarball contain config folder and deploy to cpp_releases

1.9.4
=====
- Fixed parsing of scalar names with slashes in C++
- Added Relationship deletion function
- Fixed a bug involving dropped inserts when mass-inserting Relationships in Cassandra
- Added integration tests for C++ and Python
- Made version number readable through C++

1.9.3
=====
- Fixed a bug which prevented parsing of large json blocks from the database
  when using python 2.7.
- Increased allowed URI length for SQL file entries

1.9.2
=====
- Removed restriction on the same name being used for a data item and the
  name of a curve in a curve set.
- Fixed a bug that allowed invalid records to be inserted into the database.
- Added a method to retrieve invalid records from the database.
- Sped up processing of JSON files.

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
