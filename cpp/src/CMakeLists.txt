cmake_minimum_required (VERSION 3.7)

find_package(nlohmann_json REQUIRED)

# compile a C file into an object file
if(NOT CMAKE_C_COMPILE_OBJECT)
  set(CMAKE_C_COMPILE_OBJECT
    "<CMAKE_C_COMPILER> <DEFINES> <INCLUDES> <FLAGS> -o <OBJECT>   -c <SOURCE>")
endif()

blt_register_library(NAME libdl
        TREAT_INCLUDES_AS_SYSTEM ON
        LINK_FLAGS -ldl
        )

blt_register_library(NAME adiak
        TREAT_INCLUDES_AS_SYSTEM ON
        INCLUDES "~/adiak/include" 
        )

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
        ../include/mnoda/adiak_mnoda_writer.hpp
    SOURCES
        Document.cpp
        File.cpp
        ID.cpp
        JsonUtil.cpp
        Record.cpp
        Relationship.cpp
        Run.cpp
        Datum.cpp
        adiak_mnoda_writer.cpp
    DEPENDS_ON
        nlohmann_json
        adiak
)

install(TARGETS sina
    ARCHIVE DESTINATION "lib"
    LIBRARY DESTINATION "lib")
