#ifndef SINA_TESTRECORD_HPP
#define SINA_TESTRECORD_HPP

#include "sina/ConduitUtil.hpp"
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
     * Create a new TestRecord from its conduit Node representation.
     *
     * NOTE: This needs to be implemented explicitly for each type of value
     *
     * @param asValue the record in its Node representation
     */
    explicit TestRecord(conduit::Node const &asValue);

    /**
     * Get the record's value.
     *
     * @return the record's value
     */
    const T &getValue() const noexcept {
        return value;
    }

    conduit::Node toNode() const override;

private:
    T value;
};

template<typename T>
TestRecord<T>::TestRecord(std::string id, std::string type, T value_) :
        Record{ID{std::move(id), IDType::Global}, std::move(type)},
        value{std::move(value_)} {}

template<>
TestRecord<std::string>::TestRecord(conduit::Node const &asNode);

template<>
TestRecord<int>::TestRecord(conduit::Node const &asJson);

template<typename T>
conduit::Node TestRecord<T>::toNode() const {
    auto asJson = Record::toNode();
    asJson[TEST_RECORD_VALUE_KEY] = value;
    return asJson;
}

}}

#endif //SINA_TESTRECORD_HPP
