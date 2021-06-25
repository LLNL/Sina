blt_add_doxygen_target(sina_doxygen)

blt_add_executable(
    NAME docs_main_page_basic
    SOURCES examples/main_page_basic.cpp
    DEPENDS_ON sina
)

blt_add_executable(
    NAME docs_tutorial
    SOURCES examples/tutorial.cpp
    DEPENDS_ON sina
)
