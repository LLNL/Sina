#include "sina/config.hpp"

#include "gtest/gtest.h"

namespace sina { namespace testing { namespace {

TEST(config, version) {
// Since we can't easily test the value of this string, just ensure it is set
#ifndef SINA_VERSION
    fail() << "Version not defined";
#endif
    ASSERT_GE(SINA_VERSION_MAJOR, 1);
    ASSERT_GE(SINA_VERSION_MINOR, 0);
    ASSERT_GE(SINA_VERSION_PATCH, 0);
}

}}}

