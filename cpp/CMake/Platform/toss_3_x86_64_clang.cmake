set(DOXYGEN_EXECUTABLE "doxygen" CACHE PATH "")

set(CMAKE_CXX_COMPILER clang++-4.0.0)

string(CONCAT SINA_BASE_CXX_FLAGS "-std=c++11")

string(CONCAT SINA_CXX_FLAGS "${SINA_BASE_CXX_FLAGS} "
        "-Wall -Weverything -Werror "
        "-Wno-c++98-compat -Wno-c++98-compat-pedantic "
        "-Wno-padded "
        "-Wno-covered-switch-default "
        )

string(CONCAT SINA_CXX_TEST_FLAGS "${SINA_CXX_FLAGS} "
        "-Wno-undef -Wno-float-equal "
        "-Wno-missing-noreturn -Wno-weak-vtables "
        "-Wno-deprecated -Wno-shift-sign-overflow "
        "-Wno-used-but-marked-unused "
        "-Wno-global-constructors "
        "-Wno-potentially-evaluated-expression "
        )
