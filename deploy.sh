#!/bin/bash

# Run deployment for both C++ and Python

# IMPORTANT C++ NOTE!
# Because C++ is platform-dependent and requires setting the environment
# accordingly, this DOES NOT BUILD THE C++ and DOES NOT RUN TESTS. It creates a Spack package
# and moves it and documentation relative to where the Python is deployed.
# Run this AFTER Bamboo test jobs or AFTER a manual run of `make tests` and `make docs`.

# Converts any relative paths to absolute and ensures ending in /
CPP_DOCS=$DOC_DIR/sina/cpp
PERM_GROUP=wciuser

set -e

# Arg check
if [ $# != 3 ]
  then
    echo "Script takes exactly three arguments: <wheel_deploy_dir> <doc_deploy_dir> <examples_deploy_dir>"
    exit 1
fi

DEPLOY_DIR=`readlink -f $1`/
DOC_DIR=`readlink -f $2`/

# Do not read the link or python/deploy.sh will fail to create the example link to the latest
# examples (since it will think EXAMPLE_LINK is a directory).
EXAMPLE_LINK=$3

if [ ! -d cpp/build/docs/html ]; then
    echo "You must have run the C++ tests and built the docs"
    exit 1
fi

cd python
# Build the Sina python deployment with all the known options
./deploy.sh --build-with=cassandra,cli_tools,jupyter --deploy-dir=$DEPLOY_DIR --docs-dir=$DOC_DIR --examples-link=$EXAMPLE_LINK 

cd ../cpp
CREATED_TAR=$(sh create_spack_package.sh)
chown :$PERM_GROUP $CREATED_TAR
chmod 640 $CREATED_TAR

mv $CREATED_TAR $DEPLOY_DIR
rm -rf $CPP_DOCS
mkdir -p $CPP_DOCS
mv build/docs/html/* $CPP_DOCS
chown -R :$PERM_GROUP $CPP_DOCS
find $CPP_DOCS -type f -exec chmod 640 {} \;
find $CPP_DOCS -type d -exec chmod 750 {} \;
