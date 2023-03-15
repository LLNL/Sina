#!/bin/sh

module load gcc/10.2.1
rm example_program sina_dump.json
export SINA_CPP_DIR=../../cpp/build-clang/install
export SINA_FORTRAN_DIR=../build
export Conduit_DIR=/collab/usr/gapps/wf/dev/SINA_TPL/spack/opt/spack/linux-rhel7-ivybridge/clang-11.0.1/conduit-0.7.1-fqd3avvtpgrohpv2bmnxc2eirk5lyn7a/

g++ -Wall -o  example_program example.f90 \
-Iinclude/ -I${SINA_FORTRAN_DIR}/lib/fortran/ -I${SINA_CPP_DIR}/include/  -I${Conduit_DIR}/include/conduit/ \
-L${SINA_FORTRAN_DIR}/lib/ -L${SINA_CPP_DIR}/lib/ -L${Conduit_DIR}/lib/ \
-lsina_fortran -lsina -lconduit -lgfortran -lstdc++ -lpthread


LD_LIBRARY_PATH=$LD_LIBRARY_PATH:${Conduit_DIR}/lib/
export LD_LIBRARY_PATH
