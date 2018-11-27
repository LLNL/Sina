#include "mnoda/testing/TestRecord.hpp"

namespace mnoda { namespace testing {

template<>
TestRecord<std::string>::TestRecord(nlohmann::json const &asJson) :
        Record{asJson},
        value{getRequiredString(TEST_RECORD_VALUE_KEY, asJson, "TestRecord")} {}

template<>
TestRecord<int>::TestRecord(nlohmann::json const &asJson) :
        Record{asJson},
        value{getRequiredField(TEST_RECORD_VALUE_KEY, asJson,
                "TestRecord")} {}

}}
