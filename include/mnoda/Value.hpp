#ifndef MNODA_VALUE_HPP
#define MNODA_VALUE_HPP

/// @file

#include <string>
#include <type_traits>

#include "mnoda/JsonUtil.hpp"
#include "nlohmann/json.hpp"

namespace mnoda {

/**
 * Represents whether an Value is a Value (string) or Scalar (double).
 */
enum class ValueType {
    Value,
    Scalar
};

/**
 * A Value tracks the name, value, and (optionally) tags and/or units of a
 * value associated with a Record, e.g. a scalar, a piece of metadata,
 * or an input parameter. In the Mnoda schema, a Value always
 * belongs to a Record or one of Record's inheriting types.
 *
 * Every Value must have a name and value; units and tags are optional. 
 *
 * The value of a Value may be either a string or a double.
 *
 * \code
 * mnoda::Value myValue{"my_val", 12.34};
 * mnoda::Value myOtherValue{"my_other_val", "foobar"};
 * //prints 1, corresponding to Scalar
 * std::cout << static_cast<std::underlying_type<mnoda::ValueType>::type>(myValue.getType()) << std::endl;
 * //prints 0, corresponding to Value 
 * std::cout << static_cast<std::underlying_type<mnoda::ValueType>::type>(myOtherValue.getType()) << std::endl;
 * myRecord->add(myValue);
 * myOtherValue.setUnits("km/s");
 * myRecord->add(myOtherValue);
 * \endcode
 */
class Value {
public:
    /**
     * Construct a new Value.
     *
     * @param name the name of the Value
     * @param value the string value relating to the key
     * @param units (optional) the units the Value is represented in (ex: km/h) 
     * @param tags (optional) array of strings representing tags for the Value
     */
    Value(std::string name, std::string value, std::string units = std::string(), std::vector< std::string > tags = {});

    /**
     * Construct a new Value.
     *
     * @param name the name of the Value
     * @param value the double value relating to the key
     * @param units (optional) the units the Value is represented in (ex: km/h) 
     * @param tags (optional) array of strings representing tags for the Value
     */
    Value(std::string name, double value, std::string units = std::string(), std::vector< std::string > tags = {});

    /**
     * Construct a Value from its JSON representation.
     *
     * @param asJson the Value as JSON
     */
    explicit Value(nlohmann::json const &asJson);

    /**
     * Get the value of the Value.
     *
     * @return the string value
     */
    std::string const &getValue() const noexcept {
            return stringValue;
    }

    /**
     * Get the scalar of the Value.
     *
     * @return the scalar value
     */
    double const &getScalar() const noexcept {
            return scalarValue;
    }

    /**
     * Get the name of the Value.
     *
     * @return the name of the value
     */
    std::string const &getName() const noexcept {
        return name;
    }

    /**
     * Get the tags of the Value
     *
     * @return the tags of the value
     */
    std::vector<std::string> const &getTags() const noexcept {
        return tags;
    }

    /** 
     * Get the units of the Value
     *
     * @return the units of the value
     */
    std::string getUnits() const noexcept {
        return units;
    } 

    /**
     * Set the units of the Value
     *
     * @param units the units of the value
     */
    void setUnits(std::string units);
    

    /**
     * Get the type of the Value
     *
     * @return the tags of the value
     */
    ValueType getType() const noexcept {
        return type;
    }

    /**
     * Convert this value to its JSON representation.
     *
     * @return the JSON representation of this value.
     */
    nlohmann::json toJson() const;
private:
    std::string name;
    std::string stringValue;
    double scalarValue;
    std::string units;
    std::vector<std::string> tags;
    ValueType type;
};

}

#endif //MNODA_RECORD_HPP
