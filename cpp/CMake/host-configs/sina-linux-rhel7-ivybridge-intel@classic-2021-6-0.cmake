#------------------------------------------------------------------------------
# !!!! This is a generated file, edit at own risk !!!!
#------------------------------------------------------------------------------
# CMake executable path: /usr/tce/bin/cmake
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Compilers
#------------------------------------------------------------------------------
# Compiler Spec: intel@classic-2021.6.0
#------------------------------------------------------------------------------
if(DEFINED ENV{SPACK_CC})

  set(CMAKE_C_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/intel/icc" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/intel/icpc" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/intel/ifort" CACHE PATH "")

else()

  set(CMAKE_C_COMPILER "/usr/tce/packages/intel-classic/intel-classic-2021.6.0-magic/bin/icc" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/usr/tce/packages/intel-classic/intel-classic-2021.6.0-magic/bin/icpc" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/usr/tce/packages/intel-classic/intel-classic-2021.6.0-magic/bin/ifort" CACHE PATH "")

endif()

set(CMAKE_C_FLAGS "-gcc-name=/usr/tce/packages/gcc/gcc-11.2.1/bin/gcc" CACHE STRING "")

set(CMAKE_CXX_FLAGS "-gxx-name=/usr/tce/packages/gcc/gcc-11.2.1/bin/g++" CACHE STRING "")

set(CMAKE_Fortran_FLAGS "-gcc-name=/usr/tce/packages/gcc/gcc-11.2.1/bin/gcc" CACHE STRING "")

#------------------------------------------------------------------------------
# MPI
#------------------------------------------------------------------------------

set(MPI_C_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3.7-intel-classic-2021.6.0-magic/bin/mpicc" CACHE PATH "")

set(MPI_CXX_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3.7-intel-classic-2021.6.0-magic/bin/mpicxx" CACHE PATH "")

set(MPI_Fortran_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3.7-intel-classic-2021.6.0-magic/bin/mpif90" CACHE PATH "")

set(MPIEXEC_EXECUTABLE "/usr/bin/srun" CACHE PATH "")

set(MPIEXEC_NUMPROC_FLAG "-n" CACHE STRING "")

#------------------------------------------------------------------------------
# Hardware
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Library Dependencies
#------------------------------------------------------------------------------
set(TPL_ROOT "/collab/usr/gapps/wf/dev/SINA_TPL/manual" CACHE PATH "")

set(Conduit_DIR "${TPL_ROOT}/conduit/install-debug/lib/cmake/conduit" CACHE PATH "")

set(SINA_BUILD_ADIAK_BINDINGS ON CACHE BOOL "")

set(adiak_DIR "${TPL_ROOT}/Adiak/build/install/lib/cmake/adiak/" CACHE PATH "")

#------------------------------------------------------------------------------
# Devtools
#------------------------------------------------------------------------------
set(SINA_BUILD_TESTS ON CACHE BOOL "")

set(SINA_BUILD_DOCS ON CACHE BOOL "")

set(DOXYGEN_EXECUTABLE "/usr/bin/doxygen" CACHE PATH "")


