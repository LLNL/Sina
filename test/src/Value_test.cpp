#include <stdexcept>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "nlohmann/json.hpp"

#include "mnoda/Value.hpp"

namespace mnoda { namespace testing { namespace {

using ::testing::HasSubstr;
using ::testing::DoubleEq;
using ::testing::ElementsAre;

TEST(Value, create) {
    std::vector<std::string> tags = {"tag1", "tag2"};
    Value value1{"the name", "value", tags};
    Value value2{"another name", 3.14};

    EXPECT_EQ("the name", value1.getName());
    EXPECT_EQ(ValueType::Value, value1.getType());
    EXPECT_EQ("value", value1.getValue());
    EXPECT_EQ(tags, value1.getTags());

    EXPECT_EQ("another name", value2.getName());
    EXPECT_EQ(ValueType::Scalar, value2.getType());
    EXPECT_THAT(value2.getScalar(), DoubleEq(3.14));
}

TEST(Value, createFromJson) {
    nlohmann::json object1;
    nlohmann::json object2;
    std::vector<std::string> tags = {"hello", "world"};
    object1["name"] = "object 1";
    object1["value"] = "the value";
    object1["tags"] = tags;
    object2["name"] = "object 2";
    object2["value"] = 3.14;

    Value value1{object1};
    Value value2{object2};
    EXPECT_EQ("object 1", value1.getName());
    EXPECT_EQ("the value", value1.getValue());
    EXPECT_EQ(tags, value1.getTags());

    EXPECT_EQ("object 2", value2.getName());
    EXPECT_THAT(3.14, DoubleEq(value2.getScalar()));
}

TEST(Value, createFromJson_missingKeys) {
    nlohmann::json object1;
    nlohmann::json object2;
    object1["name"] = "only name";
    object2["value"] = "only value";
    try {
        Value value1{object1};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("value"));
    }
    try {
        Value value2{object2};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("name"));
    }
}

TEST(Value, toJson) {
    std::vector<std::string> tags = {"list", "of", "tags"};
    Value value1{"value name", "value value", tags};
    Value value2{"value name again", 3.14};
    nlohmann::json valueRef1 = value1.toJson();
    nlohmann::json valueRef2 = value2.toJson();
    EXPECT_EQ("value name", valueRef1["name"]);
    EXPECT_EQ("value value", valueRef1["value"]);
    EXPECT_EQ(tags, valueRef1["tags"]);

    EXPECT_EQ("value name again", valueRef2["name"]);
    EXPECT_THAT(3.14, DoubleEq(valueRef2["value"]));
}

}}}
