#!/bin/bash

python_version_file="../python/sina/__init__.py"
find_version='__VERSION__ = "(.*?)"'


# Find version assignment chunk
file_contents=$(cat "$python_version_file")
version_assignment=`grep -oP "$find_version" <<< $file_contents`

# Extract the version string
version=${version_assignment:15}
version=${version%?}

# Assemble names
versioned_dir=mnoda-"${version}"
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

# Other script(s) rely on this echo to know the name of the created file
echo ${versioned_tar}
