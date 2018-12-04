#!/bin/sh

printUsage() {
    echo; echo "USAGE:  `basename $0` <Jupyter kernel name> <kernel path>"
    echo; echo "where"
    echo "  <Jupyter kernel name> is the internal and display name for"
    echo "      the virtual environment associated with the kernel."
    echo "  <kernel path> is the path to install the kernel at."
    exit 1
}

if [$# -ne 2]; then
    echo "ERROR: The Jupyter kernel name and path are required."
    printUsage
fi

if [ -z "$VIRTUAL_ENV" ]; then
    echo "ERROR: You must first activate the associated virtual environment."
    exit 1
fi

#  Create the kernel
echo; echo "Creating the $1 kernel at $2..."
python -m ipykernel install --prefix=$2 --name $1 --display-name $1
