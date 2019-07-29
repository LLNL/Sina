cmake_minimum_required (VERSION 3.7)

find_package(nlohmann_json REQUIRED)

blt_register_library(NAME nlohmann_json
        INCLUDES "${nlohmann_json_DIR}/../../../include"
        TREAT_INCLUDES_AS_SYSTEM ON
        )

blt_add_library(NAME sina
    HEADERS
        ../include/sina/CppBridge.hpp
        ../include/sina/Document.hpp
        ../include/sina/File.hpp
        ../include/sina/ID.hpp
        ../include/sina/JsonUtil.hpp
        ../include/sina/sina.hpp
        ../include/sina/Record.hpp
        ../include/sina/Relationship.hpp
        ../include/sina/Run.hpp
        ../include/sina/Datum.hpp
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

install(TARGETS sina
    ARCHIVE DESTINATION "lib"
    LIBRARY DESTINATION "lib")

