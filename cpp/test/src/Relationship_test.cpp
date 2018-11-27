#include <stdexcept>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "mnoda/Relationship.hpp"

namespace mnoda { namespace testing { namespace {

char const EXPECTED_GLOBAL_OBJECT_ID_KEY[] = "object";
char const EXPECTED_LOCAL_OBJECT_ID_KEY[] = "local_object";
char const EXPECTED_GLOBAL_SUBJECT_ID_KEY[] = "subject";
char const EXPECTED_LOCAL_SUBJECT_ID_KEY[] = "local_subject";
char const EXPECTED_PREDICATE_KEY[] = "predicate";

using ::testing::HasSubstr;

TEST(Relationship, create) {
    std::string subjectID = "the subject";
    std::string objectID = "the object";
    std::string predicate = "is somehow related to";

    Relationship relationship{ID{subjectID, IDType::Global}, predicate,
                              ID{objectID, IDType::Local}};

    EXPECT_EQ(subjectID, relationship.getSubject().getId());
    EXPECT_EQ(IDType::Global, relationship.getSubject().getType());
    EXPECT_EQ(objectID, relationship.getObject().getId());
    EXPECT_EQ(IDType::Local, relationship.getObject().getType());
    EXPECT_EQ(predicate, relationship.getPredicate());
}

TEST(Relationship, create_fromJson_validGlobalIDs) {
    std::string subjectID = "the subject";
    std::string objectID = "the object";
    std::string predicate = "is somehow related to";

    nlohmann::json asJson{
            {EXPECTED_GLOBAL_SUBJECT_ID_KEY, subjectID},
            {EXPECTED_GLOBAL_OBJECT_ID_KEY, objectID},
            {EXPECTED_PREDICATE_KEY, predicate}
    };

    Relationship relationship{asJson};

    EXPECT_EQ(subjectID, relationship.getSubject().getId());
    EXPECT_EQ(IDType::Global, relationship.getSubject().getType());
    EXPECT_EQ(objectID, relationship.getObject().getId());
    EXPECT_EQ(IDType::Global, relationship.getObject().getType());
    EXPECT_EQ(predicate, relationship.getPredicate());
}

TEST(Relationship, create_fromJson_validLocalIDs) {
    std::string subjectID = "the subject";
    std::string objectID = "the object";
    std::string predicate = "is somehow related to";

    nlohmann::json asJson{
            {EXPECTED_LOCAL_SUBJECT_ID_KEY, subjectID},
            {EXPECTED_LOCAL_OBJECT_ID_KEY, objectID},
            {EXPECTED_PREDICATE_KEY, predicate}
    };

    Relationship relationship{asJson};

    EXPECT_EQ(subjectID, relationship.getSubject().getId());
    EXPECT_EQ(IDType::Local, relationship.getSubject().getType());
    EXPECT_EQ(objectID, relationship.getObject().getId());
    EXPECT_EQ(IDType::Local, relationship.getObject().getType());
    EXPECT_EQ(predicate, relationship.getPredicate());
}

TEST(Relationship, create_fromJson_missingSubect) {
    nlohmann::json asJson{
            {EXPECTED_LOCAL_OBJECT_ID_KEY, "the object"},
            {EXPECTED_PREDICATE_KEY, "some predicate"}
    };

    try {
        Relationship relationship{asJson};
        FAIL() << "Should have gotten an exception about a missing subject";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_LOCAL_SUBJECT_ID_KEY));
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_GLOBAL_SUBJECT_ID_KEY));
    }
}

TEST(Relationship, create_fromJson_missingObject) {
    nlohmann::json asJson{
            {EXPECTED_LOCAL_SUBJECT_ID_KEY, "the subject"},
            {EXPECTED_PREDICATE_KEY, "some predicate"}
    };

    try {
        Relationship relationship{asJson};
        FAIL() << "Should have gotten an exception about a missing object";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_LOCAL_OBJECT_ID_KEY));
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_GLOBAL_OBJECT_ID_KEY));
    }
}

TEST(Relationship, create_fromJson_missingPredicate) {
    nlohmann::json asJson{
            {EXPECTED_LOCAL_SUBJECT_ID_KEY, "the subject"},
            {EXPECTED_LOCAL_OBJECT_ID_KEY, "the object"}
    };

    try {
        Relationship relationship{asJson};
        FAIL() << "Should have gotten an exception about a missing predicate";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_PREDICATE_KEY));
        EXPECT_THAT(expected.what(), HasSubstr("Relationship"));
    }
}

TEST(Relationship, toJson_localIds) {
    std::string subjectID = "the subject";
    std::string objectID = "the object";
    std::string predicate = "is somehow related to";

    Relationship relationship{ID{subjectID, IDType::Local}, predicate,
                              ID{objectID, IDType::Local}};

    nlohmann::json asJson = relationship.toJson();

    EXPECT_EQ(subjectID, asJson[EXPECTED_LOCAL_SUBJECT_ID_KEY]);
    EXPECT_EQ(objectID, asJson[EXPECTED_LOCAL_OBJECT_ID_KEY]);
    EXPECT_EQ(predicate, asJson[EXPECTED_PREDICATE_KEY]);
    EXPECT_EQ(0, asJson.count(EXPECTED_GLOBAL_SUBJECT_ID_KEY));
    EXPECT_EQ(0, asJson.count(EXPECTED_GLOBAL_OBJECT_ID_KEY));
}

TEST(Relationship, toJson_globalIds) {
    std::string subjectID = "the subject";
    std::string objectID = "the object";
    std::string predicate = "is somehow related to";

    Relationship relationship{ID{subjectID, IDType::Global}, predicate,
                              ID{objectID, IDType::Global}};

    nlohmann::json asJson = relationship.toJson();

    EXPECT_EQ(subjectID, asJson[EXPECTED_GLOBAL_SUBJECT_ID_KEY]);
    EXPECT_EQ(objectID, asJson[EXPECTED_GLOBAL_OBJECT_ID_KEY]);
    EXPECT_EQ(predicate, asJson[EXPECTED_PREDICATE_KEY]);
    EXPECT_EQ(0, asJson.count(EXPECTED_LOCAL_SUBJECT_ID_KEY));
    EXPECT_EQ(0, asJson.count(EXPECTED_LOCAL_OBJECT_ID_KEY));
}

}}}
