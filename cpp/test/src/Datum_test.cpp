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
    std::string value = "value";
    Datum datum1{value};
    datum1.setUnits("some units");
    datum1.setTags(tags);
    Datum datum2{3.14};

    EXPECT_EQ(ValueType::String, datum1.getType());
    EXPECT_EQ("value", datum1.getValue());
    EXPECT_EQ("some units", datum1.getUnits());
    EXPECT_EQ(tags, datum1.getTags());

    EXPECT_EQ(ValueType::Scalar, datum2.getType());
    EXPECT_THAT(datum2.getScalar(), DoubleEq(3.14));
}

TEST(Datum, createFromJson) {
    nlohmann::json object1;
    nlohmann::json object2;
    std::vector<std::string> tags = {"hello", "world"};
    object1["value"] = "the value";
    object1["tags"] = tags;
    object1["units"] = "some units";
    object2["value"] = 3.14;

    Datum datum1{object1};
    Datum datum2{object2};
    EXPECT_EQ("the value", datum1.getValue());
    EXPECT_EQ("some units", datum1.getUnits());
    EXPECT_EQ(tags, datum1.getTags());

    EXPECT_THAT(3.14, DoubleEq(datum2.getScalar()));
}

TEST(Datum, setUnits) {
    std::string value = "value";
    Datum datum1{value};
    datum1.setUnits("new units");
    EXPECT_EQ("new units", datum1.getUnits());
}

TEST(Datum, setTags) {
    std::string value = "value";
    Datum datum1{value};
    datum1.setTags({"new_tag"});
    EXPECT_EQ("new_tag", datum1.getTags()[0]);
}

TEST(Datum, createFromJson_missingKeys) {
    nlohmann::json object1;
    try {
        Datum datum1{object1};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("value"));
    }
}

TEST(Datum, toJson) {
    std::vector<std::string> tags = {"list", "of", "tags"};
    std::string value = "Datum value";
    Datum datum1{value};
    datum1.setTags(tags);
    Datum datum2{3.14};
    datum2.setUnits("Datum units");
    nlohmann::json datumRef1 = datum1.toJson();
    nlohmann::json datumRef2 = datum2.toJson();
    EXPECT_EQ("Datum value", datumRef1["value"]);
    EXPECT_EQ(tags, datumRef1["tags"]);

    EXPECT_EQ("Datum units", datumRef2["units"]);
    EXPECT_THAT(3.14, DoubleEq(datumRef2["value"]));
}

}}}
