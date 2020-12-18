cmake_minimum_required (VERSION 3.7)

add_definitions(${SINA_CXX_TEST_FLAGS})

include_directories("${PROJECT_SOURCE_DIR}/test/include")
include_directories("${CMAKE_CURRENT_BINARY_DIR}/../include")

# libdl is a requirement of Adiak, not Sina, but conditional inclusion
# creates issues on CZ. Delete this when Adiak includes libdl
blt_register_library(NAME libdl
    TREAT_INCLUDES_AS_SYSTEM ON
    LINK_FLAGS -ldl
)

find_package(Conduit REQUIRED)

if(${SINA_BUILD_ADIAK_BINDINGS})
    add_definitions(-DSINA_BUILD_ADIAK_BINDINGS=1)
    find_package(adiak REQUIRED)

    blt_register_library(NAME adiak
        TREAT_INCLUDES_AS_SYSTEM ON
        INCLUDES "${adiak_DIR}/../../../include"
        LIBRARIES "${adiak_DIR}/../../libadiak.a"
    )
    string(CONCAT OPTIONAL_SINA_DEPENDENCIES "adiak")
endif(${SINA_BUILD_ADIAK_BINDINGS})

blt_add_executable(NAME unittests
    SOURCES
        include/sina/testing/ConduitTestUtils.hpp
        include/sina/testing/TestRecord.hpp
        src/config_test.cpp
        src/CppBridge_test.cpp
        src/ConduitTestUtils.cpp
        src/Curve_test.cpp
        src/CurveSet_test.cpp
        src/Document_test.cpp
        src/File_test.cpp
        src/ID_test.cpp
        src/ConduitUtil_test.cpp
        src/Record_test.cpp
        src/Relationship_test.cpp
        src/Run_test.cpp
        src/Datum_test.cpp
        src/AdiakWriter_test.cpp
        src/TestRecord.cpp
    DEPENDS_ON sina gtest gmock Conduit libdl
)

blt_add_test(NAME unittests
             COMMAND unittests)
