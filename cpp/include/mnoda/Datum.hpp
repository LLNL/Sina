#ifndef MNODA_DATUM_HPP
#define MNODA_DATUM_HPP

/// @file

#include <string>
#include <type_traits>

#include "mnoda/JsonUtil.hpp"
#include "nlohmann/json.hpp"

namespace mnoda {

/**
 * Represents whether a Datum is a String or Scalar (double).
 */
enum class ValueType {
    String,
    Scalar,
    StringArray,
    ScalarArray
};

/**
 * A Datum tracks the value and (optionally) tags and/or units of a
 * value associated with a Record, e.g. a scalar, a piece of metadata,
 * or an input parameter. In the Mnoda schema, a Datum always
 * belongs to a Record or one of Record's inheriting types.
 *
 * Every Datum must have a value; units and tags are optional.
 *
 * The value of a Datum may be a string, a double, an array of strings,
 * or an array of doubles. 
 *
 * \code
 * mnoda::Datum myDatum{12.34};
 * std::string value = "foobar";
 * mnoda::Datum myOtherDatum{value};
 * std::vector<double> scalars = {1, 2, 20.0};
 * mnoda::Datum myArrayDatum{scalars};
 * //prints 1, corresponding to Scalar
 * std::cout << static_cast<std::underlying_type<mnoda::ValueType>::type>(myDatum.getType()) << std::endl;
 * //prints 0, corresponding to String
 * std::cout << static_cast<std::underlying_type<mnoda::ValueType>::type>(myOtherDatum.getType()) << std::endl;
 * //prints 3, corresponding to ScalarArray
 * std::cout << static_cast<std::underlying_type<mnoda::ValueType>::type>(myArrayDatum.getType()) << std::endl;
 * myRecord->add(myDatum);
 * myOtherDatum.setUnits("km/s");
 * myRecord->add(myOtherDatum);
 * std::vector<std:string> tags = {"input", "core"};
 * myArrayDatum.setTags(tags);
 * myRecord->add(myArrayDatum);
 * \endcode
 */
class Datum {
public:
    /**
     * Construct a new Datum.
     *
     * @param value the string value of the datum
     */
    Datum(std::string value);

    /**
     * Construct a new Datum.
     *
     * @param value the double value of the datum
     */
    Datum(double value);

    /**
     * Construct a new Datum.
     *
     * @param value the string array value of the datum 
     */
    Datum(std::vector<std::string> value);

    /**
     * Construct a new Datum.
     *
     * @param value the scalar array value of the datum 
     */
    Datum(std::vector<double> value);

    /**
     * Construct a Datum from its JSON representation.
     *
     * @param asJson the Datum as JSON
     */
    explicit Datum(nlohmann::json const &asJson);

    /**
     * Get the string value of the Datum.
     *
     * @return the string value
     */
    std::string const &getValue() const noexcept {
            return stringValue;
    }

    /**
     * Get the scalar value of the Datum.
     *
     * @return the scalar value
     */
    double const &getScalar() const noexcept {
            return scalarValue;
    }

    /**
     * Get the string array value of the Datum.
     *
     * @return the string vector value
     */
    std::vector<std::string> const &getStringArray() const noexcept {
            return stringArrayValue;
    }

    /**
     * Get the scalar array value of the Datum.
     *
     * @return the scalar vector value
     */
    std::vector<double> const &getScalarArray() const noexcept {
            return scalarArrayValue;
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
    std::string stringValue;
    double scalarValue;
    std::vector<std::string> stringArrayValue;
    std::vector<double> scalarArrayValue;
    std::string units;
    std::vector<std::string> tags;
    ValueType type;
};

}

#endif //MNODA_DATUM_HPP
