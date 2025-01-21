Contents
========
- Overview
- LC Setup
- Standard Setup
- Manual Setup

    - Creating the Environment
    - Installing Software Dependencies

- Activating and Deactivating the Virtual Environment
- Using the Example Notebooks and Datasets
- Testing
- Supported Environments
- Database Support


Overview
========

Sina's Python component is a tool for making simulation (meta)data collection
and exploration simple.

It works by collecting information from code runs, logs, and other outputs into
a common file format which can then be passed off to one of Sina's supported
backends, all of which are queried using the same user-friendly Python API. To the
end user, this means that important data can be accessed through Python scripts,
GUIs (Jupyter notebooks) etc. with all the speed of a database and none of the
complexity (the user never has to interact with database architecture), nor any of
the traditional headaches of parsing logs or remembering which file contains what.

Sina is integrated into a number of LLNL physics codes to capture simulation data;
look for the _sina.json! If your code isn't configured to output Sina, but you'd
like it to be, we may be able to work with the code team to integrate it--you can reach
us at weave-support@llnl.gov, or check out the WEAVE project on Gitlab and Teams.

The instructions below will guide you through setting up a virtual environment for
Sina (or installing it in one that already exists), running example notebooks, and
getting dependencies for your backend(s) of choice. Note that SQL
will always be available as the "default" backend. Once you're done with setup,
a quickstart tutorial can be found in notebook form at
<sina_root>/examples/basic_usage.ipynb.

Remember that, if you're on LC, each time you log in you'll first need to activate the
environment. When you're done, we recommend you deactivate the virtual environment to get
back to your default environment or end your session.


LC Setup
========

If you're on an LC machine, you can use a virtual environment with dependencies
already installed::

    $ source /collab/usr/gapps/wf/releases/sina/bin/activate

The above is for bash; other activation scripts, e.g. activate.csh, can be found
in the same directory.

Sina will now be available for use via Python virtual environment, and can be
tested with `sina -h` (which should display a help message). When you're done,
use `deactivate` to exit the virtual environment. Note that this will be the release
(master) Sina version--if you want to use Sina Develop, keep reading!

If you run into issues with the LC virtual environment, please email us at weave-support@llnl.gov.


Standard Non-LC Setup
=====================

Sina is available on PyPi::

    $ pip install llnl-sina

However, this will only give you access to the release version! Non-release
versions are not available externally. Internal users looking to use our development
version, or wanting to contribute to Sina, clone us from CZ Gitlab. External
contributors should clone us from the LLNL Github.

After cloning, cd to the python folder. Standard installation, provided by the Makefile,
is initiated by entering the following at the command line::

    $ make

This command creates the virtual environment, installs \(missing\) dependencies,
and installs Sina.

You can build the documentation, which will appear in `build/docs`, using::

    $ make docs

Tests are run by entering::

    $ make tests

Alternatively, you can run all of the above by entering the following::

    $ make all

This will install Sina with its default backend (SQL).

Once installation is complete, you are ready to activate the environment -- see
"Activating the Virtual Environment" -- and begin using Sina. You can also install
the optional Cassandra backend with::

    $ make cassandra

Additional command line tools (such as diffing Records) are available with::

    $ make cli-tools


Manual Setup
============

You will need to create, activate, and install software dependencies in your
environment.


Creating the Environment
------------------------
Enter the following command to set up your initial environment::

    $ python -m virtualenv venv   # venv can be any name you want

Now activate the environment \(see "Activating the Virtual Environment"\).

You need to be in the proper Sina directory before proceeding to install
dependencies, so enter the following command::

    (venv) $ cd $SINA_PYTHON

where `SINA_PYTHON` is the `python` subdirectory of the Sina source code.


Installing Software Dependencies
--------------------------------
You first need to make sure there is a requirements/links.txt file that contains
the appropriate link constraints.  There are two requirements files containing
flags and links used in our supported environments::

- requirements/lc-links.txt
- requirements/no-links.txt

The first file contains the options needed to restrict packages to those
available on the wheelhouse hosted on the Open Computing Facility (OCF) at
Lawrence Livermore National Laboratory.  The second file contains no flags.
The links.txt file is included in other requirements files to ensure the
options are consistent for the build and testing processes. The makefile will create a
softlink to the appropriate file; if you're doing this manually, you'll need to
link requirements/links.txt to the appropriate file yourself.

Once you've set up your requirements/links.txt, you can use our dev requirements
file (<sina_root>/python/requirements/development.txt) to install
basic Sina dependencies::

    $(venv) pip install -r requirements/development.txt


The requirements file should install the package in editable mode but, if
not, run::

    $(venv) pip install -e .


Activating and Deactivating the Virtual Environment
===================================================
Enter the following command to enter the virtual environment::

    $ source $SINA_PYTHON/venv/bin/activate  # use activate.csh if in a [t]csh

where `SINA_PYTHON` is the python subdirectory of the Sina source code.
You will need to do this every time you want to start up a session in the named
virtual environment. You can test Sina's available with::

    (venv) $ sina --version

Enter the following command to deactivate the virtual environment::

    (venv) $ deactivate

when you are done.


Using the Example Notebooks and Datasets
========================================

Sina contains tutorials in the form of Jupyter notebooks.
Files are stored in the examples directory (found in the
sina root folder alongside the python and cpp folders), and are organized by
dataset, with data_overview.rst containing descriptions of each set.
To use the notebooks, you'll first need to run getting_started.ipynb
(also in the examples directory) from the LC Jupyter server at
lc.llnl.gov/jupyter. This will create a Jupyter kernel from your current virtual
environment, making anything installed in it available to the notebook.
After that, you'll be ready to run the rest of the
notebooks. If you're not working on LC, you can also set Jupyter up locally:
run `make Jupyter` from the python folder, then `jupyter notebook`. This will
open a webpage similar to what you'd see accessing LC's Jupyter server.

Most notebooks rely on sample datasets. Pre-built sets are deployed
with Sina to the LC, but you can build them locally as well to experiment with
Sina. Go into any dataset folder (the NOAA set is well-sized for experimentation)
and `./build_db.sh`. Note that you'll need Sina available to do so, see the
section on virtual environments.

To clean all output from the notebooks::

    (venv) $ make clean-notebooks


Testing
=======

This package uses pytest to run unit tests.  Enter the following while in
your virtual environment::

    (venv) $ pytest

Additional tests, which include checks for PEP8 compliance and proper
documentation, can be run my entering the following::

    $ make tests

This command will set up and enter the necessary virtual environment.


Supported Environments
======================

Sina is regularly tested in the following environments:

- **OSX 10.15**: Primary development environment for most team members.
  If you are not on the LC network, be sure to comment out `--no-index` in the
  requirements file.
- **TOSS 3, RedHat 7.4 (quartz, rzsonar)**: Automated testing environment
- **TOSS 3, RedHat 7.5 (catalyst, rztopaz)**: Secondary development environment

Absence is not an indication that Sina will not work; please consider expanding this list!


Database Support
================

Out-of-the-box, Sina does not install drivers for relational databases other
than SQLite. If you wish to connect to other databases (e.g. MySQL, MariaDB,
or Oracle), you need to install the appropriate drivers for that database.
You can do this with our Makefile::

    $ make mysql

After you install the connector, you can connect to these types of databases
from the command line tools::

    $ sina ingest --database-type=sql --database "mysql+mysqlconnector://host:port/?read_default_file=~/.my.cnf"

You can also connect with the programmatic API::

    factory = DAOFactory("mysql+mysqlconnector://host:port/?read_default_file=~/.my.cnf")
