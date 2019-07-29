#include <stdexcept>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "sina/JsonUtil.hpp"

namespace sina { namespace testing { namespace {

using ::testing::HasSubstr;
using ::testing::DoubleEq;

TEST(JsonUtil, getRequiredField_present) {
    nlohmann::json parent{
            {"fieldName", "field value"}
    };
    auto &field = getRequiredField("fieldName", parent, "parent name");
    EXPECT_TRUE(field.is_string());
    EXPECT_EQ("field value", field);
}

TEST(JsonUtil, getRequiredField_missing) {
    nlohmann::json parent;
    try {
        auto &field = getRequiredField("fieldName", parent, "parent name");
        FAIL() << "Should not have found field, but got " << field;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
    }
}

TEST(JsonUtil, getRequiredString_valid) {
    nlohmann::json parent{
            {"fieldName", "field value"}
    };
    EXPECT_EQ("field value",
            getRequiredString("fieldName", parent, "parent name"));
}

TEST(JsonUtil, getRequiredString_missing) {
    nlohmann::json parent;
    try {
        auto value = getRequiredString("fieldName", parent, "parent name");
        FAIL() << "Should not have found string, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
    }
}

TEST(JsonUtil, getRequiredString_wrongType) {
    nlohmann::json parent{
            {"fieldName", 123}
    };
    try {
        auto value = getRequiredString("fieldName", parent, "parent name");
        FAIL() << "Should not have found string, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
        EXPECT_THAT(expected.what(), HasSubstr("string"));
    }
}

TEST(JsonUtil, getRequiredDouble_valid) {
    nlohmann::json parent{
        {"fieldName", 3.14}
    };
    EXPECT_THAT(3.14, 
        DoubleEq(getRequiredDouble("fieldName", parent, "parent name")));
}

TEST(JsonUtil, getRequiredDouble_missing) {
    nlohmann::json parent;
    try {
        auto value = getRequiredDouble("fieldName", parent, "parent name");
        FAIL() << "Should not have found double, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
    }
}

TEST(JsonUtil, getRequiredDouble_wrongType) {
    nlohmann::json parent{
        {"fieldName", "field value"}
    };
    try {
        auto value = getRequiredDouble("fieldName", parent, "parent name");
        FAIL() << "Should not have found double, but got " << value;
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("fieldName"));
        EXPECT_THAT(expected.what(), HasSubstr("parent name"));
        EXPECT_THAT(expected.what(), HasSubstr("double"));
    }
}

TEST(JsonUtil, getOptionalString_valid) {
    nlohmann::json parent{
            {"fieldName", "the value"}
    };
    EXPECT_EQ("the value",
            getOptionalString("fieldName", parent, "parent name"));
}

TEST(JsonUtil, getOptionalString_missing) {
    nlohmann::json parent;
    EXPECT_EQ("", getOptionalString("fieldName", parent, "parent name"));
}

TEST(JsonUtil, getOptionalString_explicitNullValue) {
    nlohmann::json parent{
            {"fieldName", nullptr}
    };
    EXPECT_EQ("", getOptionalString("fieldName", parent, "parent name"));
}

TEST(JsonUtil, getOptionalString_wrongType) {
    nlohmann::json parent{
            {"fieldName", 123}
    };
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
