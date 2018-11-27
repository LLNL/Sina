#include <stdexcept>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "nlohmann/json.hpp"

#include "mnoda/ID.hpp"

namespace mnoda { namespace testing { namespace {

using ::testing::HasSubstr;

TEST(ID, create) {
    ID id1{"the name", IDType::Local};
    ID id2{"another name", IDType::Global};

    EXPECT_EQ("the name", id1.getId());
    EXPECT_EQ("another name", id2.getId());

    EXPECT_EQ(IDType::Local, id1.getType());
    EXPECT_EQ(IDType::Global, id2.getType());
}

TEST(IDField, create) {
    ID id{"the id", IDType::Global};
    internal::IDField field{id, "local name", "global name"};
    EXPECT_EQ("the id", field.getID().getId());
    EXPECT_EQ(IDType::Global, field.getID().getType());
    EXPECT_EQ("local name", field.getLocalName());
    EXPECT_EQ("global name", field.getGlobalName());
}

TEST(IDField, createFromJson_local) {
    nlohmann::json object{
            {"local id key", "the id"}
    };
    internal::IDField field{object, "local id key", "global id key"};
    EXPECT_EQ("the id", field.getID().getId());
    EXPECT_EQ(IDType::Local, field.getID().getType());
    EXPECT_EQ("local id key", field.getLocalName());
    EXPECT_EQ("global id key", field.getGlobalName());
}

TEST(IDField, createFromJson_global) {
    nlohmann::json object{
            // should be ignored in the presence of a global ID
            {"local id key", "local id"},
            {"global id key", "global id"}
    };
    internal::IDField field{object, "local id key", "global id key"};
    EXPECT_EQ("global id", field.getID().getId());
    EXPECT_EQ(IDType::Global, field.getID().getType());
    EXPECT_EQ("local id key", field.getLocalName());
    EXPECT_EQ("global id key", field.getGlobalName());
}

TEST(IDField, createFromJson_missingKeys) {
    nlohmann::json object;
    try {
        internal::IDField field{object, "local id key", "global id key"};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("local id key"));
        EXPECT_THAT(expected.what(), HasSubstr("global id key"));
    }
}

TEST(IDField, toJson_local) {
    ID id{"the id", IDType::Local};
    internal::IDField field{id, "local name", "global name"};
    nlohmann::json value;
    field.addTo(value);
    EXPECT_EQ("the id", value["local name"]);
    EXPECT_EQ(0, value.count("global name"));
}

TEST(IDField, toJson_global) {
    ID id{"the id", IDType::Global};
    internal::IDField field{id, "local name", "global name"};
    nlohmann::json value;
    field.addTo(value);
    EXPECT_EQ("the id", value["global name"]);
    EXPECT_EQ(0, value.count("local name"));
}

}}}
