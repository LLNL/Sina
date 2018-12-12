#!/bin/bash

# Run deployment for both C++ and Python

# IMPORTANT C++ NOTE!
# Because C++ is platform-dependent and requires setting the environment
# accordingly, this DOES NOT BUILD THE C++ and DOES NOT RUN TESTS. It creates a Spack package
# and moves it and documentation relative to where the Python is deployed.
# Run this AFTER Bamboo test jobs or AFTER a manual run of `make tests` and `make docs`.

# Converts any relative paths to absolute and ensures ending in /
DEPLOY_DIR=`greadlink -f $1`/
DOC_DIR=`greadlink -f $2`/
EXAMPLE_DIR=`greadlink -f $3`/
CPP_DOCS=$DOC_DIR/sina/cpp

set -e
if [ ! "$(ls -A cpp/build/docs)" ]; then
    echo "You must have run the C++ tests and built the docs"
    exit -1
fi

cd python
./deploy.sh $DEPLOY_DIR $DOC_DIR $EXAMPLE_DIR

cd ../cpp
CREATED_TAR=$(sh create_spack_package.sh)

mv $CREATED_TAR $DEPLOY_DIR
rm -rf $CPP_DOCS
mkdir -p $CPP_DOCS
mv build/docs $CPP_DOCS
