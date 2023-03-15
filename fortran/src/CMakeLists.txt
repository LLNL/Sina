cmake_minimum_required (VERSION 3.7)

find_package(Conduit REQUIRED)
blt_register_library(NAME Conduit
        INCLUDES "${CONDUIT_INCLUDE_DIRS}"
        LIBRARIES "conduit"
        )

find_package(Sina REQUIRED)

blt_register_library(NAME Sina
        INCLUDES "${sina_INCLUDE_DIR}"
        LIBRARIES "sina"
        DEPENDS_ON Conduit
        )

blt_add_library(NAME sina_fortran
    HEADERS
	../include/sina_fortran_interface.h
    SOURCES
	sina_fortran_interface.cpp
	sina_fortran_interface.f90
    DEPENDS_ON Sina
)

install(TARGETS sina_fortran
    ARCHIVE DESTINATION "lib"
    LIBRARY DESTINATION "lib")
