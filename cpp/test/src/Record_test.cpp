#include <stdexcept>
#include <typeinfo>

#include "gtest/gtest.h"
#include "gmock/gmock.h"

#include "sina/Record.hpp"
#include "sina/CppBridge.hpp"

#include "sina/testing/ConduitTestUtils.hpp"
#include "sina/testing/TestRecord.hpp"

namespace sina { namespace testing { namespace {

using ::testing::Contains;
using ::testing::ElementsAre;
using ::testing::Key;
using ::testing::HasSubstr;
using ::testing::DoubleEq;
using ::testing::Not;

char const EXPECTED_TYPE_KEY[] = "type";
char const EXPECTED_LOCAL_ID_KEY[] = "local_id";
char const EXPECTED_GLOBAL_ID_KEY[] = "id";
char const EXPECTED_DATA_KEY[] = "data";
char const EXPECTED_LIBRARY_DATA_KEY[] = "library_data";
char const EXPECTED_FILES_KEY[] = "files";
char const EXPECTED_USER_DEFINED_KEY[] = "user_defined";

TEST(Record, create_typeMissing) {
    conduit::Node originalNode;
    originalNode[EXPECTED_LOCAL_ID_KEY] = "the ID";
    try {
        Record record{originalNode};
        FAIL() << "Should have failed due to missing type";
    } catch (std::invalid_argument const &expected) {
        EXPECT_THAT(expected.what(), HasSubstr(EXPECTED_TYPE_KEY));
    }
}

TEST(Record, add_file_existing_key) {
    Record record{ID{"the id", IDType::Local}, "test_record"};
    std::string path = "the/path.txt";

    File original{path};
    original.setMimeType("txt");
    record.add(original);
    EXPECT_EQ(1u, record.getFiles().size());
    EXPECT_EQ("txt", record.getFiles().find(File{path})->getMimeType());

    File replacement{path};
    replacement.setMimeType("image");
    record.add(replacement);
    EXPECT_EQ(1u, record.getFiles().size());
    EXPECT_EQ("image", record.getFiles().find(File{path})->getMimeType());
}

TEST(Record, create_localId_fromNode) {
    conduit::Node originalNode;
    originalNode[EXPECTED_LOCAL_ID_KEY] = "the ID";
    originalNode[EXPECTED_TYPE_KEY] = "my type";
    Record record{originalNode};
    EXPECT_EQ("my type", record.getType());
    EXPECT_EQ("the ID", record.getId().getId());
    EXPECT_EQ(IDType::Local, record.getId().getType());
}

TEST(Record, create_globalId_fromNode) {
    conduit::Node originalNode;
    originalNode[EXPECTED_GLOBAL_ID_KEY] = "the ID";
    originalNode[EXPECTED_TYPE_KEY] = "my type";
    Record record{originalNode};
    EXPECT_EQ("my type", record.getType());
    EXPECT_EQ("the ID", record.getId().getId());
    EXPECT_EQ(IDType::Global, record.getId().getType());
}

TEST(Record, create_globalId_withContent) {
    conduit::Node originalNode;
    originalNode[EXPECTED_GLOBAL_ID_KEY] = "the ID";
    originalNode[EXPECTED_TYPE_KEY] = "my type";
    originalNode[EXPECTED_DATA_KEY];
    originalNode[EXPECTED_LIBRARY_DATA_KEY];

    std::string name1 = "datum name 1";
    conduit::Node name1_node;
    name1_node["value"] = "value 1";
    originalNode[EXPECTED_DATA_KEY][name1] = name1_node;

    std::string libName = "my_lib";
    conduit::Node libNode;
    std::string name2 = "datum name 2";
    conduit::Node name2_node;
    name2_node["value"] = "value 2";
    libNode[EXPECTED_DATA_KEY];
    libNode[EXPECTED_DATA_KEY][name2] = name2_node;
    originalNode[EXPECTED_LIBRARY_DATA_KEY][libName] = libNode;

    Record record{originalNode};
    auto &data = record.getData();
    EXPECT_EQ("value 1", data.at(name1).getValue());
    auto &libdata = record.getLibraryData();
    EXPECT_THAT(libdata, Contains(Key(libName)));
    EXPECT_EQ("value 2", libdata.at(libName).getData().at(name2).getValue());
}

TEST(Record, create_globalId_files) {
    conduit::Node originalNode;
    originalNode[EXPECTED_GLOBAL_ID_KEY] = "the ID";
    originalNode[EXPECTED_TYPE_KEY] = "my type";
    originalNode[EXPECTED_FILES_KEY];

    std::string uri1 = "/some/uri.txt";
    std::string uri2 = "www.anotheruri.com";
    std::string uri3 = "yet another uri";
    originalNode[EXPECTED_FILES_KEY].add_child(uri1);
    originalNode[EXPECTED_FILES_KEY].add_child(uri2);
    originalNode[EXPECTED_FILES_KEY].add_child(uri3);
    Record record{originalNode};
    auto &files = record.getFiles();
    ASSERT_EQ(3u, files.size());
    EXPECT_EQ(1, files.count(File{uri1}));
    EXPECT_EQ(1, files.count(File{uri2}));
    EXPECT_EQ(1, files.count(File{uri3}));
}

TEST(Record, create_fromNode_userDefined) {
    conduit::Node originalNode;
    originalNode[EXPECTED_GLOBAL_ID_KEY] = "the ID";
    originalNode[EXPECTED_TYPE_KEY] = "my type";
    originalNode[EXPECTED_USER_DEFINED_KEY]["k1"] = "v1";
    originalNode[EXPECTED_USER_DEFINED_KEY]["k2"] = 123;
    std::vector<int> k3_vals{1, 2, 3};
    originalNode[EXPECTED_USER_DEFINED_KEY]["k3"] = k3_vals;

    Record record{originalNode};
    auto const &userDefined = record.getUserDefinedContent();
    EXPECT_EQ("v1", userDefined["k1"].as_string());
    EXPECT_EQ(123, userDefined["k2"].as_int());
    auto int_array = userDefined["k3"].as_int_ptr();
    std::vector<double>udef_ints(int_array, int_array+userDefined["k3"].dtype().number_of_elements());
    EXPECT_THAT(udef_ints, ElementsAre(1, 2, 3));
}

TEST(Record, getUserDefined_initialConst) {
    ID id{"the id", IDType::Local};
    Record const record{id, "my type"};
    conduit::Node const &userDefined = record.getUserDefinedContent();
    EXPECT_TRUE(userDefined.dtype().is_empty());
}

TEST(Record, getUserDefined_initialNonConst) {
    ID id{"the id", IDType::Local};
    Record record{id, "my type"};
    conduit::Node &initialUserDefined = record.getUserDefinedContent();
    EXPECT_TRUE(initialUserDefined.dtype().is_empty());
    initialUserDefined["foo"] = 123;
    EXPECT_EQ(123, record.getUserDefinedContent()["foo"].as_int());
}

TEST(Record, toNode_localId) {
    ID id{"the id", IDType::Global};
    Record record{id, "my type"};
    auto asNode = record.toNode();
    EXPECT_TRUE(asNode.dtype().is_object());
    EXPECT_EQ("my type", asNode[EXPECTED_TYPE_KEY].as_string());
    EXPECT_EQ("the id", asNode[EXPECTED_GLOBAL_ID_KEY].as_string());
    EXPECT_TRUE(asNode[EXPECTED_LOCAL_ID_KEY].dtype().is_empty());
}

TEST(Record, toNode_globalId) {
    ID id{"the id", IDType::Local};
    Record record{id, "my type"};
    auto asNode = record.toNode();
    EXPECT_TRUE(asNode.dtype().is_object());
    EXPECT_EQ("my type", asNode[EXPECTED_TYPE_KEY].as_string());
    EXPECT_EQ("the id", asNode[EXPECTED_LOCAL_ID_KEY].as_string());
    EXPECT_TRUE(asNode[EXPECTED_GLOBAL_ID_KEY].dtype().is_empty());
}

TEST(Record, toNode_default_values) {
    ID id{"the id", IDType::Global};
    Record record{id, "my type"};
    auto asNode = record.toNode();
    EXPECT_TRUE(asNode.dtype().is_object());
    // We want to be sure that unset optional fields aren't present
    EXPECT_FALSE(asNode.has_child(EXPECTED_DATA_KEY));
    EXPECT_FALSE(asNode.has_child(EXPECTED_FILES_KEY));
    EXPECT_FALSE(asNode.has_child(EXPECTED_USER_DEFINED_KEY));
}

TEST(Record, toNode_userDefined) {
    ID id{"the id", IDType::Local};
    Record record{id, "my type"};
    conduit::Node userDef;
    userDef["k1"] = "v1";
    userDef["k2"] = 123;
    std::vector<int> int_vals{1, 2, 3};
    userDef["k3"] = int_vals;
    record.setUserDefinedContent(userDef);

    auto asNode = record.toNode();

    auto userDefined = asNode[EXPECTED_USER_DEFINED_KEY];
    EXPECT_EQ("v1", userDefined["k1"].as_string());
    EXPECT_EQ(123, userDefined["k2"].as_int());
    auto int_array = userDefined["k3"].as_int_ptr();
    std::vector<double>udef_ints(int_array, int_array+userDefined["k3"].dtype().number_of_elements());
    EXPECT_THAT(udef_ints, ElementsAre(1, 2, 3));
}

TEST(Record, toNode_files) {
    ID id{"the id", IDType::Local};
    Record record{id, "my type"};
    std::string uri1 = "a/file/path/foo.png";
    std::string uri2 = "uri2";
    File file{uri1};
    file.setMimeType("mt1");
    record.add(file);
    record.add(File{uri2});
    // Identical uris should overwrite
    record.add(File{uri2});
    auto asNode = record.toNode();
    ASSERT_EQ(2u, asNode[EXPECTED_FILES_KEY].number_of_children());
    auto &child_with_slashes = asNode[EXPECTED_FILES_KEY].child(uri1);
    EXPECT_EQ("mt1", child_with_slashes["mimetype"].as_string());
    EXPECT_TRUE(asNode[EXPECTED_FILES_KEY][uri2]["mimetype"].dtype().is_empty());
}

TEST(RecordLoader, load_missingLoader) {
    RecordLoader loader;
    conduit::Node asNode;
    asNode[EXPECTED_GLOBAL_ID_KEY] = "the ID";
    asNode[EXPECTED_TYPE_KEY] = "unknownType";
    auto loaded = loader.load(asNode);
    auto &actualType = typeid(*loaded);
    EXPECT_EQ(typeid(Record), actualType) << "Type was " << actualType.name();
}

TEST(RecordLoader, load_loaderPresent) {
    RecordLoader loader;
    EXPECT_FALSE(loader.canLoad("TestInt"));
    EXPECT_FALSE(loader.canLoad("TestString"));

    loader.addTypeLoader("TestInt",
            [](conduit::Node const &value) {
                return internal::make_unique<TestRecord<int>>(value);
            });
    EXPECT_TRUE(loader.canLoad("TestInt"));

    loader.addTypeLoader("TestString",
            [](conduit::Node const &value) {
                return internal::make_unique<TestRecord<std::string>>(value);
            });
    EXPECT_TRUE(loader.canLoad("TestString"));

    conduit::Node asNode;
    asNode[EXPECTED_GLOBAL_ID_KEY] = "the ID";
    asNode[EXPECTED_TYPE_KEY] = "TestString";
    asNode[TEST_RECORD_VALUE_KEY] = "The value";
    auto loaded = loader.load(asNode);
    auto testObjPointer = dynamic_cast<TestRecord<std::string> *>(loaded.get());
    ASSERT_NE(nullptr, testObjPointer);
    EXPECT_EQ("The value", testObjPointer->getValue());
    EXPECT_EQ("TestString", testObjPointer->getType());
}

TEST(RecordLoader, createRecordLoaderWithAllKnownTypes) {
    RecordLoader loader = createRecordLoaderWithAllKnownTypes();
    EXPECT_TRUE(loader.canLoad("run"));
}

}}}
