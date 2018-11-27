#ifndef MNODA_ID_HPP
#define MNODA_ID_HPP

/**
 * @file
 *
 * The Mnoda schema allows records to have either a local ID or a global ID.
 * When a global ID is specified, that will be used in the database. When a
 * local ID is specified, an ID will be automatically generated when inserting
 * the record into the database.
 */

#include <string>

#include "nlohmann/json.hpp"

namespace mnoda {

/**
 * Represents whether an ID is local or global.
 */
enum class IDType {
    Local,
    Global
};

/**
 * An ID is used to represent the ID of an record. This class holds both the
 * actual ID and whether it is a local or global ID.
 */
class ID {
public:
    /**
     * Create a new ID.
     * @param id the actual value of the ID
     * @param type whether the ID is local or global
     */
    ID(std::string id, IDType type);

    /**
     * Get the value of the ID.
     *
     * @return the actual ID
     */
    std::string const &getId() const noexcept {
        return id;
    }

    /**
     * Get the type of the ID.
     *
     * @return whether the ID is local or global
     */
    IDType getType() const noexcept {
        return type;
    }

private:
    std::string id;
    IDType type;
};

namespace internal {

/**
 * IDField instances are used to describe a pair of ID fields in a schema
 * object which correspond to global and local names for the field. For
 * example, the "id" and "local_id" fields in records, or the
 * "subject"/"local_subject" and "object"/"local_object" pairs in
 * relationships.
 */
class IDField {
public:
    /**
     * Construct a new IDField.
     *
     * @param value the value of the ID
     * @param localName the name of the local variant of the field
     * @param globalName the name of the global variant of the field
     */
    IDField(ID value, std::string localName, std::string globalName);

    /**
     * Construct an IDField by looking for its values in a JSON object.
     *
     * @param parentObject the JSON object containing the ID field
     * @param localName the local name of the field
     * @param globalName the global name of the field
     */
    IDField(nlohmann::json const &parentObject, std::string localName,
            std::string globalName);

    /**
     * Get the value of this field.
     *
     * @return the ID describing the field's value
     */
    ID const &getID() const noexcept {
        return value;
    }

    /**
     * Get the name to use for this field when the ID is local.
     *
     * @return the name of the local ID field
     */
    std::string const &getLocalName() const noexcept {
        return localName;
    }

    /**
     * Get the name to use for this field when the ID is global.
     *
     * @return the name of the global ID field
     */
    std::string const &getGlobalName() const noexcept {
        return globalName;
    }

    /**
     * Add this field to the given JSON object.
     *
     * @param object the JSON object to which to add the field
     */
    void addTo(nlohmann::json &object) const;

private:
    ID value;
    std::string localName;
    std::string globalName;
};

} // namespace internal

} // namespace mnoda

#endif //MNODA_ID_HPP
