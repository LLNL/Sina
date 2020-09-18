cmake_minimum_required (VERSION 3.7)

project(sina CXX)

set (ENABLE_GMOCK ON CACHE PATH "")

set(CMAKE_CXX_FLAGS ${SINA_BASE_CXX_FLAGS})
include(blt/SetupBLT.cmake)

# Now that BLT has built gtest and gmock, we can use our own flags for our
# main code. If we do this too early, the gtest/gmock builds will fail
set(CMAKE_CXX_FLAGS ${SINA_CXX_FLAGS})

include_directories("${PROJECT_SOURCE_DIR}/include")

install(DIRECTORY "include/sina"
    DESTINATION "include")

add_subdirectory(src)
if (${SINA_BUILD_TESTS})
    add_subdirectory(test)
endif (${SINA_BUILD_TESTS})

if (${SINA_BUILD_DOCS})
    add_subdirectory(docs)
if (${SINA_BUILD_DOCS})
