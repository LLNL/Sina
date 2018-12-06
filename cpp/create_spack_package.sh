#!/bin/bash

set -e

version=0.1.0
versioned_dir=mnoda-${version}
versioned_tar=${versioned_dir}.tgz
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

