#include "gtest/gtest.h"

#include "mnoda/File.hpp"

namespace mnoda { namespace testing { namespace {

char const EXPECTED_URI_KEY[] = "uri";
char const EXPECTED_MIMETYPE_KEY[] = "mimetype";

TEST(File, construct_differentType) {
    File f1{"from literal"};
    File f2{std::string{"from std::string"}};
    EXPECT_EQ("from literal", f1.getUri());
    EXPECT_EQ("from std::string", f2.getUri());
}

TEST(File, setMimeType) {
    File file{"the URI"};
    file.setMimeType("mime");
    EXPECT_EQ("the URI", file.getUri());
    EXPECT_EQ("mime", file.getMimeType());
}

TEST(File, create_fromJson_basic) {
    nlohmann::json asJson{
            {EXPECTED_URI_KEY, "the URI"}
    };
    File file{asJson};
    EXPECT_EQ("the URI", file.getUri());
    EXPECT_EQ("", file.getMimeType());
}

TEST(File, create_fromJson_complete) {
    nlohmann::json asJson{
            {EXPECTED_URI_KEY, "the URI"},
            {EXPECTED_MIMETYPE_KEY, "the mime type"}
    };
    File file{asJson};
    EXPECT_EQ("the URI", file.getUri());
    EXPECT_EQ("the mime type", file.getMimeType());
}

TEST(File, toJson_basic) {
    File file{"the URI"};
    auto asJson = file.toJson();
    EXPECT_EQ("the URI", asJson[EXPECTED_URI_KEY]);
    EXPECT_EQ(nlohmann::json::value_t::null,
            asJson[EXPECTED_MIMETYPE_KEY].type());
}

TEST(File, toJson_complete) {
    File file{"the URI", "the mime type"};
    auto asJson = file.toJson();
    EXPECT_EQ("the URI", asJson[EXPECTED_URI_KEY]);
    EXPECT_EQ("the mime type", asJson[EXPECTED_MIMETYPE_KEY]);
}

}}}
