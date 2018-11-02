#!/bin/sh

printUsage() {
    echo; echo "USAGE:  `basename $0` <Jupyter kernel name>"
    echo; echo "where"
    echo "  <Jupyter kernel name> is the internal and display name for"
    echo "      the virtual environment associated with the kernel."
    exit 1
}

if [ -z "$1" ]; then
    echo "ERROR: The Jupyter kernel name is required."
    printUsage
fi

if [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: You must first activate the associated virtual environment."
    exit 1
fi

#  Create the kernel
echo; echo "Creating the $1 kernel..."
python -m ipykernel install --prefix=$HOME/.local/ --name $1 --display-name $1
