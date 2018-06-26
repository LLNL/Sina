cmake_minimum_required (VERSION 3.7)

add_definitions(${MNODA_CXX_TEST_FLAGS})

include_directories("${PROJECT_SOURCE_DIR}/test/include")

blt_add_executable(NAME unittests
    SOURCES
        include/mnoda/testing/TestRecord.hpp
        src/CppBridge_test.cpp
        src/Document_test.cpp
        src/File_test.cpp
        src/ID_test.cpp
        src/JsonUtil_test.cpp
        src/Record_test.cpp
        src/Relationship_test.cpp
        src/Run_test.cpp
        src/Value_test.cpp
        src/TestRecord.cpp
    DEPENDS_ON mnoda gtest gmock nlohmann_json
)

blt_add_test(NAME unittests
             COMMAND unittests)
