#include <stdexcept>
#include <string>
#include <vector>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "nlohmann/json.hpp"

#include "mnoda/Datum.hpp"

namespace mnoda { namespace testing { namespace {

using ::testing::HasSubstr;
using ::testing::DoubleEq;
using ::testing::ElementsAre;

TEST(Datum, create) {
    std::vector<std::string> tags = {"tag1", "tag2"};
    Datum datum1{"the name", "value"};
    datum1.setUnits("some units");
    datum1.setTags(tags);
    Datum datum2{"another name", 3.14};

    EXPECT_EQ("the name", datum1.getName());
    EXPECT_EQ(ValueType::Value, datum1.getType());
    EXPECT_EQ("value", datum1.getValue());
    EXPECT_EQ("some units", datum1.getUnits());
    EXPECT_EQ(tags, datum1.getTags());

    EXPECT_EQ("another name", datum2.getName());
    EXPECT_EQ(ValueType::Scalar, datum2.getType());
    EXPECT_THAT(datum2.getScalar(), DoubleEq(3.14));
}

TEST(Datum, createFromJson) {
    nlohmann::json object1;
    nlohmann::json object2;
    std::vector<std::string> tags = {"hello", "world"};
    object1["name"] = "object 1";
    object1["value"] = "the value";
    object1["tags"] = tags;
    object1["units"] = "some units";
    object2["name"] = "object 2";
    object2["value"] = 3.14;

    Datum datum1{object1};
    Datum datum2{object2};
    EXPECT_EQ("object 1", datum1.getName());
    EXPECT_EQ("the value", datum1.getValue());
    EXPECT_EQ("some units", datum1.getUnits());
    EXPECT_EQ(tags, datum1.getTags());

    EXPECT_EQ("object 2", datum2.getName());
    EXPECT_THAT(3.14, DoubleEq(datum2.getScalar()));
}

TEST(Datum, setUnits) {
    Datum datum1{"the name","value"};
    datum1.setUnits("new units");
    EXPECT_EQ("new units", datum1.getUnits());
}

TEST(Datum, setTags) {
    Datum datum1{"the name","value"};
    datum1.setTags({"new_tag"});
    EXPECT_EQ("new_tag", datum1.getTags()[0]);
}

TEST(Datum, createFromJson_missingKeys) {
    nlohmann::json object1;
    nlohmann::json object2;
    object1["name"] = "only name";
    object2["value"] = "only value";
    try {
        Datum datum1{object1};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("value"));
    }
    try {
        Datum datum2{object2};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("name"));
    }
}

TEST(Datum, toJson) {
    std::vector<std::string> tags = {"list", "of", "tags"};
    Datum datum1{"Datum name", "Datum value"};
    datum1.setTags(tags);
    Datum datum2{"Datum name again", 3.14};
    datum2.setUnits("Datum units again");
    nlohmann::json datumRef1 = datum1.toJson();
    nlohmann::json datumRef2 = datum2.toJson();
    EXPECT_EQ("Datum name", datumRef1["name"]);
    EXPECT_EQ("Datum value", datumRef1["value"]);
    EXPECT_EQ(tags, datumRef1["tags"]);

    EXPECT_EQ("Datum name again", datumRef2["name"]);
    EXPECT_EQ("Datum units again", datumRef2["units"]);
    EXPECT_THAT(3.14, DoubleEq(datumRef2["value"]));
}

}}}
