cmake_minimum_required (VERSION 3.7)

find_package(Conduit REQUIRED)

blt_register_library(NAME Conduit
        INCLUDES "${Conduit_DIR}/../../../include/conduit"
        LIBRARIES "conduit"
        TREAT_INCLUDES_AS_SYSTEM ON
        )

# libdl is a requirement of Adiak, not Sina, but conditional inclusion
# creates issues on CZ. Delete this when Adiak includes libdl
blt_register_library(NAME libdl
    TREAT_INCLUDES_AS_SYSTEM ON
    LINK_FLAGS -ldl
)

set(OPTIONAL_SINA_DEPENDENCIES "")

if(${SINA_BUILD_ADIAK_BINDINGS})
    add_definitions(-DSINA_BUILD_ADIAK_BINDINGS=1)
    set_source_files_properties(AdiakWriter.cpp PROPERTIES COMPILE_FLAGS "${CXX_FLAGS} ${SINA_CXX_ADIAK_WRITER_EXTRA_FLAGS}")
    find_package(adiak REQUIRED)

    blt_register_library(NAME adiak
        TREAT_INCLUDES_AS_SYSTEM ON
        INCLUDES "${adiak_DIR}/../../../include"
        LIBRARIES "${adiak_DIR}/../../libadiak.a"
    )
    string(CONCAT OPTIONAL_SINA_DEPENDENCIES "adiak")
endif(${SINA_BUILD_ADIAK_BINDINGS})

blt_add_library(NAME sina
    HEADERS
        ../include/sina/CppBridge.hpp
        ../include/sina/Curve.hpp
        ../include/sina/CurveSet.hpp
        ../include/sina/Document.hpp
        ../include/sina/File.hpp
        ../include/sina/ID.hpp
        ../include/sina/ConduitUtil.hpp
        ../include/sina/sina.hpp
        ../include/sina/Record.hpp
        ../include/sina/Relationship.hpp
        ../include/sina/Run.hpp
        ../include/sina/Datum.hpp
        ../include/sina/AdiakWriter.hpp
    SOURCES
        Curve.cpp
        CurveSet.cpp
        Document.cpp
        File.cpp
        ID.cpp
        ConduitUtil.cpp
        Record.cpp
        Relationship.cpp
        Run.cpp
        Datum.cpp
        AdiakWriter.cpp
    DEPENDS_ON
        Conduit
        ${OPTIONAL_SINA_DEPENDENCIES}
)

install(TARGETS sina
    ARCHIVE DESTINATION "lib"
    LIBRARY DESTINATION "lib")
