#!/bin/bash

# Skip error and exit when expanding unset variables and parameters; otherwise,
# virtualenv will fail
set +u

# Exit immediately if a command exits with a non-zero status
set -e

# Wheelhouse used with venv --extra-search-dir to find pip/setuptools
WHEELHOUSE=/usr/gapps/python/wheelhouse
# Make sure python 3 is available on LC
export PATH=/usr/apps/python-3.6.0/bin/:$PATH

# Move to correct directory
if [ ! -f setup.py ]
then
    if [ ! -f ../setup.py ]
    then
        echo "Please run test script from sina python folder"
        exit -1
    else
        EXEC_HOME=`pwd`/..
    fi
else
    EXEC_HOME=`pwd`
    pwd
fi

# Set up and activate virtual environment for testing
TEST_VENV=$EXEC_HOME/tests/test_venv

rm -rf $TEST_VENV
mkdir -p $TEST_VENV

# Default LC setuptools is too old to recognize .whls, hence extra-search-dir
python -m virtualenv --clear --extra-search-dir $WHEELHOUSE $TEST_VENV

# Install packages into virtual environment
# workaround due to overlong shebang in Bamboo agents
TEST_BIN=$TEST_VENV/bin
source $TEST_BIN/activate

# Nose installed separately to make sure xunit's available
# Pip settings supplied by setup.py (implicit) and requirements.txt.
# Manually add links.txt until I modify the Makefile to take in the VENV.
ln -sf lc-links.txt requirements/links.txt
python $TEST_BIN/pip install -r requirements/development.txt

# Test building across python versions, run actual tests
# Note: if you don't have Cassandra running, Cassandra tests won't run either.
$TEST_BIN/tox

deactivate
