#include <string>

#include "gtest/gtest.h"

#include "sina/CppBridge.hpp"

namespace sina { namespace internal {  namespace testing { namespace {


TEST(CppBridge, make_unique_noParams) {
    std::unique_ptr<std::string> ptr = make_unique<std::string>();
    EXPECT_TRUE(ptr->empty());
}

TEST(CppBridge, make_unique_withParam) {
    std::unique_ptr<std::string> ptr = make_unique<std::string>("foo");
    EXPECT_EQ("foo", *ptr);
}

}}}}
