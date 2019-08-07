#include "gtest/gtest.h"

#include "sina/File.hpp"

namespace sina { namespace testing { namespace {

char const EXPECTED_URI_KEY[] = "uri";
char const EXPECTED_MIMETYPE_KEY[] = "mimetype";
char const EXPECTED_TAGS_KEY[] = "tags";

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

TEST(File, setTags) {
    std::vector<std::string> tags = {"these", "are", "tags"};
    File file{"the URI"};
    file.setTags(tags);
    EXPECT_EQ("the URI", file.getUri());
    EXPECT_EQ(tags, file.getTags());
}

TEST(File, create_fromJson_basic) {
    std::string uri = "the URI";
    nlohmann::json basic_file;
    File file{uri, basic_file};
    EXPECT_EQ(uri, file.getUri());
    EXPECT_EQ("", file.getMimeType());
    EXPECT_EQ(0, file.getTags().size());
}

TEST(File, create_fromJson_complete) {
    std::string uri = "another/uri.txt";
    std::vector<std::string> tags = {"tags", "are", "fun"};
    nlohmann::json full_file{
            {EXPECTED_MIMETYPE_KEY, "the mime type"},
    };
    full_file[EXPECTED_TAGS_KEY] = tags;
    File file{uri, full_file};
    EXPECT_EQ(uri, file.getUri());
    EXPECT_EQ("the mime type", file.getMimeType());
    EXPECT_EQ(tags, file.getTags());
}

TEST(File, toJson_basic) {
    File file{"the URI"};
    auto asJson = file.toJson();
    EXPECT_EQ(nlohmann::json::value_t::null,
            asJson[EXPECTED_MIMETYPE_KEY].type());
    EXPECT_EQ(nlohmann::json::value_t::null,
            asJson[EXPECTED_TAGS_KEY].type());
}

TEST(File, toJson_complete) {
    std::vector<std::string> tags = {"these", "are", "tags"};
    File file{"the URI"};
    file.setMimeType("the mime type");
    file.setTags(tags);
    auto asJson = file.toJson();
    EXPECT_EQ("the mime type", asJson[EXPECTED_MIMETYPE_KEY]);
    EXPECT_EQ(tags, asJson[EXPECTED_TAGS_KEY]);
}

}}}
