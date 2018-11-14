#!/bin/sh

SRC_ROOT=$HOME/siboka
SRC_DIR=$SRC_ROOT/sina

VENV=sina
VENV_ACTIVATE=$SRC_DIR/venv/bin/activate

#  Make sure that the user does not have a virtual environment currently active
#  because removing an activated virtual environment could cause problems
if [ "$VIRTUAL_ENV" -neq "" ]; then
    echo "Deactivating $VIRTUAL_ENV..."
    deactivate
fi

# Download and build the latest repository snapshot
# .. First ensure the project directory is in place
if [ ! -d $SRC_ROOT ]; then
    echo; echo "Creating missing $SRC_ROOT..."
    mkdir -p $SRC_ROOT
fi

# .. Now ensure a fresh clone of the repository
if [ -d $SRC_DIR ]; then
    echo; echo "Removing current $SRC_DIR..."
    rm -rf $SRC_DIR
fi

echo; echo "Cloning the Sina repository..."
cd $SRC_ROOT
git clone ssh://git@cz-bitbucket.llnl.gov:7999/sibo/sina.git
cd $SRC_DIR

# Leverage the existing makefile rules to set up the virtual environment,
# which is called 'venv'
make install

source $VENV_ACTIVATE

#  Create the kernel
echo; echo "Creating the $VENV kernel..."
python -m ipykernel install --prefix=$HOME/.local/ --name $VENV \
    --display-name $VENV

deactivate
