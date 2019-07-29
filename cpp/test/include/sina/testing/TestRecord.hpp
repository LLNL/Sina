#ifndef SINA_TESTRECORD_HPP
#define SINA_TESTRECORD_HPP

#include "sina/JsonUtil.hpp"
#include "sina/Record.hpp"

namespace sina { namespace testing {

char constexpr TEST_RECORD_VALUE_KEY[] = "testKey";

/**
 * A TestRecord is a class template that's a subclass of Record and simply
 * stores a value of a specified type.
 *
 * @tparam T the type of the value to store
 */
template<typename T>
class TestRecord : public Record {
public:

    /**
     * Create a new TestRecord.
     *
     * @param id the ID of the record. It is always a global ID.
     * @param type the type of the record
     * @param value the value of the record
     */
    TestRecord(std::string id, std::string type, T value);

    /**
     * Create a new TestRecord from its JSON representation.
     *
     * NOTE: This nees to be implemented explicitly for each type of value
     *
     * @param asValue the record in its JSON representation
     */
    explicit TestRecord(nlohmann::json const &asValue);

    /**
     * Get the record's value.
     *
     * @return the record's value
     */
    const T &getValue() const noexcept {
        return value;
    }

    nlohmann::json toJson() const override;

private:
    T value;
};

template<typename T>
TestRecord<T>::TestRecord(std::string id, std::string type, T value_) :
        Record{ID{std::move(id), IDType::Global}, std::move(type)},
        value{std::move(value_)} {}

template<>
TestRecord<std::string>::TestRecord(nlohmann::json const &asJson);

template<>
TestRecord<int>::TestRecord(nlohmann::json const &asJson);

template<typename T>
nlohmann::json TestRecord<T>::toJson() const {
    auto asJson = Record::toJson();
    asJson[TEST_RECORD_VALUE_KEY] = value;
    return asJson;
}

}}

#endif //SINA_TESTRECORD_HPP
