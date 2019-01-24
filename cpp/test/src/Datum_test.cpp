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
    std::vector<std::string> val_list = {"val1", "val2"};
    std::vector<double> scal_list = {100, 2.0};
    Datum datum1{value};
    datum1.setUnits("some units");
    datum1.setTags(tags);
    Datum datum2{3.14};
    Datum datum3{val_list};
    Datum datum4{scal_list};

    EXPECT_EQ(ValueType::String, datum1.getType());
    EXPECT_EQ("value", datum1.getValue());
    EXPECT_EQ("some units", datum1.getUnits());
    EXPECT_EQ(tags, datum1.getTags());

    EXPECT_EQ(ValueType::Scalar, datum2.getType());
    EXPECT_THAT(datum2.getScalar(), DoubleEq(3.14));

    EXPECT_EQ(ValueType::StringArray, datum3.getType());
    EXPECT_EQ(val_list, datum3.getStringArray());

    EXPECT_EQ(ValueType::ScalarArray, datum4.getType());
    EXPECT_EQ(scal_list, datum4.getScalarArray());
}

TEST(Datum, createFromJson) {
    nlohmann::json object1;
    nlohmann::json object2;
    nlohmann::json object3;
    nlohmann::json object4;
    nlohmann::json object5;
    std::vector<std::string> tags = {"hello", "world"};
    std::vector<std::string> val_list = {"val1", "val2"};
    std::vector<double> scal_list = {100, 2.0};
    object1["value"] = "the value";
    object1["tags"] = tags;
    object1["units"] = "some units";
    object2["value"] = 3.14;
    object3["value"] = val_list;
    object4["value"] = scal_list;
    //Empty arrays are valid
    object5["value"] = nlohmann::json::array();

    Datum datum1{object1};
    Datum datum2{object2};
    Datum datum3{object3};
    Datum datum4{object4};
    Datum datum5{object5};

    EXPECT_EQ("the value", datum1.getValue());
    EXPECT_EQ("some units", datum1.getUnits());
    EXPECT_EQ(tags, datum1.getTags());
    EXPECT_EQ(val_list, datum3.getStringArray());
    EXPECT_EQ(scal_list, datum4.getScalarArray());
    EXPECT_EQ(ValueType::ScalarArray, datum5.getType());

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

TEST(Datum, createFromJson_badListValue) {
    nlohmann::json object1;
    object1["value"] = {1, "two", 3};
    try {
        Datum datum1{object1};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        std::string warning = "it must consist of only strings or only numbers";
        EXPECT_THAT(expected.what(), HasSubstr(warning));
    }
}

TEST(Datum, toJson) {
    std::vector<std::string> tags = {"list", "of", "tags"};
    std::string value = "Datum value";
    std::vector<double> scal_list = {-14, 22, 9};
    std::vector<std::string> val_list = {"east", "west"};
    Datum datum1{value};
    datum1.setTags(tags);
    Datum datum2{3.14};
    datum2.setUnits("Datum units");
    Datum datum3{scal_list};
    Datum datum4{val_list};
    nlohmann::json datumRef1 = datum1.toJson();
    nlohmann::json datumRef2 = datum2.toJson();
    nlohmann::json datumRef3 = datum3.toJson();
    nlohmann::json datumRef4 = datum4.toJson();
    EXPECT_EQ("Datum value", datumRef1["value"]);
    EXPECT_EQ(tags, datumRef1["tags"]);

    EXPECT_EQ("Datum units", datumRef2["units"]);
    EXPECT_THAT(3.14, DoubleEq(datumRef2["value"]));

    EXPECT_EQ(scal_list, datumRef3["value"]);
    EXPECT_EQ(val_list, datumRef4["value"]);
}

}}}
