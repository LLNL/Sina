#include <stdexcept>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "sina/Run.hpp"

namespace sina { namespace testing { namespace {

using ::testing::HasSubstr;

char const EXPECTED_TYPE_KEY[] = "type";
char const EXPECTED_LOCAL_ID_KEY[] = "local_id";
char const EXPECTED_GLOBAL_ID_KEY[] = "id";
char const EXPECTED_APPLICATION_KEY[] = "application";
char const EXPECTED_VERSION_KEY[] = "version";
char const EXPECTED_USER_KEY[] = "user";

// Throughout, we have to use "sina::Run" instead of just "Run" due to
// a conflict with the Run() function in gtest

TEST(Run, create_fromJson_valid) {
    nlohmann::json originJson{
            {EXPECTED_TYPE_KEY, "run"},
            {EXPECTED_GLOBAL_ID_KEY, "the id"},
            {EXPECTED_APPLICATION_KEY, "the app"},
            {EXPECTED_VERSION_KEY, "1.2.3"},
            {EXPECTED_USER_KEY, "jdoe"}
    };
    sina::Run run{originJson};
    EXPECT_EQ("run", run.getType());
    EXPECT_EQ("the id", run.getId().getId());
    EXPECT_EQ(IDType::Global, run.getId().getType());
    EXPECT_EQ("the app", run.getApplication());
    EXPECT_EQ("1.2.3", run.getVersion());
    EXPECT_EQ("jdoe", run.getUser());
}

TEST(Run, create_fromJson_missingApplication) {
    nlohmann::json originJson{
            {EXPECTED_TYPE_KEY, "run"},
            {EXPECTED_GLOBAL_ID_KEY, "the id"},
            {EXPECTED_VERSION_KEY, "1.2.3"},
            {EXPECTED_USER_KEY, "jdoe"}
    };
    try {
        sina::Run run{originJson};
        FAIL() << "Application should be missing, but is "
               << run.getApplication();
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_APPLICATION_KEY));
    }
}

TEST(Run, toJson) {
    ID id{"the id", IDType::Global};
    sina::Run run{id, "the app", "1.2.3", "jdoe"};
    auto asJson = run.toJson();
    EXPECT_TRUE(asJson.is_object());
    EXPECT_EQ("run", asJson[EXPECTED_TYPE_KEY]);
    EXPECT_EQ("the id", asJson[EXPECTED_GLOBAL_ID_KEY]);
    EXPECT_EQ(0, asJson.count(EXPECTED_LOCAL_ID_KEY));
    EXPECT_EQ("the app", asJson[EXPECTED_APPLICATION_KEY]);
    EXPECT_EQ("1.2.3", asJson[EXPECTED_VERSION_KEY]);
    EXPECT_EQ("jdoe", asJson[EXPECTED_USER_KEY]);
}

TEST(Run, addRunLoader) {
    nlohmann::json originJson{
            {EXPECTED_TYPE_KEY, "run"},
            {EXPECTED_GLOBAL_ID_KEY, "the id"},
            {EXPECTED_APPLICATION_KEY, "the app"},
            {EXPECTED_VERSION_KEY, "1.2.3"},
            {EXPECTED_USER_KEY, "jdoe"}
    };

    RecordLoader loader;
    addRunLoader(loader);

    auto record = loader.load(originJson);
    auto run = dynamic_cast<sina::Run *>(record.get());
    ASSERT_NE(nullptr, run);
    EXPECT_EQ("run", run->getType());
    EXPECT_EQ("the id", run->getId().getId());
    EXPECT_EQ(IDType::Global, run->getId().getType());
    EXPECT_EQ("the app", run->getApplication());
    EXPECT_EQ("1.2.3", run->getVersion());
    EXPECT_EQ("jdoe", run->getUser());
}

}}}
