#ifndef MNODA_RUN_HPP
#define MNODA_RUN_HPP

/// @file

#include "mnoda/Record.hpp"

namespace mnoda {

/**
 * A Run is a subtype of Record corresponding to a single run of an application, as
 * specified in the Mnoda schema. A Run has a few additional fields required in addition
 * to the id required by a Record (type is automatically set to "run"):
 *
 *  - application: the application/code used to create the Run
 *  - version: the version of the application used to create the Run
 *  - user: the username of the person who ran the application that generated this Run
 *
 * To create a Run:
 * \code
 * mnoda::ID run1ID{"run1", mnoda::IDType::Local};
 * std::unique_ptr<mnoda::Record> run1{new mnoda::Run{run1ID, "My Sim Code", "1.2.3", "jdoe"}};
 * \endcode
 *
 */
class Run : public Record {
public:
    /**
     * Create a new Run.
     *
     * @param id the run's ID
     * @param application the application that was run
     * @param version the version of the application
     * @param user the user who executed the run
     */
    Run(ID id, std::string application, std::string version, std::string user);

    /**
     * Create a Run from its representation as a Json object
     *
     * @param asJson the run as a Json object
     */
    explicit Run(nlohmann::json const &asJson);

    /**
     * Get the application that was run.
     *
     * @return the application's name
     */
    std::string const &getApplication() const {
        return application;
    }

    /**
     * Get the version of the application that was run.
     *
     * @return the application's version
     */
    std::string const &getVersion() const {
        return version;
    }

    /**
     * Get the name of the user who ran the application.
     *
     * @return the user's name
     */
    std::string const &getUser() const {
        return user;
    }

    nlohmann::json toJson() const override;

private:
    std::string application;
    std::string version;
    std::string user;
};

/**
 * Add a type loader to the given RecordLoader for loading Run instances.
 *
 * @param loader the RecordLoader to which to add the function for loading
 * Run instances.
 */
void addRunLoader(RecordLoader &loader);

}


#endif //MNODA_RUN_HPP
