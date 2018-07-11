#include <cstdio>
#include <fstream>
#include <iostream>
#include <type_traits>
#include <utility>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "mnoda/CppBridge.hpp"
#include "mnoda/Document.hpp"
#include "mnoda/Run.hpp"

#include "mnoda/testing/TestRecord.hpp"

namespace mnoda { namespace testing { namespace {

using ::testing::ElementsAre;
using ::testing::HasSubstr;

char const TEST_RECORD_TYPE[] = "test type";
char const EXPECTED_RECORDS_KEY[] = "records";
char const EXPECTED_RELATIONSHIPS_KEY[] = "relationships";

TEST(Document, create_fromJson_empty) {
    nlohmann::json documentAsJson;
    RecordLoader loader;
    Document document{documentAsJson, loader};
    EXPECT_EQ(0u, document.getRecords().size());
    EXPECT_EQ(0u, document.getRelationships().size());
}

TEST(Document, create_fromJson_wrongRecordsType) {
    nlohmann::json recordsAsJson{
            {EXPECTED_RECORDS_KEY, "123"}
    };
    RecordLoader loader;
    try {
        Document document{recordsAsJson, loader};
        FAIL() << "Should not have been able to parse records. Have "
               << document.getRecords().size();
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_RECORDS_KEY));
    }
}

TEST(Document, create_fromJson_withRecords) {
    nlohmann::json recordAsJson{
            {"type", "IntTestRecord"},
            {"id", "the ID"},
            {TEST_RECORD_VALUE_KEY, 123}
    };

    nlohmann::json recordsAsJson;
    recordsAsJson.emplace_back(recordAsJson);

    nlohmann::json documentAsJson;
    documentAsJson[EXPECTED_RECORDS_KEY] = recordsAsJson;

    RecordLoader loader;
    loader.addTypeLoader("IntTestRecord", [](nlohmann::json const &asJson) {
        return internal::make_unique<TestRecord<int>>(asJson);
    });

    Document document{documentAsJson, loader};
    auto &records = document.getRecords();
    ASSERT_EQ(1u, records.size());
    auto testRecord = dynamic_cast<TestRecord<int> const *>(records[0].get());
    ASSERT_NE(nullptr, testRecord);
    ASSERT_EQ(123, testRecord->getValue());
}

TEST(Document, create_fromJson_withRelationships) {
    nlohmann::json relationshipAsJson{
            {"subject", "the subject"},
            {"object", "the object"},
            {"predicate", "is related to"},
    };

    nlohmann::json relationshipsAsJson;
    relationshipsAsJson.emplace_back(relationshipAsJson);

    nlohmann::json documentAsJson{
            {EXPECTED_RELATIONSHIPS_KEY, relationshipsAsJson}
    };

    Document document{documentAsJson, RecordLoader{}};
    auto &relationships = document.getRelationships();
    ASSERT_EQ(1u, relationships.size());
    EXPECT_EQ("the subject", relationships[0].getSubject().getId());
    EXPECT_EQ(IDType::Global, relationships[0].getSubject().getType());
    EXPECT_EQ("the object", relationships[0].getObject().getId());
    EXPECT_EQ(IDType::Global, relationships[0].getObject().getType());
    EXPECT_EQ("is related to", relationships[0].getPredicate());
}

TEST(Document, toJson_empty) {
    Document const document;
    nlohmann::json asJson = document.toJson();
    EXPECT_EQ(nlohmann::json::value_t::null, asJson[EXPECTED_RECORDS_KEY]);
    EXPECT_EQ(nlohmann::json::value_t::null,
            asJson[EXPECTED_RELATIONSHIPS_KEY]);
}

TEST(Document, toJson_records) {
    Document document;
    std::string expectedIds[] = {"id 1", "id 2", "id 3"};
    std::string expectedValues[] = {"value 1", "value 2", "value 3"};

    auto numRecords = sizeof(expectedIds) / sizeof(expectedIds[0]);
    for (std::size_t i = 0; i < numRecords; ++i) {
        document.add(internal::make_unique<TestRecord<std::string>>(
                expectedIds[i], TEST_RECORD_TYPE, expectedValues[i]));
    }

    auto asJson = document.toJson();

    auto records = asJson[EXPECTED_RECORDS_KEY];
    ASSERT_EQ(numRecords, records.size());
    for (std::size_t i = 0; i < numRecords; ++i) {
        auto &actualRecord = records[i];
        EXPECT_EQ(expectedIds[i], actualRecord["id"]);
        EXPECT_EQ(TEST_RECORD_TYPE, actualRecord["type"]);
        EXPECT_EQ(expectedValues[i], actualRecord[TEST_RECORD_VALUE_KEY]);
    }
}

TEST(Document, toJson_relationships) {
    Document document;
    std::string expectedSubjects[] = {"subject 1", "subject 2"};
    std::string expectedObjects[] = {"object 1", "object 2"};
    std::string expectedPredicates[] = {"predicate 1", "predicate 2"};

    auto numRecords = sizeof(expectedSubjects) / sizeof(expectedSubjects[0]);
    for (std::size_t i = 0; i < numRecords; ++i) {
        document.add(Relationship{
                ID{expectedSubjects[i], IDType::Global},
                expectedPredicates[i],
                ID{expectedObjects[i], IDType::Global},
        });
    }

    auto asJson = document.toJson();

    auto relationships = asJson[EXPECTED_RELATIONSHIPS_KEY];
    ASSERT_EQ(numRecords, relationships.size());
    for (std::size_t i = 0; i < numRecords; ++i) {
        auto &actualRelationship = relationships[i];
        EXPECT_EQ(expectedSubjects[i], actualRelationship["subject"]);
        EXPECT_EQ(expectedObjects[i], actualRelationship["object"]);
        EXPECT_EQ(expectedPredicates[i], actualRelationship["predicate"]);
    }
}

/**
 * Instances of this class acquire a temporary file name when created
 * and delete the file when destructed.
 *
 * NOTE: This class uses unsafe methods and should only be used for testing
 * purposes. DO NOT move it to the main code!!!!
 */
class NamedTempFile {
public:
    NamedTempFile();

    // As a resource-holding class, we don't want this to be copyable
    // (or movable since there is no reason to return it from a function)
    NamedTempFile(NamedTempFile const &) = delete;

    NamedTempFile(NamedTempFile &&) = delete;

    NamedTempFile &operator=(NamedTempFile const &) = delete;

    NamedTempFile &operator=(NamedTempFile &&) = delete;

    ~NamedTempFile();

    std::string const &getName() const {
        return fileName;
    }

private:
    std::string fileName;
};

NamedTempFile::NamedTempFile() {
    std::vector<char> tmpFileName;
    tmpFileName.resize(L_tmpnam);
    // tmpnam is not the best way to do this, but it is standard and this is
    // only a test.
    if (!std::tmpnam(tmpFileName.data())) {
        throw std::ios::failure{"Could not get temporary file"};
    }
    fileName = tmpFileName.data();
}

NamedTempFile::~NamedTempFile() {
    std::remove(fileName.data());
}

TEST(Document, saveDocument) {
    NamedTempFile tmpFile;

    // First, write some random stuff to the temp file to make sure it is
    // overwritten.
    {
        std::ofstream fout{tmpFile.getName()};
        fout << "Initial contents";
    }

    Document document;
    document.add(internal::make_unique<Record>(ID{"the id", IDType::Global},
            "the type"));

    saveDocument(document, tmpFile.getName());

    nlohmann::json readContents;
    {
        std::ifstream fin{tmpFile.getName()};
        fin >> readContents;
    }

    ASSERT_TRUE(readContents[EXPECTED_RECORDS_KEY].is_array());
    EXPECT_EQ(1, readContents[EXPECTED_RECORDS_KEY].size());
    auto &readRecord = readContents[EXPECTED_RECORDS_KEY][0];
    EXPECT_EQ("the id", readRecord["id"]);
    EXPECT_EQ("the type", readRecord["type"]);
}

TEST(Document, load_secifiedRecordLoader) {
    using RecordType = TestRecord<int>;
    auto originalRecord = internal::make_unique<RecordType>(
            "the ID", "my type", 123);
    Document originalDocument;
    originalDocument.add(std::move(originalRecord));

    NamedTempFile file;
    {
        std::ofstream fout{file.getName()};
        fout << originalDocument.toJson();
    }

    RecordLoader loader;
    loader.addTypeLoader("my type", [](nlohmann::json const &asJson) {
        return internal::make_unique<RecordType>(
                getRequiredString("id", asJson, "Test type"),
                getRequiredString("type", asJson, "Test type"),
                getRequiredField(TEST_RECORD_VALUE_KEY, asJson,
                        "Test type"));
    });
    Document loadedDocument = loadDocument(file.getName(), loader);
    ASSERT_EQ(1u, loadedDocument.getRecords().size());
    auto loadedRecord = dynamic_cast<RecordType const *>(
            loadedDocument.getRecords()[0].get());
    ASSERT_NE(nullptr, loadedRecord);
    EXPECT_EQ(123, loadedRecord->getValue());
}

TEST(Document, load_defaultRecordLoaders) {
    auto originalRun = internal::make_unique<mnoda::Run>(
            ID{"the ID", IDType::Global}, "the app", "1.2.3", "jdoe");
    Document originalDocument;
    originalDocument.add(std::move(originalRun));

    NamedTempFile file;
    {
        std::ofstream fout{file.getName()};
        fout << originalDocument.toJson();
    }

    Document loadedDocument = loadDocument(file.getName());
    ASSERT_EQ(1u, loadedDocument.getRecords().size());
    auto loadedRun = dynamic_cast<mnoda::Run const *>(
            loadedDocument.getRecords()[0].get());
    EXPECT_NE(nullptr, loadedRun);
}
}}}
