cmake_minimum_required (VERSION 3.7)

find_package(nlohmann_json REQUIRED)

blt_register_library(NAME nlohmann_json
        INCLUDES "${nlohmann_json_DIR}/../../../include"
        TREAT_INCLUDES_AS_SYSTEM ON
        )

blt_add_library(NAME mnoda
    HEADERS
        ../include/mnoda/CppBridge.hpp
        ../include/mnoda/Document.hpp
        ../include/mnoda/File.hpp
        ../include/mnoda/ID.hpp
        ../include/mnoda/JsonUtil.hpp
        ../include/mnoda/mnoda.hpp
        ../include/mnoda/Record.hpp
        ../include/mnoda/Relationship.hpp
        ../include/mnoda/Run.hpp
        ../include/mnoda/Datum.hpp
    SOURCES
        Document.cpp
        File.cpp
        ID.cpp
        JsonUtil.cpp
        Record.cpp
        Relationship.cpp
        Run.cpp
        Datum.cpp
    DEPENDS_ON nlohmann_json
)

install(TARGETS mnoda
    ARCHIVE DESTINATION "lib"
    LIBRARY DESTINATION "lib")

