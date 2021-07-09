#------------------------------------------------------------------------------
# !!!! This is a generated file, edit at own risk !!!!
#------------------------------------------------------------------------------
# CMake executable path: /usr/tce/bin/cmake
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Compilers
#------------------------------------------------------------------------------
# Compiler Spec: intel@19.0.4
#------------------------------------------------------------------------------
if(DEFINED ENV{SPACK_CC})

  set(CMAKE_C_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/intel/icc" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/intel/icpc" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/intel/ifort" CACHE PATH "")

else()

  set(CMAKE_C_COMPILER "/usr/tce/packages/intel/intel-19.0.4/bin/icc" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/usr/tce/packages/intel/intel-19.0.4/bin/icpc" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/usr/tce/packages/intel/intel-19.0.4/bin/ifort" CACHE PATH "")

endif()

set(CMAKE_C_FLAGS "-gcc-name=/usr/tce/packages/gcc/gcc-10.2.1/bin/gcc" CACHE STRING "")

set(CMAKE_CXX_FLAGS "-gxx-name=/usr/tce/packages/gcc/gcc-10.2.1/bin/g++" CACHE STRING "")

set(CMAKE_Fortran_FLAGS "-gcc-name=/usr/tce/packages/gcc/gcc-10.2.1/bin/gcc" CACHE STRING "")

#------------------------------------------------------------------------------
# MPI
#------------------------------------------------------------------------------

set(MPI_C_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-intel-19.0.4/bin/mpicc" CACHE PATH "")

set(MPI_CXX_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-intel-19.0.4/bin/mpicxx" CACHE PATH "")

set(MPI_Fortran_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-intel-19.0.4/bin/mpif90" CACHE PATH "")

set(MPIEXEC_EXECUTABLE "/usr/bin/srun" CACHE PATH "")

set(MPIEXEC_NUMPROC_FLAG "-n" CACHE STRING "")

#------------------------------------------------------------------------------
# Hardware
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Library Dependencies
#------------------------------------------------------------------------------
set(TPL_ROOT "/collab/usr/gapps/wf/dev/SINA_TPL/spack/opt/spack/linux-rhel7-ivybridge/intel-19.0.4" CACHE PATH "")

set(Conduit_DIR "${TPL_ROOT}/conduit-0.7.1-sanqdhoj37r5parhgr3doeirmmozbbin/lib/cmake/conduit" CACHE PATH "")

set(SINA_BUILD_ADIAK_BINDINGS ON CACHE BOOL "")

set(adiak_DIR "${TPL_ROOT}/adiak-0.2.1-yohidushtxjxc4lcbstq6d7koe3gyott/lib/cmake/adiak/" CACHE PATH "")

#------------------------------------------------------------------------------
# Devtools
#------------------------------------------------------------------------------
set(SINA_BUILD_TESTS ON CACHE BOOL "")

set(SINA_BUILD_DOCS ON CACHE BOOL "")

set(DOXYGEN_EXECUTABLE "/usr/bin/doxygen" CACHE PATH "")


