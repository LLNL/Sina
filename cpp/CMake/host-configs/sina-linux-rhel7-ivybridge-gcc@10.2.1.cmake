#------------------------------------------------------------------------------
# !!!! This is a generated file, edit at own risk !!!!
#------------------------------------------------------------------------------
# CMake executable path: /usr/tce/bin/cmake
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Compilers
#------------------------------------------------------------------------------
# Compiler Spec: gcc@10.2.1
#------------------------------------------------------------------------------
if(DEFINED ENV{SPACK_CC})

  set(CMAKE_C_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/gcc/gcc" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/gcc/g++" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/gcc/gfortran" CACHE PATH "")

else()

  set(CMAKE_C_COMPILER "/usr/tce/packages/gcc/gcc-10.2.1/bin/gcc" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/usr/tce/packages/gcc/gcc-10.2.1/bin/g++" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/usr/tce/packages/gcc/gcc-10.2.1/bin/gfortran" CACHE PATH "")

endif()

#------------------------------------------------------------------------------
# MPI
#------------------------------------------------------------------------------

set(MPI_C_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-gcc-10.2.1/bin/mpicc" CACHE PATH "")

set(MPI_CXX_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-gcc-10.2.1/bin/mpicxx" CACHE PATH "")

set(MPI_Fortran_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-gcc-10.2.1/bin/mpif90" CACHE PATH "")

set(MPIEXEC_EXECUTABLE "/usr/bin/srun" CACHE PATH "")

set(MPIEXEC_NUMPROC_FLAG "-n" CACHE STRING "")

#------------------------------------------------------------------------------
# Hardware
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Library Dependencies
#------------------------------------------------------------------------------
set(TPL_ROOT "/collab/usr/gapps/wf/dev/SINA_TPL/spack/opt/spack/linux-rhel7-ivybridge/gcc-10.2.1" CACHE PATH "")

set(Conduit_DIR "${TPL_ROOT}/conduit-0.7.1-zurcldnefm45fkfnvo4q4m67cubvivog/lib/cmake/conduit" CACHE PATH "")

set(SINA_BUILD_ADIAK_BINDINGS ON CACHE BOOL "")

set(adiak_DIR "${TPL_ROOT}/adiak-0.2.1-mq2ed42qp3ujmaxgxtpkm5pdgeux2okt/lib/cmake/adiak/" CACHE PATH "")

#------------------------------------------------------------------------------
# Devtools
#------------------------------------------------------------------------------
set(SINA_BUILD_TESTS ON CACHE BOOL "")

set(SINA_BUILD_DOCS ON CACHE BOOL "")

set(DOXYGEN_EXECUTABLE "/usr/bin/doxygen" CACHE PATH "")


