#------------------------------------------------------------------------------
# !!!! This is a generated file, edit at own risk !!!!
#------------------------------------------------------------------------------
# CMake executable path: /usr/tce/bin/cmake
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Compilers
#------------------------------------------------------------------------------
# Compiler Spec: clang@11.0.1
#------------------------------------------------------------------------------
if(DEFINED ENV{SPACK_CC})

  set(CMAKE_C_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/clang/clang" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/clang/clang++" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/collab/usr/gapps/wf/dev/SINA_TPL/spack/lib/spack/env/clang/gfortran" CACHE PATH "")

else()

  set(CMAKE_C_COMPILER "/usr/tce/packages/clang/clang-11.0.1/bin/clang" CACHE PATH "")

  set(CMAKE_CXX_COMPILER "/usr/tce/packages/clang/clang-11.0.1/bin/clang++" CACHE PATH "")

  set(CMAKE_Fortran_COMPILER "/usr/tce/packages/gcc/gcc-10.2.1/bin/gfortran" CACHE PATH "")

endif()

set(CMAKE_C_FLAGS "--gcc-toolchain=/usr/tce/packages/gcc/gcc-10.2.1" CACHE STRING "")

set(CMAKE_CXX_FLAGS "--gcc-toolchain=/usr/tce/packages/gcc/gcc-10.2.1" CACHE STRING "")

#------------------------------------------------------------------------------
# MPI
#------------------------------------------------------------------------------

set(MPI_C_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-clang-11.0.1/bin/mpicc" CACHE PATH "")

set(MPI_CXX_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-clang-11.0.1/bin/mpicxx" CACHE PATH "")

set(MPI_Fortran_COMPILER "/usr/tce/packages/mvapich2/mvapich2-2.3-clang-11.0.1/bin/mpif90" CACHE PATH "")

set(MPIEXEC_EXECUTABLE "/usr/bin/srun" CACHE PATH "")

set(MPIEXEC_NUMPROC_FLAG "-n" CACHE STRING "")

#------------------------------------------------------------------------------
# Hardware
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# Library Dependencies
#------------------------------------------------------------------------------
set(TPL_ROOT "/collab/usr/gapps/wf/dev/SINA_TPL/spack/opt/spack/linux-rhel7-ivybridge/clang-11.0.1" CACHE PATH "")

set(Conduit_DIR "${TPL_ROOT}/conduit-0.7.1-fqd3avvtpgrohpv2bmnxc2eirk5lyn7a/lib/cmake/conduit" CACHE PATH "")

set(SINA_BUILD_ADIAK_BINDINGS ON CACHE BOOL "")

set(adiak_DIR "${TPL_ROOT}/adiak-0.2.1-g5j7rsmf6vpihd6bqzim64xzcuqd7zjy/lib/cmake/adiak/" CACHE PATH "")

#------------------------------------------------------------------------------
# Devtools
#------------------------------------------------------------------------------
set(SINA_BUILD_TESTS ON CACHE BOOL "")

set(SINA_BUILD_DOCS ON CACHE BOOL "")

set(DOXYGEN_EXECUTABLE "/usr/bin/doxygen" CACHE PATH "")


