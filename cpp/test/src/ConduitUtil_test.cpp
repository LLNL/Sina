#include <stdexcept>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "sina/ConduitUtil.hpp"

namespace sina { namespace testing { namespace {

using ::testing::HasSubstr;
using ::testing::DoubleEq;

TEST(ConduitUtil, getRequiredField_present) {
    conduit::Node parent;
    parent["fieldName"] = "field value";
    auto &field = getRequiredField("fieldName", parent, "parent name");
    EXPECT_TRUE(field.dtype().is_string());
    EXPECT_EQ("field value", field.as_string());
}

TEST(ConduitUtil, getRequiredField_missing) {
    conduit::Node parent;
    try {
        auto &field = getRequiredField("fieldName", parent, "parent name");
        FAIL() << "Should not have found field, but got " << field.name();
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
    }
}

TEST(ConduitUtil, getRequiredString_valid) {
    conduit::Node parent;
    parent["fieldName"] = "field value";
    EXPECT_EQ("field value",
              getRequiredString("fieldName", parent, "parent name"));
}

TEST(ConduitUtil, getRequiredString_missing) {
    conduit::Node parent;
    try {
        auto value = getRequiredString("fieldName", parent, "parent name");
        FAIL() << "Should not have found string, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
    }
}

TEST(ConduitUtil, getRequiredString_wrongType) {
    conduit::Node parent;
    parent["fieldName"] = 123;
    try {
        auto value = getRequiredString("fieldName", parent, "parent name");
        FAIL() << "Should not have found string, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
        EXPECT_THAT(expected.what(), HasSubstr("string"));
    }
}

TEST(ConduitUtil, getRequiredDouble_valid) {
    conduit::Node parent;
    parent["fieldName"] = 3.14;
    EXPECT_THAT(3.14,
        DoubleEq(getRequiredDouble("fieldName", parent, "parent name")));
}

TEST(ConduitUtil, getRequiredDouble_missing) {
    conduit::Node parent;
    try {
        auto value = getRequiredDouble("fieldName", parent, "parent name");
        FAIL() << "Should not have found double, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
    }
}

TEST(ConduitUtil, getRequiredDouble_wrongType) {
    conduit::Node parent;
    parent["fieldName"] = "field value";
    try {
        auto value = getRequiredDouble("fieldName", parent, "parent name");
        FAIL() << "Should not have found double, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
        EXPECT_THAT(expected.what(), HasSubstr("double"));
    }
}

TEST(ConduitUtil, getOptionalString_valid) {
    conduit::Node parent;
    parent["fieldName"] = "the value";
    EXPECT_EQ("the value",
              getOptionalString("fieldName", parent, "parent name"));
}

TEST(ConduitUtil, getOptionalString_missing) {
    conduit::Node parent;
    EXPECT_EQ("", getOptionalString("fieldName", parent, "parent name"));
}

/* TODO: Didn't find any references to handling of nullptr in conduit
TEST(ConduitUtil, getOptionalString_explicitNullValue) {
    conduit::Node parent;
    parent["fieldName"] = nullptr;
    EXPECT_EQ("", getOptionalString("fieldName", parent, "parent name"));
}*/

TEST(ConduitUtil, getOptionalString_wrongType) {
    conduit::Node parent;
    parent["fieldName"] = 123;
    try {
        auto value = getOptionalString("fieldName", parent, "parent name");
        FAIL() << "Should not have found string, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
        EXPECT_THAT(expected.what(), HasSubstr("string"));
    }
}

}}}
