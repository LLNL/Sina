#!/bin/bash
#
# Sina deployment: wheel, virtual environment, documentation, and examples.
#
# The following environment variables can be used to affect the virtual
# environment that is built:
#
#   PYTHON           = Specify non-default python (e.g., python3)
#   SINA_PIP_OPTIONS = Additional options to pip (e.g., '--no-index')
#   VENV_OPTIONS     = Additional options when the venv is created (e.g.,
#                        '--system-site-packages' to inherit system packages

umask 027

# Valid make targets for optional build features
VALID_MAKE_TARGETS="cassandra,cli_tools,jupyter"

# Default values for LC
LC_GROUP=wciuser  # Group to be given access to deployed artifacts
LC_DEPLOY_DIR=/collab/usr/gapps/wf/releases  # Release directory
LC_DOCS_DIR=/usr/global/web-pages/lc/www/workflow/docs  # Workflow docs
LC_EXAMPLES_DIR=/collab/usr/gapps/wf/examples  # Backward compatible examples dir link

# Common names
DOC_SYM_NAME=sina # symlink for the documentation subdirectory
VENV_SYM_NAME=sina # symlink for venv

# Ensure we're running from the correct directory
if [ ! -f setup.py ]
  then
    echo "Please run this deploy script from the sina root folder"
    exit 1
fi

SOURCE_DIR=$PWD

# Now that the options have been established, proceed with deployment setup.
set -e


# ---------------------------------  FUNCTIONS ---------------------------------

checkDirectory() {
  # $1=directory description, $2=directory path
  if [ ! -z "$2" ]; then
    if [ ! -d $2 ]; then
      echo "ERROR: Expected $1 directory '$2' to exist."
      printUsage
      exit 1
    fi
  else
    echo "ERROR: Expected the $1 directory option to have a value."
    printUsage
    exit 1
  fi
}

deployDocs() {
  DOC_PATH=$DOCS_DIR/$VERSION_SUBDIR
  echo "Deploying documentation into $DOC_PATH..."

  if [ ! -d $DOC_PATH ]; then
    echo "Creating the documentation directory at $DOC_PATH..."
    mkdir -p $DOC_PATH
  fi

  # The documentation is currently built during testing so just use those results
  rm -rf $DOC_PATH
  mv ./docs/build/html $DOC_PATH

  # Ensure permissions are set appropriately and the shortcut links to the latest
  chown -R :$PERM_GROUP $DOC_PATH
  ln -sf $DOC_PATH $DOCS_DIR/$DOC_SYM_NAME
}

deployExamples() {
  EXAMPLES_SOURCE_DIR=`dirname $SOURCE_DIR`/examples
  EXAMPLES_DEST_ROOT=$DEPLOY_DIR/examples/$VERSION_SUBDIR
  echo "Deploying examples into $EXAMPLES_DEST_ROOT..."

  # Ensure the deployment directory exists
  if [ ! -d $EXAMPLES_DEST_ROOT ]; then
    mkdir -p $EXAMPLES_DEST_ROOT
  fi

  # Build the example databases
  echo "Activating the virtual environment in $VENV_PATH..."
  source $VENV_PATH/bin/activate

  for db_build_script in `find $EXAMPLES_SOURCE_DIR -name build_db.sh`; do
    DATASET_SOURCE_DIR=$(dirname $db_build_script)
    DATASET_NAME=$(basename $DATASET_SOURCE_DIR)
    EXAMPLE_DEST=$EXAMPLES_DEST_ROOT/$DATASET_NAME
    if [ ! -d $EXAMPLE_DEST ]; then
      mkdir -p $EXAMPLE_DEST
    else
      rm -rf $EXAMPLE_DEST/*
    fi
    echo "Building $DATASET_NAME database in $EXAMPLE_DEST..."
    cd $EXAMPLE_DEST 
    bash $db_build_script $DATASET_SOURCE_DIR
    cd $SOURCE_DIR
  done
  deactivate

  # Copy the example notebooks
  for notebook in `find $EXAMPLES_SOURCE_DIR -name "*.ipynb"`; do
    DATASET_NAME=$(basename $(dirname "$notebook"))
    NOTEBOOK_NAME=$(basename "$notebook")
    if [ "$DATASET_NAME" == "examples" ]
    then
        # it's a "top-level" notebook like getting_started
        NOTEBOOK_DEST=$EXAMPLES_DEST_ROOT/$NOTEBOOK_NAME
    else
        NOTEBOOK_DEST=$EXAMPLES_DEST_ROOT/$DATASET_NAME/$NOTEBOOK_NAME
    fi
    cp "$notebook" $NOTEBOOK_DEST
  done

  # Ensure permissions are set appropriately and the shortcut links to the latest
  chown -R :$PERM_GROUP $EXAMPLES_DEST_ROOT
  ln -sf $EXAMPLES_DEST_ROOT $EXAMPLES_DIR
}

# deployWheel:  Don't bother creating a shortcut or link to the latest wheel as
# it appears python will complain that it's not a valid wheel name.
deployWheel() {
  WHEEL_DEST=$DEPLOY_DIR/wheels
  echo "Deploying the wheel into $WHEEL_DEST..."

  mv -f ./dist/$WHEEL_FILENAME $WHEEL_DEST/$WHEEL_FILENAME
  chown :$PERM_GROUP $WHEEL_DEST/$WHEEL_FILENAME
}

deployVenv() {
  echo "Building and deploying the virtual environment into $VENV_PATH"
  make install VENV=$VENV_PATH
  for opt in $BUILD_OPTIONS; do
    if echo "$VALID_MAKE_TARGETS" | grep -q "$opt"; then
        make $opt VENV=$VENV_PATH
    else
      echo "WARNING: Ignoring invalid build target since $opt not in $VALID_MAKE_TARGETS"
    fi
  done

  # Ensure permissions are set appropriately and the shortcut links to the latest
  chown -R :$PERM_GROUP $VENV_PATH
  ln -sf $VENV_PATH $DEPLOY_DIR/$VENV_SYM_NAME
}

# SIBO-231: Removed statements skipping cassandra tests once have server available
# to perform the tests.
executeTests() {
  echo "Running the core tests and building docs..."
  make test-core
  for opt in $BUILD_OPTIONS; do
    if echo "$VALID_MAKE_TARGETS" | grep -q "$opt"; then
      if [ "$opt" != "cassandra" ]; then
        echo "Running optional tests: test-$opt..."
        make test-$opt
      else
        echo "WARNING: Skipping Cassandra tests due to server issues (see SIBO-231)"
      fi
    else
      echo "WARNING: Ignoring invalid test target since $opt not in $VALID_MAKE_TARGETS"
    fi
  done
}

# Provide command line options for deployment directories and optional features
OPTIONS='[--build=<options>] [--deploy-dir=<deploy>] [--docs-dir=<docs>] [--examples-dir=<examples>] [--group=<group>] [--no-master]'

printUsage() {
  echo; echo "USAGE: `basename $0` $OPTIONS"
  echo; echo "where"
  echo "  <deploy>     Path to the release deployment directory, where the venv "
  echo "                 goes in that directory and the wheel in a 'wheel'"
  echo "                 subdirectory [default=$LC_DEPLOY_DIR]"
  echo "  <docs>       Path to the static documentation directory"
  echo "                 [default=$LC_DOCS_DIR]"
  echo "  <examples>   Path to the examples deployment directory symlink"
  echo "                 [default=$LC_EXAMPLES_DIR]"
  echo "  <group>      Group permissions for deployment directories"
  echo "                 [default=$LC_GROUP]"
  echo "  <options>    Comma-separated list of make targets for optional build features from: "
  echo "                 cassandra, cli_tools, and jupyter"
  echo "                 [default='']"
  echo "  --no-master  Do not check out and update the master branch"
  exit 1
}


# ---------------------------  COMMAND LINE PROCESSING -------------------------

# Process command line options
BUILD_OPTIONS=
DEPLOY_DIR=$LC_DEPLOY_DIR
DOCS_DIR=$LC_DOCS_DIR
EXAMPLES_DIR=$LC_EXAMPLES_DIR
PERM_GROUP=$LC_GROUP
USE_MASTER=1

for arg in "$@"; do
  option=${arg%%=*}
  value=${arg##*=}
  case "$option" in
  --option) BUILD_OPTIONS=$(echo $value | tr "," "\n");;
  --deploy-dir) DEPLOY_DIR=$value;;
  --docs-dir) DOCS_DIR=$value;;
  --examples-dir) EXAMPLES_DIR=$value;;
  --group) PERM_GROUP=$value;;
  --no-master) USE_MASTER=0;;
  *) echo "WARNING: Ignoring unrecognized option: $arg";;
  esac
done

# Ensure arguments are reasonable
checkDirectory deployment $DEPLOY_DIR
DEPLOY_DIR=`readlink -f $DEPLOY_DIR`

checkDirectory documentation $DOCS_DIR
DOCS_DIR=`readlink -f $DOCS_DIR`

# Don't check the EXAMPLES_DIR for existence since it is [to be] a symlink
EXAMPLES_DIR=`readlink -f $EXAMPLES_DIR`

HAVE_GROUP=`grep "^$PERM_GROUP:" /etc/group`
if [ "$HAVE_GROUP" == "" ]; then
  echo "ERROR: Group '$PERM_GROUP' does not exist.  Provide a valid group."
  printUsage
  exit 1
fi


# ----------------------------  DEPLOYMENT PROCESSING --------------------------

# Ensure using the master branch, which is assumed to be available in the
# current directory.
if [ USE_MASTER -eq 1 ]; then
  echo "Ensuring working with the latest git master branch..."
  git checkout master
  git pull
else
  echo "Working as-is with the current git branch..."
fi

# Ensure we have a "clean" repository
echo "Removing all generated files to ensure a 'clean' build..."
make clean

# Ensure the [master branch] tests are successful before proceeding
# TODO: Uncomment the following and resume testing once the jupyter
#  "raw_input was called ... StdinNotImplementedError..." (see SIBO-783).
# and remove 'make docs'.
echo "WARNING: Skipping test execution until SIBO-783 is resolved"
#executeTests
make docs

# Build and deploy the wheel, making sure to expose the wheel filename for virtual
# environment directory purposes.
make wheel
WHEEL_FILENAME=`ls ./dist/*.whl | cut -d / -f3`
deployWheel

# Build and deploy the virtual environment using the wheel name as the basis
# for the directory name.
VENV_PATH=$DEPLOY_DIR/`basename $WHEEL_FILENAME .whl`
deployVenv

# Build and deploy documentation and examples using sina version numbers
# (Note that 'sina' is prepended to the version for backward compatibility
#  since it has been used as the root and symlink for the latest versions
#  of the docs and virtual environment.)
VERSION_SUBDIR=sina-`grep VERSION ./sina/__init__.py | sed 's/[^0-9.]//g'`

deployDocs
deployExamples

echo "DONE"
