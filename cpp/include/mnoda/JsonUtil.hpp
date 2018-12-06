#ifndef MNODA_JSONUTIL_HPP
#define MNODA_JSONUTIL_HPP

/**
 * @file
 *
 * This file contains utility methods to make working with the JSON library
 * easier. The functions here also include error reporting with user-friendly
 * messages.
 */

#include <string>

#include "nlohmann/json.hpp"

namespace mnoda {

/**
 * Get a required field from the a JSON value.
 *
 * @param fieldName the name of the field to get
 * @param parent the parent object from which to get the field
 * @param parentType a user-friendly name of the type of the parent to use
 * in an error message if the field doesn't exist.
 * @return the requested field
 * @throws std::invalid_argument if the field does not exist
 */
nlohmann::json const &getRequiredField(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType);

/**
 * Get the value of a required field from the a JSON value. The field value
 * must be a string.
 *
 * @param fieldName the name of the field to get
 * @param parent the parent object from which to get the field
 * @param parentType a user-friendly name of the type of the parent to use
 * in an error message if the field doesn't exist.
 * @return the value of the requested field
 * @throws std::invalid_argument if the field does not exist or is not a string
 */
std::string getRequiredString(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType);

/**
 * Get the value of a required field from the a JSON value. The field value
 * must be a double.
 *
 * @param fieldName the name of the field to get
 * @param parent the parent object from which to get the field
 * @param parentType a user-friendly name of the type of the parent to use
 * in an error message if the field doesn't exist.
 * @return the value of the requested field
 * @throws std::invalid_argument if the field does not exist or is not a double
 */
double getRequiredDouble(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType);

/**
 * Get the value of an optional field from the a JSON value. The field value
 * must be a string if it is present.
 *
 * @param fieldName the name of the field to get
 * @param parent the parent object from which to get the field
 * @param parentType a user-friendly name of the type of the parent to use
 * in an error message if the field doesn't exist.
 * @return the value of the requested field, or an empty string if it
 * does not exist
 * @throws std::invalid_argument if the field exists but is not a string
 */
std::string getOptionalString(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType);
}

#endif //MNODA_JSONUTIL_HPP
