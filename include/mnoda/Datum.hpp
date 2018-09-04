#ifndef MNODA_DATUM_HPP
#define MNODA_DATUM_HPP

/// @file

#include <string>
#include <type_traits>

#include "mnoda/JsonUtil.hpp"
#include "nlohmann/json.hpp"

namespace mnoda {

/**
 * Represents whether an Datum is a Value (string) or Scalar (double).
 */
enum class ValueType {
    Value,
    Scalar
};

/**
 * A Datum tracks the name, value, and (optionally) tags and/or units of a
 * value associated with a Record, e.g. a scalar, a piece of metadata,
 * or an input parameter. In the Mnoda schema, a Datum always
 * belongs to a Record or one of Record's inheriting types.
 *
 * Every Datum must have a name and value; units and tags are optional.
 *
 * The value of a Datum may be either a string or a double.
 *
 * \code
 * mnoda::Datum myDatum{"my_scalar", 12.34};
 * mnoda::Datum myOtherDatum{"my_value", "foobar"};
 * //prints 1, corresponding to Scalar
 * std::cout << static_cast<std::underlying_type<mnoda::ValueType>::type>(myDatum.getType()) << std::endl;
 * //prints 0, corresponding to Value
 * std::cout << static_cast<std::underlying_type<mnoda::ValueType>::type>(myOtherDatum.getType()) << std::endl;
 * myRecord->add(myDatum);
 * myOtherDatum.setUnits("km/s");
 * myRecord->add(myOtherDatum);
 * \endcode
 */
class Datum {
public:
    /**
     * Construct a new Datum.
     *
     * @param name the name of the Datum
     * @param value the string value relating to the key
     */
    Datum(std::string name, std::string value);

    /**
     * Construct a new Datum.
     *
     * @param name the name of the Datum
     * @param value the double value relating to the key
     */
    Datum(std::string name, double value);

    /**
     * Construct a Datum from its JSON representation.
     *
     * @param asJson the Datum as JSON
     */
    explicit Datum(nlohmann::json const &asJson);

    /**
     * Get the value of the Datum.
     *
     * @return the string value
     */
    std::string const &getValue() const noexcept {
            return stringValue;
    }

    /**
     * Get the scalar of the Datum.
     *
     * @return the scalar value
     */
    double const &getScalar() const noexcept {
            return scalarValue;
    }

    /**
     * Get the name of the Datum.
     *
     * @return the name of the value
     */
    std::string const &getName() const noexcept {
        return name;
    }

    /**
     * Get the tags of the Datum
     *
     * @return the tags of the value
     */
    std::vector<std::string> const &getTags() const noexcept {
        return tags;
    }

    /**
     * Set the tags of the Datum
     *
     * @param tags the tags of the value
     */
    void setTags(std::vector<std::string> tags);

    /**
     * Get the units of the Datum
     *
     * @return the units of the value
     */
    std::string const &getUnits() const noexcept {
        return units;
    }

    /**
     * Set the units of the Datum
     *
     * @param units the units of the value
     */
    void setUnits(std::string units);


    /**
     * Get the type of the Datum
     *
     * @return the type of the value
     */
    ValueType getType() const noexcept {
        return type;
    }

    /**
     * Convert this Datum to its JSON representation.
     *
     * @return the JSON representation of this Datum.
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

#endif //MNODA_DATUM_HPP
