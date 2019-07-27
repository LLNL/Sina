#!/bin/bash

# Find version assignment chunk
python_version_file="../python/sina/__init__.py"
find_version='__VERSION__ = "(.*?)"'
version_assignment=`grep -oP "$find_version" $python_version_file`

# Extract the version string
version=${version_assignment:15}
version=${version%?}

# Assemble names
versioned_dir=sina-cpp-"${version}"
versioned_tar=${versioned_dir}.tgz

set -e
mkdir ${versioned_dir}
cd ${versioned_dir}
ln -s ../CMake .
ln -s ../CMakeLists.txt .
ln -s ../README.md .
ln -s ../blt .
ln -s ../src .
ln -s ../include .
ln -s ../test .
cd ..
tar --exclude="${versioned_dir}/blt/.git" -czhf ${versioned_tar} ${versioned_dir}
rm -fr ${versioned_dir}

# ../deploy.sh relies on this echo to know the name of the created file
echo ${versioned_tar}
