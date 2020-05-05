#ifndef SINA_JSONUTIL_HPP
#define SINA_JSONUTIL_HPP

/**
 * @file
 *
 * This file contains utility methods to make working with conduit
 * easier. The functions here also include error reporting with user-friendly
 * messages.
 */

#include <string>

#include "conduit.hpp"

namespace sina {

/**
 * Get a required field from a conduit Node.
 *
 * @param fieldName the name of the field to get
 * @param parent the parent object from which to get the field
 * @param parentType a user-friendly name of the type of the parent to use
 * in an error message if the field doesn't exist.
 * @return the requested field as a Node
 * @throws std::invalid_argument if the field does not exist
 */
conduit::Node const &getRequiredField(std::string const &fieldName,
        conduit::Node const &parent, std::string const &parentType);

/**
 * Get the value of a required field from a conduit Node. The field value
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
        conduit::Node const &parent, std::string const &parentType);

/**
 * Get the value of a required field from a conduit Node. The field value
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
        conduit::Node const &parent, std::string const &parentType);

/**
 * Get the value of an optional field from a conduit Node. The field value
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
        conduit::Node const &parent, std::string const &parentType);

/**
 * Add a vector of strings to a Node. This operation's not natively
 * part of Conduit.
 *
 * @param parent the node to add the strings to
 * @param child_name the name of the child (aka the name of the field)
 * @param string_values the data values for the field
 */
void addStringsToNode(conduit::Node &parent, const std::string &child_name,
      std::vector<std::string> const &string_values);
}

#endif //SINA_JSONUTIL_HPP
