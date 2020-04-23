#include <iostream>
#include <stdexcept>
#include <sstream>
#include <string>
#include <vector>

#include "sina/ConduitUtil.hpp"
#include "conduit/conduit.hpp"

namespace sina {

namespace {
/**
 * Get the given field as string. If it is not a string, an exception is
 * thrown with a user-friendly message.
 *
 * @param field the value of the field
 * @param fieldName the name of the field
 * @param parentType the name of the parent which contained the field
 * @return the avlue of the field
 * @throws std::invalid_argument if the field is not a string
 */
std::string getExpectedString(conduit::Node const &field,
        std::string const &fieldName,
        std::string const &parentType) {
    if (!field.dtype().is_string()) {
        std::ostringstream message;
        message << "The field '" << fieldName
                << "' for objects of type '" << parentType
                << "' must be a string, was '"
                << field.dtype().name() << "'";
        throw std::invalid_argument(message.str());
    }
    return field.as_string();
}
}

conduit::Node const &getRequiredField(std::string const &fieldName,
        conduit::Node const &parent, std::string const &parentType) {
    if (!parent.has_child(fieldName)) {
        std::ostringstream message;
        message << "The field '" << fieldName
                << "' is required for objects of type '" << parentType << "'";
        throw std::invalid_argument(message.str());
    }
    return parent[fieldName];
}

std::string getRequiredString(std::string const &fieldName,
        conduit::Node const &parent, std::string const &parentType) {
    conduit::Node const &field = getRequiredField(fieldName, parent, parentType);
    return getExpectedString(field, fieldName, parentType);
}

std::string getOptionalString(std::string const &fieldName,
        conduit::Node const &parent, std::string const &parentType) {
    if (!parent.has_child(fieldName)) {
        return "";
    }
    return getExpectedString(parent[fieldName], fieldName, parentType);
}

double getRequiredDouble(std::string const &fieldName,
        conduit::Node const &parent, std::string const &parentType) {
    auto &ref = getRequiredField(fieldName, parent, parentType);
    if (!ref.dtype().is_number()) {
        std::ostringstream message;
        message << "The field '" << fieldName
                << "' for objects of type '" << parentType
                << "' must be a double";
        throw std::invalid_argument(message.str());
    }
    return ref.as_double();
}

void addStringsToNode(const conduit::Node &parent, const std::string &child_name,
      std::vector<std::string> string_values){
  for(auto &value : string_values)
  {
      auto &list_entry = parent[child_name].append();
      list_entry.set(value);
  }
}

}
