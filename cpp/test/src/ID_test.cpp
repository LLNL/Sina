#include <stdexcept>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "conduit/conduit.hpp"

#include "sina/ID.hpp"

namespace sina { namespace testing { namespace {

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

TEST(IDField, createFromNode_local) {
    conduit::Node object;
    object["local id key"] = "the id";
    internal::IDField field{object, "local id key", "global id key"};
    EXPECT_EQ("the id", field.getID().getId());
    EXPECT_EQ(IDType::Local, field.getID().getType());
    EXPECT_EQ("local id key", field.getLocalName());
    EXPECT_EQ("global id key", field.getGlobalName());
}

TEST(IDField, createFromNode_global) {
    conduit::Node object;
    object["local id key"] = "local id";
    object["global id key"] = "global id";

    internal::IDField field{object, "local id key", "global id key"};
    EXPECT_EQ("global id", field.getID().getId());
    EXPECT_EQ(IDType::Global, field.getID().getType());
    EXPECT_EQ("local id key", field.getLocalName());
    EXPECT_EQ("global id key", field.getGlobalName());
}

TEST(IDField, createFromNode_missingKeys) {
    conduit::Node object;
    try {
        internal::IDField field{object, "local id key", "global id key"};
        FAIL() << "Should have gotten a value error";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr("local id key"));
        EXPECT_THAT(expected.what(), HasSubstr("global id key"));
    }
}

TEST(IDField, toNode_local) {
    ID id{"the id", IDType::Local};
    internal::IDField field{id, "local name", "global name"};
    conduit::Node value;
    field.addTo(value);
    EXPECT_EQ("the id", value["local name"].value());
    EXPECT_TRUE(value["global name"].dtype().is_empty());
}

TEST(IDField, toNode_global) {
    ID id{"the id", IDType::Global};
    internal::IDField field{id, "local name", "global name"};
    conduit::Node value;
    field.addTo(value);
    EXPECT_EQ("the id", value["global name"].value());
    EXPECT_FALSE(value.has_child("local name"));
}

}}}
