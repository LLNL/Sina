#!/bin/bash
#
# Sina deployment: wheel, 2 virtual environments, documentation, and examples.
#
# By default, the 2 virtual environments correspond to the system's python2 and
# python3. If you want to change this behavior, consider changing
# EXTRA_VENV_SUFFIX to fit the new behavior.
#
# The following environment variables can be used to affect the virtual
# environment that is built by the invoked Makefile:
#
#   PYTHON_3         = The Python used to build the main (Python 3) virtual env
#   PYTHON_2         = The Python used to build the Python 2 virtual env
#   SINA_PIP_OPTIONS = Additional options to pip (e.g., '--no-index')
#   VENV_OPTIONS     = Additional options when the venv is created (e.g.,
#                      '--system-site-packages' to inherit system packages

umask 027

# Valid make targets for optional build features
VALID_MAKE_TARGETS="cassandra,cli_tools,jupyter,mysql"

# Valid deployment processing steps
VALID_STEPS="clean,git,tests,venv,docs,examples"

# Default values for LC
LC_GROUP=wciuser  # Group to be given access to deployed artifacts
LC_DEPLOY_DIR=/collab/usr/gapps/wf/releases  # Release directory (also holds the usage examples)
LC_DOCS_DIR=/usr/global/web-pages/lc/www/workflow/docs  # Workflow docs
LC_EXAMPLES_LINK=/collab/usr/gapps/wf/examples  # Link to examples

# Common names
DOC_LATEST_NAME=sina  # what we should call the most recent version of the docs
VENV_SYM_NAME=sina  # symlink for venv
PYTHON_3=${PYTHON_3:-`which python3`}  # Python used for the Python 3 virtual env
PYTHON_2=${PYTHON_2:-`which python`}  # Python used for the Python 2 virtual env
PYTHON_2_SUFFIX="-py2"  # Suffix added to venvs to indicate they're for the Py2 venv

# Ensure we're running from the correct directory
if [ ! -f setup.py ]
  then
    echo "Please run this deploy script from the sina root folder"
    exit 1
fi

SOURCE_DIR=$PWD

set -e


# ---------------------------------  FUNCTIONS ---------------------------------

# Make sure directories given as args to deploy.sh exist.
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


# Deploy the documentation to $DOCS_DIR
# Creates both a versioned and unversioned ("latest") copy.
deployDocs() {
  DOC_PATH=$DOCS_DIR/$VERSION_SUBDIR
  echo; echo "Deploying documentation into $DOC_PATH..."

  if [ ! -d $DOC_PATH ]; then
    echo "Creating the documentation directory at $DOC_PATH..."
    mkdir -p $DOC_PATH
  fi

  rm -rf $DOC_PATH/*
  DOC_SOURCE=./docs/build/html
  if [ ! -d $DOC_SOURCE ]; then
    echo "Building documentation..."
    make docs
  fi
  (cd $DOC_SOURCE && mv * $DOC_PATH/)

  # Ensure permissions are set appropriately and the shortcut links to the latest
  chown -R :$PERM_GROUP $DOC_PATH

  # LC webhosting seems to have issues with symlinks, so we copy instead
  echo "Copying $DOC_PATH into $DOCS_DIR/$DOC_LATEST_NAME..."

  # Explicitly remove the old "default" vers to ensure it is replaced by the new
  rm -rf $DOCS_DIR/$DOC_LATEST_NAME
  cp -r $DOC_PATH $DOCS_DIR/$DOC_LATEST_NAME

}


# Deploy the examples. Build within $DEPLOY_DIR/examples/<version>, then make
# a link at $EXAMPLES_LINK
deployExamples() {
  EXAMPLES_SOURCE_DIR=`dirname $SOURCE_DIR`/examples
  EXAMPLES_DEST_ROOT=$DEPLOY_DIR/examples/$VERSION_SUBDIR
  echo "Deploying examples into $EXAMPLES_DEST_ROOT..."

  # Ensure the deployment directory exists
  if [ ! -d $EXAMPLES_DEST_ROOT ]; then
    mkdir -p $EXAMPLES_DEST_ROOT
    # Make sure we chown from the parent directory, which might also have been created
    chown -R :$PERM_GROUP $DEPLOY_DIR/examples
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
    # Run the script for creating the database needed for this set of examples
    # The database is created in $EXAMPLE_DEST
    bash $db_build_script $DATASET_SOURCE_DIR
    cd $SOURCE_DIR
  done
  # We'll also need to create a special folder for the advanced (untested) notebooks
  # It has no associated db, so it won't be created above
  mkdir $EXAMPLES_DEST_ROOT/advanced_tutorials
  deactivate

  # Copy the example notebooks
  for notebook in `find $EXAMPLES_SOURCE_DIR -name "*.ipynb"`; do
    if [[ $notebook == *"-checkpoint.ipynb" ]]; then
        continue  # Skip over any checkpoint files
    fi
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
  if [ "$EXAMPLES_DEST_ROOT" != "$EXAMPLES_LINK" ]; then
    echo "Linking $EXAMPLES_LINK to $EXAMPLES_DEST_ROOT..."

    # Explicitly remove the link to ensure it is replaced by the new symlink
    rm -rf $EXAMPLES_LINK
    ln -s $EXAMPLES_DEST_ROOT $EXAMPLES_LINK
  else
    echo "WARNING: Cannot create examples symlink $EXAMPLES_LINK to $EXAMPLES_DEST_ROOT"
  fi
}


# deployWheel:  Don't bother creating a shortcut or link to the latest wheel as
# it appears python will complain that it's not a valid wheel name.
deployWheel() {
  echo "Deploying the wheel into $WHEEL_DEST"

  mv -f ./dist/$WHEEL_FILENAME $WHEEL_DEST/$WHEEL_FILENAME
  chown :$PERM_GROUP $WHEEL_DEST/$WHEEL_FILENAME
}


# Usage: deployVenv <path to make venv at> <name for venv link> <python to use>
# Links to created venvs are created in $DEPLOY_DIR, extras installed are
# decided by $BUILD_OPTIONS
deployVenv() {
  VENV_DEST=$1
  VENV_LINK_NAME=$2
  PYTHON_EXEC=$3
  echo; echo "Building and deploying the virtual environment into $VENV_DEST"
  make install VENV=$VENV_DEST PYTHON=$PYTHON_EXEC
  for opt in $BUILD_OPTIONS; do
    if echo "$VALID_MAKE_TARGETS" | grep -q "$opt"; then
        make $opt VENV=$VENV_DEST PYTHON=$PYTHON_EXEC
    else
      echo "WARNING: Ignoring invalid build target since $opt not in $VALID_MAKE_TARGETS"
    fi
  done
  # Ensure that installed Sina is the new wheel (fixes permission issues)
  source $VENV_DEST/bin/activate
  # Due to Bamboo's penchant for long, deep paths, the generated pip shebang can
  # become too long for Linux to handle. Work around this by using python directly.
  python $VENV_PATH/bin/pip install --force-reinstall --no-deps $WHEEL_DEST/$WHEEL_FILENAME
  deactivate

  # Ensure permissions are set appropriately and the shortcut links to the latest
  chown -R :$PERM_GROUP $VENV_DEST

  echo "Linking $DEPLOY_DIR to $VENV_DEST..."

  # Explicitly remove the link to ensure it is replaced by the new symlink
  rm -f $DEPLOY_DIR/$VENV_LINK_NAME
  ln -sf $VENV_DEST $DEPLOY_DIR/$VENV_LINK_NAME
  chown :$PERM_GROUP $DEPLOY_DIR/$VENV_LINK_NAME
}


# Run whatever tests are associated with this deployment. Decided by
# BUILD_OPTIONS, which defaults to nothing (just run "make tests")
executeTests() {
  num_extras=${#BUILD_OPTIONS[@]}

  if [ $num_extras -le 0 ]; then
    # Run _all_ of the standard tests, including flake8, etc.
    echo; echo "Running the core tests and building docs..."
    make tests
  else
    make test-core
    make flake8
    for opt in $BUILD_OPTIONS; do
      echo
      if echo "$VALID_MAKE_TARGETS" | grep -q "$opt"; then
        # TODO: SIBO-231: Remove skipping cassandra tests once have server
        # available perform those tests.
        if [ "$opt" != "cassandra" ]; then
          echo "Running optional tests: test-$opt..."
          make test-$opt
        else
          echo "WARNING: Skipping Cassandra tests due to server issues (see SIBO-231)"
        fi
      else
        echo "ERROR: Invalid test target! $opt is not in $VALID_MAKE_TARGETS"
        exit 1
      fi
    done
  fi
}


# Provide command line options for deployment directories and optional features
# Note the equals sign between flag and value.
OPTIONS='[--build-with=<build-options>] [--deploy-dir=<deploy-dir>] [--docs-dir=<docs-dir>] [--examples-link=<examples-link>] [--group=<group>] [--help] [--skip=<skip-steps>]'

printUsage() {
  echo; echo "USAGE: `basename $0` $OPTIONS"
  echo; echo "where"
  echo "  <build-options>  Comma-separated list of optional build targets from: "
  echo "                     cassandra,cli_tools,jupyter,mysql [default='']"
  echo "  <deploy-dir>     Path to the release deployment directory, where the "
  echo "                     venv goes in that directory and the wheel in a "
  echo "                     'wheel' subdirectory [default=$LC_DEPLOY_DIR]"
  echo "  <docs-dir>       Path to the static documentation directory"
  echo "                     [default=$LC_DOCS_DIR]"
  echo "  <examples-link>  Path to the examples deployment directory symlink"
  echo "                     [default=$LC_EXAMPLES_LINK]"
  echo "  <group>          Group permissions for deployment directories"
  echo "                     [default=$LC_GROUP]"
  echo "  <skip-steps>     Comma-separated list of deployment steps to skip from:"
  echo "                     clean,git,tests,venv,docs,examples [default='']"
  exit 1
}


# ---------------------------  COMMAND LINE PROCESSING -------------------------

# Process command line options
BUILD_OPTIONS=
DEPLOY_DIR=$LC_DEPLOY_DIR
DOCS_DIR=$LC_DOCS_DIR
EXAMPLES_LINK=$LC_EXAMPLES_LINK
PERM_GROUP=$LC_GROUP
SKIP_STEPS=

for arg in "$@"; do
  option=${arg%%=*}
  value=${arg##*=}
  case "$option" in
  --build-with) BUILD_OPTIONS=$(echo $value | tr "," "\n");;
  --deploy-dir) DEPLOY_DIR=$value;;
  --docs-dir) DOCS_DIR=$value;;
  --examples-link) EXAMPLES_LINK=$value;;
  --group) PERM_GROUP=$value;;
  --help) printUsage; exit 0;;
  --skip) SKIP_STEPS=$(echo $value | tr "," "\n");;
  *) echo "ERROR: Unrecognized option $arg" && exit 1;;
  esac
done

# Ensure arguments are reasonable
checkDirectory deployment $DEPLOY_DIR
DEPLOY_DIR=`realpath $DEPLOY_DIR`

checkDirectory documentation $DOCS_DIR
DOCS_DIR=`realpath $DOCS_DIR`

HAVE_GROUP=`grep "^$PERM_GROUP:" /etc/group`
if [ "$HAVE_GROUP" == "" ]; then
  echo "ERROR: Group '$PERM_GROUP' does not exist.  Provide a valid group."
  printUsage
  exit 1
fi

# Set up some globals to ensure they are available across deployment steps.

# Ensure wheel destination is available across deployment steps
# If it doesn't exist, warn and quit
WHEEL_DEST=$DEPLOY_DIR/wheels
[ ! -d "$DEPLOY_DIR/wheels" ] && echo "ERROR: $DEPLOY_DIR doesn't contain a 'wheels' folder." && exit 1

# The path for the latest docs and examples is "sina-<version>" in order to
# continue to allow "sina" to be used as a symlink to the latest version.
VERSION_SUBDIR=sina-`grep VERSION ./sina/__init__.py | sed 's/[^0-9.]//g'`


# ----------------------------  DEPLOYMENT PROCESSING --------------------------

# clean: Ensure a "clean" build space (based on the current branch assuming it
#        may include more items to remove than master)
if [[ ! "${SKIP_STEPS[@]}" =~ "clean" ]]; then
  echo; echo "Removing all generated files to ensure a 'clean' build..."
  make clean
fi

# git: Ensure using the master branch, which is assumed to be available in the
#      current directory.
if [[ ! "${SKIP_STEPS[@]}" =~ "git" ]]; then
  echo; echo "Ensuring working with the latest git master branch..."
  git checkout master
  git pull
fi

# tests: Ensure tests are successful before proceeding (also build docs)
if [[ ! "${SKIP_STEPS[@]}" =~ "tests" ]]; then
  executeTests
else
  if [[ ! "${SKIP_STEPS[@]}" =~ "docs" ]]; then
    make docs
  fi
fi

# wheel: Build and deploy the wheel, making sure to expose the wheel filename
#        for virtual environment directory purposes.
make wheel
WHEEL_FILENAME=`ls ./dist/*.whl | cut -d / -f3`
deployWheel

# venv: Build and deploy the virtual environment using the wheel name as the
#       basis for the directory name.
if [ "$WHEEL_FILENAME" != "" ]; then
  # Need the virtual environment path for deploying examples
  VENV_PATH=$DEPLOY_DIR/`basename $WHEEL_FILENAME .whl`
  if [[ ! "${SKIP_STEPS[@]}" =~ "venv" ]]; then
      deployVenv $VENV_PATH $VENV_SYM_NAME $PYTHON_3
      deployVenv $VENV_PATH$PYTHON_2_SUFFIX $VENV_SYM_NAME$PYTHON_2_SUFFIX $PYTHON_2
  fi
else
  echo "ERROR: The wheel file could not be found. Did it fail to build?"
  exit 1
fi

# docs: Deploy the generated documentation
if [[ ! "${SKIP_STEPS[@]}" =~ "docs" ]]; then
  deployDocs
fi

# examples: Deploy built-in examples
if [[ ! "${SKIP_STEPS[@]}" =~ "examples" ]]; then
  deployExamples
fi

echo "DONE"
