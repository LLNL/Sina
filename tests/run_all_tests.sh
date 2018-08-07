#!/bin/bash

# If not +u, virtualenv will fail
set +u

# Wheelhouse used with venv --extra-search-dir to find pip/setuptools
WHEELHOUSE=/usr/gapps/python/wheelhouse
# Comma-separated directories to ignore when doing style checks
IGNORE_STYLE=venv,docs,tests/test_venv,web,demos,.tox
# Make sure python 3 is available on LC
export PATH=/usr/apps/python-3.6.0/bin/:$PATH

# Move to correct directory
if [ ! -f setup.py ]
then
    if [ ! -f ../setup.py ]
    then
        echo "Please run test script from sina root folder"
        exit -1
    else
        EXEC_HOME=`pwd`/..
    fi
else
    EXEC_HOME=`pwd`
    pwd
fi

# Set up and activate virtual environment for testing
rm -rf $EXEC_HOME/tests/test_venv
mkdir -p $EXEC_HOME/tests/test_venv

# Default LC setuptools is too old to recognize .whls, hence extra-search-dir
python -m virtualenv --clear --extra-search-dir $WHEELHOUSE $EXEC_HOME/tests/test_venv/
source $EXEC_HOME/tests/test_venv/bin/activate

# Install packages into virtual environment
# Workaround due to overlong shebang in Bamboo agents
BIN=$EXEC_HOME/tests/test_venv/bin

# Nose installed seperately to make sure xunit's available
# Pip settings supplied by requirements.txt, etc.
python $BIN/pip install -r requirements.txt

set -e

# Perform a PEP8 style check
python $BIN/flake8 --max-line-length=99 --exclude=$IGNORE_STYLE | tee $EXEC_HOME/tests/test_venv/flake8.out
if [ -s $EXEC_HOME/tests/test_venv/flake8.out ]
then
    exit -1
fi

# Perform a documentation style check using Sphinx and autodoc
# Side effect: builds documentation
$BIN/tox -e docs

# Test building across python versions, run actual tests
# Note: if you don't have Cassandra running, Cassandra tests won't run either.
$BIN/tox
deactivate
