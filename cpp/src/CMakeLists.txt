cmake_minimum_required (VERSION 3.7)
include(CMakePackageConfigHelpers)

find_package(Conduit REQUIRED)

blt_register_library(NAME Conduit
        INCLUDES "${CONDUIT_INCLUDE_DIRS}"
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
    set_source_files_properties(AdiakWriter.cpp PROPERTIES COMPILE_FLAGS "${CXX_FLAGS} ${SINA_CXX_ADIAK_WRITER_EXTRA_FLAGS}")
    find_package(adiak REQUIRED)

    blt_register_library(NAME adiak
        TREAT_INCLUDES_AS_SYSTEM ON
        INCLUDES "${adiak_INCLUDE_DIR}"
        LIBRARIES adiak
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
        ../include/sina/DataHolder.hpp
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
        DataHolder.cpp
        AdiakWriter.cpp
    DEPENDS_ON
        Conduit
        ${OPTIONAL_SINA_DEPENDENCIES}
)

install(TARGETS sina
    EXPORT sinaTarget
    ARCHIVE DESTINATION "lib"
    LIBRARY DESTINATION "lib")

#install(EXPORT sinaTarget
#        FILE "SinaConfig.cmake"
#        NAMESPACE sina::
#        DESTINATION "lib/cmake/sina"
#)

set(sina_INSTALL_INCLUDE_DIR include/)
configure_package_config_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/../CMake/config.cmake.in"
  "SinaConfig.cmake"
  INSTALL_DESTINATION "${CMAKE_INSTALL_LIBDIR}/cmake/sina"
  PATH_VARS sina_INSTALL_INCLUDE_DIR)

install(FILES "${CMAKE_CURRENT_BINARY_DIR}/SinaConfig.cmake"
        DESTINATION lib/cmake/sina)
