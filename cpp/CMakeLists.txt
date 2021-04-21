cmake_minimum_required (VERSION 3.7)

project(sina)

set (ENABLE_GMOCK ON CACHE PATH "")

set(CMAKE_CXX_FLAGS ${SINA_BASE_CXX_FLAGS})
include(blt/SetupBLT.cmake)

# Now that BLT has built gtest and gmock, we can use our own flags for our
# main code. If we do this too early, the gtest/gmock builds will fail
set(CMAKE_CXX_FLAGS ${SINA_CXX_FLAGS})

set(SINA_VERSION_MAJOR 1)
set(SINA_VERSION_MINOR 9)
set(SINA_VERSION_PATCH 5)

CONFIGURE_FILE(${CMAKE_SOURCE_DIR}/config/config.hpp.in
        ${CMAKE_CURRENT_BINARY_DIR}/include/sina/config.hpp)

include_directories("${PROJECT_SOURCE_DIR}/include")
include_directories("${CMAKE_CURRENT_BINARY_DIR}/include")

install(DIRECTORY "include/sina"
    DESTINATION "include")

install(FILES "${CMAKE_CURRENT_BINARY_DIR}/include/sina/config.hpp"
    DESTINATION "include/sina")

add_subdirectory(src)
if (${SINA_BUILD_TESTS})
    add_subdirectory(test)
endif (${SINA_BUILD_TESTS})

if (${SINA_BUILD_DOCS})
    add_subdirectory(docs)
endif (${SINA_BUILD_DOCS})
