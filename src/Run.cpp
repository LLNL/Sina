/// @file

#include "mnoda/Run.hpp"

#include <utility>

#include "mnoda/CppBridge.hpp"
#include "mnoda/JsonUtil.hpp"

namespace mnoda {

namespace {
char const RUN_TYPE[] = "run";
char const APPLICATION_FIELD[] = "application";
char const VERSION_FIELD[] = "version";
char const USER_FIELD[] = "user";
}

Run::Run(mnoda::ID id, std::string application_, std::string version_,
        std::string user_) : Record{std::move(id), RUN_TYPE},
                             application{std::move(application_)},
                             version{std::move(version_)},
                             user{std::move(user_)} {}

Run::Run(nlohmann::json const &asJson) :
        Record(asJson),
        application{getRequiredString(APPLICATION_FIELD, asJson, RUN_TYPE)},
        version{getRequiredString(VERSION_FIELD, asJson, RUN_TYPE)},
        user{getRequiredString(USER_FIELD, asJson, RUN_TYPE)} {}

nlohmann::json Run::toJson() const {
    auto asJson = Record::toJson();
    asJson[APPLICATION_FIELD] = application;
    asJson[VERSION_FIELD] = version;
    asJson[USER_FIELD] = user;
    return asJson;
}

void addRunLoader(RecordLoader &loader) {
    loader.addTypeLoader(RUN_TYPE, [](nlohmann::json const &value) {
        return internal::make_unique<Run>(value);
    });
}

}
