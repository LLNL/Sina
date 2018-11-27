

/// @file

#include "mnoda/ID.hpp"

#include <utility>
#include <stdexcept>

namespace mnoda {

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
ID extractIDFromObject(nlohmann::json const &parentObject,
        std::string const &localName, std::string const &globalName) {
    auto globalIter = parentObject.find(globalName);
    if (globalIter != parentObject.end()) {
        return ID{*globalIter, IDType::Global};
    }
    auto localIter = parentObject.find(localName);
    if (localIter != parentObject.end()) {
        return ID{*localIter, IDType::Local};
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

IDField::IDField(nlohmann::json const &parentObject, std::string localName_,
        std::string globalName_) : IDField{
        extractIDFromObject(parentObject, localName_, globalName_),
        std::move(localName_), std::move(globalName_)} {}

void IDField::addTo(nlohmann::json &object) const {
    auto &key = value.getType() == IDType::Global ? globalName : localName;
    object[key] = value.getId();
}

} // namespace internal
} // namespace mnoda
