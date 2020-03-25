set(DOXYGEN_EXECUTABLE "doxygen" CACHE PATH "")
string(CONCAT SINA_BASE_CXX_FLAGS "-std=c++11")

string(CONCAT SINA_CXX_FLAGS "${SINA_BASE_CXX_FLAGS} "
        "-Wall -Weverything -Werror "
        "-Wno-c++98-compat -Wno-c++98-compat-pedantic "
        "-Wno-padded "
        )

string(CONCAT SINA_CXX_TEST_FLAGS "${SINA_CXX_FLAGS} "
        "-Wno-undef -Wno-float-equal "
        "-Wno-missing-noreturn -Wno-weak-vtables "
        "-Wno-deprecated -Wno-shift-sign-overflow "
        "-Wno-used-but-marked-unused "
        "-Wno-global-constructors "
        "-Wno-potentially-evaluated-expression "
        "-Wno-zero-as-null-pointer-constant "
        )

string(CONCAT SINA_CXX_ADIAK_WRITER_EXTRA_FLAGS "-Wno-covered-switch-default")
