#include <iostream>
#include <stdexcept>
#include <sstream>

#include "mnoda/JsonUtil.hpp"

namespace mnoda {

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
std::string getExpectedString(nlohmann::json const &field,
        std::string const &fieldName,
        std::string const &parentType) {
    if (!field.is_string()) {
        std::ostringstream message;
        message << "The field '" << fieldName
                << "' for objects of type '" << parentType
                << "' must be a string";
        throw std::invalid_argument(message.str());
    }
    return field;
}
}

nlohmann::json const &getRequiredField(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType) {
    auto fieldIter = parent.find(fieldName);
    if (fieldIter == parent.end()) {
        std::ostringstream message;
        message << "The field '" << fieldName
                << "' is required for objects of type '" << parentType << "'";
        throw std::invalid_argument(message.str());
    }
    return *fieldIter;
}

std::string getRequiredString(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType) {
    nlohmann::json const &ref = getRequiredField(fieldName, parent, parentType);
    return getExpectedString(ref, fieldName, parentType);
}

std::string getOptionalString(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType) {
    auto fieldPtr = parent.find(fieldName);
    if (fieldPtr == parent.end() || fieldPtr->is_null()) {
        return "";
    }
    return getExpectedString(*fieldPtr, fieldName, parentType);
}

double getRequiredDouble(std::string const &fieldName,
        nlohmann::json const &parent, std::string const &parentType) {
    auto &ref = getRequiredField(fieldName, parent, parentType);
    if (!ref.is_number()) {
        std::ostringstream message;
        message << "The field '" << fieldName
                << "' for objects of type '" << parentType
                << "' must be a double";
        throw std::invalid_argument(message.str());
    }
    return ref;
}

}
