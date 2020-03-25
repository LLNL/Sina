#!/bin/bash

# Run deployment for both C++ and Python

# IMPORTANT C++ NOTE!
# Because C++ is platform-dependent and requires setting the environment
# accordingly, this DOES NOT BUILD THE C++ and DOES NOT RUN TESTS. It creates a Spack package
# and moves it and documentation relative to where the Python is deployed.
# Run this AFTER Bamboo test jobs or AFTER a manual run of `make tests` and `make docs`.

set -e

# Arg check
if [ $# != 3 ]
  then
    echo "This toplevel script requires exactly 3 positional args; the
python-only deploy can take named args. Usage: <DEPLOY_DIR> <DOC_DIR> <EXAMPLE_LINK>"
    exit 1
fi

# Convert any relative paths to absolute and standardize ending in /
DEPLOY_DIR=`realpath $1`/
DOC_DIR=`realpath $2`/
# EXAMPLE_DIR is a symlink, so no ending /
EXAMPLE_LINK=`realpath --no-symlinks $3`
CPP_DOCS=$DOC_DIR/sina/cpp
PERM_GROUP=wciuser

if [ ! -d cpp/build/docs/html ]; then
    echo "You must have run the C++ tests and built the docs"
    exit 1
fi

cd python
# Build the Sina python deployment with all the known options
# NOTE: Cython currently fails on Python 3.7. This is addressed in the Bamboo job (sets python to use 3.6.4).
./deploy.sh --build-with=cassandra,cli_tools,jupyter --deploy-dir=$DEPLOY_DIR --docs-dir=$DOC_DIR --examples-link=$EXAMPLE_LINK --skip=git
echo "Python deployment complete! Continuing to C++ portion..."

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
