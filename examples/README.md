Open Data and Open Source Examples
==================================

Contents
========

- Introduction

- Additions

  - Required Files
  - Naming Conventions
  - Converter or Ingestor
  - README
  - Build Script


Introduction
============

This directory contains examples based on open data and, eventually, data
derived from executing open source simulations.  Scripts and notebooks for 
each example are maintained in separate subdirectories.  Key features of each 
dataset are summarized in the table below.

| Example   | Database | Record Type(s) | Total Records | Total Relationships |
|:----------|:--------:|:---------------|:-------------:|:-------------------:|
| Fukushima | SQLite   | Custom         | 32,445        | 32,436              |
| NOAA      | SQLite   | Custom         | 1,527         | 1,520               |


Additions
=========

Adding examples to this repository, especially those involving simulation data
is encouraged.  Each example based on a new dataset should be placed in a 
subdirectory named after the dataset and provide a minimum set of files that 
adhere to the specified naming conventions to facilitate sharing, automated 
regression testing, and automated deployment.

Required Files
--------------

The following set of files shall be required within the dataset subdirectory
for each new dataset example:

1. dataset converter/ingestor (see *Naming Convention* section);
1. README.md file (see *README* section);
1. build_db.sh (see *Build Script* section); and
1. at least one example Python or Jupyter Notebook script illustrating at least one database query.


Naming Conventions
------------------

Facilitating sharing of individual example files outside of the context of 
repository clones involves ensuring that converters and example scripts
include the name of the dataset on which they operate.  So each 
The directory name shall be the name of the dataset and the names of associated
converters, ingestors, and example scripts shall start with the name of the
dataset.  

Furthermore, the name of each converter script shall conform to the convention
of `dataset_sourcetype2desttype.py`, where `dataset` is replaced with the name 
of the dataset and `sourcetype` is replaced with the type of file being 
converted (e.g., `csv`).  For example, `fukushima_csv2mnoda.py` identifies the 
script as a converter for the fukushima dataset.  It also indicates the data 
extracted from a `CSV` file is converted to a `Mnoda` file.


Converter or Ingestor
---------------------

There shall be a script that takes the raw source data and either converts it
to a Mnoda file for subsequent ingestion into a database or performs the
ingestion directly.  Be sure to comply with the naming convention described
in the *Naming Conventions* section.


README
------

Each example is required to have a README.md file that includes:

1. Describe the dataset;
1. Describe the records extracted from the dataset;
1. Describe the process for building the database; and
1. List references that include attribution to the source of the data.

*It is critical that the README.md file includes appropriate attribution.*
For Open datasets, this mean there is a URL to the data source.  Data
derived by running Open Source applications, such as Lawrence Livermore 
Laboratory's Proxy applications, include the appropriate attribution.  For 
example, a dataset based on running Lulesh must have a README.md file that
includes the LLNL-CODE-461231 release number.


Build Script
------------

The build script is intended for automated deployment to a shared space on 
Lawrence Livermore National Laboratory's Livermore Computing systems to 
allow potential users to explore the data using the example notebooks.
Each script shall automate the process of data extraction, Mnoda file
creation (optional), and database creation.



Updated: 02/28/2019
