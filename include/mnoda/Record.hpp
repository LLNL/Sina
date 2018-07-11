#ifndef MNODA_RECORD_HPP
#define MNODA_RECORD_HPP

/// @file

#include <functional>
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>

#include "nlohmann/json.hpp"

#include "mnoda/ID.hpp"
#include "mnoda/Value.hpp"
#include "mnoda/File.hpp"

namespace mnoda {

/**
 * The Record class represents an entry in a Document's Record list. Records represent the data to be stored
 * (as opposed to the relationships between data)--natural scopes for Records include things like a single run
 * of an application, an msub job, a cluster of runs that has some metadata attached to the cluster (this Record
 * might have a "contains" Relationship for all the runs within it), etc.
 *
 * Each Record must have a type and an id. Each Record can also have a list of
 * Value and File objects.
 *
 * \code
 * mnoda::ID myID{"my_record", mnoda::IDType::Local};
 * std::unique_ptr<mnoda::Record> myRecord{new mnoda::Record{myID, "my_type"}};
 * std::vector<std::string> myTags{"input"};
 * mnoda::Value myValue{"my_scalar", 12, myTags};
 * myRecord->add(std::move(myValue));
 * std::cout << myRecord->toJson() << std::endl;
 * \endcode
 *
 * The output would be:
 * \code{.json} 
 * {"local_id":"my_record","type":"my_type","values":[{"name":"my_scalar","tags":["input"],"value":12.0}]}
 * \endcode
 */
class Record {
public:
    using ValueList = std::vector<Value>;
    using FileList = std::vector<File>;

    /**
     * Construct a new Record.
     *
     * @param id the ID of the record
     * @param type the type of the record
     */
    Record(ID id, std::string type);

    /**
     * Construct a Record from its JSON representation.
     *
     * @param asJson the Record as JSON
     */
    explicit Record(nlohmann::json const &asJson);

    Record(Record const &) = delete;

    Record &operator=(Record const &) = delete;

    /**
     * Get the Record's ID.
     *
     * @return the ID
     */
    ID const &getId() const noexcept {
        return id.getID();
    }

    /**
     * Get the Record's type.
     *
     * @return the Record's type
     */
    std::string const &getType() const noexcept {
        return type;
    }

    /**
     * Get the Record's values.
     *
     * @return the Record's values
     */
    ValueList const &getValues() const noexcept {
        return values;
    }

    /**
     * Add a Value to this record.
     *
     * @param value the Value to add
     */
    void add(Value value);

    /**
     * Add a File to this record.
     *
     * @param file the File to add
     */
    void add(File file);

    /**
     * Get the files associated with this record.
     *
     * @return the record's files
     */
    FileList const &getFiles() const noexcept {
        return files;
    }

    /**
     * Get the user-defined content of the object.
     *
     * @return the user-defined content
     */
    nlohmann::json const &getUserDefinedContent() const noexcept {
        return userDefined;
    }

    /**
     * Get the user-defined content of the object.
     *
     * @return the user-defined content
     */
    nlohmann::json &getUserDefinedContent() noexcept {
        return userDefined;
    }

    /**
     * Set the user-defined content of the object.
     *
     * @param userDefined the user-defined content
     */
    void setUserDefinedContent(nlohmann::json userDefined);

    /**
     * Convert this record to its JSON representation.
     *
     * @return the JSON representation of this record.
     */
    virtual nlohmann::json toJson() const;

    virtual ~Record() = default;

private:
    internal::IDField id;
    std::string type;
    ValueList values;
    FileList files;
    nlohmann::json userDefined;
};


/**
 * A RecordLoader is used to convert Json::Value instances which represent
 * Mnoda Records into instances of their corresponding mnoda::Record
 * subclasses. For convenience, a RecordLoader capable of handling Records of all known
 * types can be created using createRecordLoaderWithAllKnownTypes:
 *
 * \code
 * mnoda::Document myDocument = mnoda::Document(jObj, mnoda::createRecordLoaderWithAllKnownTypes());
 * \endcode
 */
class RecordLoader {
public:
    /**
     * A TypeLoader is a function which converts records of a specific type
     * to their corresponding sub classes.
     */
    using TypeLoader = std::function<std::unique_ptr<Record>(
            nlohmann::json const &)>;

    /**
     * Add a function for loading records of the specified type.
     *
     * @param type the type of records this function can load
     * @param loader the function which can load the records
     */
    void addTypeLoader(std::string const &type, TypeLoader loader);

    /**
     * Load a mnoda::Record from its JSON representation.
     *
     * @param recordAsJson the Record in its JSON representation
     * @return the Record
     */
    std::unique_ptr<Record> load(nlohmann::json const &recordAsJson) const;

    /**
     * Check whether this loader can load records of the given type.
     *
     * @param type the type of the records to check
     * @return whether records of the given type can be loaded
     */
    bool canLoad(std::string const &type) const;

private:
    std::unordered_map<std::string, TypeLoader> typeLoaders;
};

/**
 * Create a RecordLoader which can load records of all known types.
 *
 * @return the newly-created loader
 */
RecordLoader createRecordLoaderWithAllKnownTypes();

}

#endif //MNODA_RECORD_HPP
