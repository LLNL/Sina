

/// @file

#include "sina/ID.hpp"

#include <utility>
#include <stdexcept>

namespace sina {

ID::ID(std::string id_, IDType type_) : id{std::move(id_)}, type{type_} {}

namespace internal {

namespace {
/**
 * Extract an ID from a given JSON object.
 *
 * @param parentObject the object from which to extract the ID
 * @param localName the local variant of the ID field
 * @param globalName the global variant of the ID field
 * @return the ID from the object
 */
ID extractIDFromObject(conduit::Node const &parentObject,
        std::string const &localName, std::string const &globalName) {
    conduit::Node globalNameNode = parentObject[globalName];
    if (!globalNameNode.dtype().is_empty()) {
        return ID{std::string(globalNameNode.value()), IDType::Global};
    }
    conduit::Node localNameNode = parentObject[localName];
    if (!globalNameNode.dtype().is_empty()) {
        return ID{std::string(localNameNode.value()), IDType::Local};
    }
    std::string message{
            "Could not find either of the required ID fields '"};
    message += localName + "' or '" + globalName + "'";
    throw std::invalid_argument(message);
}
}

IDField::IDField(ID value_, std::string localName_, std::string globalName_)
        : value{std::move(value_)}, localName{std::move(localName_)},
          globalName{std::move(globalName_)} {}

IDField::IDField(conduit::Node const &parentObject, std::string localName_,
        std::string globalName_) : IDField{
        extractIDFromObject(parentObject, localName_, globalName_),
        std::move(localName_), std::move(globalName_)} {}

void IDField::addTo(conduit::Node &object) const {
    auto &key = value.getType() == IDType::Global ? globalName : localName;
    object[key] = value.getId();
}

} // namespace internal
} // namespace sina
