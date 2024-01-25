cmake_minimum_required (VERSION 3.7)

enable_language(Fortran)
project(sina-fortran)

if (NOT BLT_CXX_STD)
    set(BLT_CXX_STD "c++11" CACHE STRING "")
endif()

include(../cpp/blt/SetupBLT.cmake)

set(SINA_VERSION_MAJOR 1)
set(SINA_VERSION_MINOR 13) 
set(SINA_VERSION_PATCH 0)

include_directories("${PROJECT_SOURCE_DIR}/include")

install(DIRECTORY "include"
        DESTINATION "${PROJECT_SOURCE_DIR}")

#install(FILES "${CMAKE_CURRENT_BINARY_DIR}/include/config.hpp"
#    DESTINATION "include/")
install(DIRECTORY "include"
        DESTINATION "sina-fortran")

add_subdirectory(src)
