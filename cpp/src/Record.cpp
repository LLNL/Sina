/// @file

#include "sina/Record.hpp"

#include <stdexcept>
#include <utility>

#include "sina/CppBridge.hpp"
#include "sina/JsonUtil.hpp"
#include "sina/Run.hpp"
#include "sina/Datum.hpp"

namespace {

char const LOCAL_ID_FIELD[] = "local_id";
char const GLOBAL_ID_FIELD[] = "id";
char const DATA_FIELD[] = "data";
char const TYPE_FIELD[] = "type";
char const FILES_FIELD[] = "files";
char const USER_DEFINED_FIELD[] = "user_defined";

}

namespace sina {

Record::Record(ID id_, std::string type_) :
        id{std::move(id_), LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{std::move(type_)} {}

nlohmann::json Record::toJson() const {
    nlohmann::json asJson;
    asJson[TYPE_FIELD] = type;
    id.addTo(asJson);
    // Optional fields
    if(!files.empty()){
      nlohmann::json fileRef;
      for (auto &file : files) {
          fileRef[file.getUri()] = file.toJson();
      asJson[FILES_FIELD] = fileRef;
      }
    }
    if(!data.empty()){
      //Loop through vector of data and append Json
      nlohmann::json datumRef;
      for(auto &datum : data)
          datumRef[datum.first] = datum.second.toJson();
      asJson[DATA_FIELD] = datumRef;
    }
    if(!userDefined.is_null()){
      asJson[USER_DEFINED_FIELD] = userDefined;
    }
    return asJson;
}

Record::Record(nlohmann::json const &asJson) :
        id{asJson, LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{getRequiredString(TYPE_FIELD, asJson, "record")} {
    auto dataIter = asJson.find(DATA_FIELD);
    if(dataIter != asJson.end()){
        //Loop through DATA_FIELD objects and add them to data:
        for(auto &namedDatum : dataIter->items()){
            data.emplace(std::make_pair(namedDatum.key(), Datum(namedDatum.value())));
        }
    }
    auto filesIter = asJson.find(FILES_FIELD);
    if (filesIter != asJson.end()) {
        for (auto &namedFile : filesIter->items()){
            files.insert(File(namedFile.key(), namedFile.value()));
        }
    }
    auto userDefinedIter = asJson.find(USER_DEFINED_FIELD);
    if (userDefinedIter != asJson.end()) {
        // Enforce that user_defined must be an object
        if (!userDefinedIter->is_object()) {
            throw std::invalid_argument("User_defined must be a JSON object");
        }
        userDefined = *userDefinedIter;
    }
}

void Record::add(std::string name, Datum datum) {
    data.emplace(std::make_pair(name, datum));
}

void Record::add(File file) {
    files.insert(std::move(file));
}

void Record::setUserDefinedContent(nlohmann::json::object_t userDefined_) {
    userDefined = std::move(userDefined_);
}

void RecordLoader::addTypeLoader(std::string const &type, TypeLoader loader) {
    typeLoaders[type] = std::move(loader);
}

std::unique_ptr<Record>
RecordLoader::load(nlohmann::json const &recordAsJson) const {
    auto loaderIter = typeLoaders.find(recordAsJson[TYPE_FIELD]);
    if (loaderIter != typeLoaders.end()) {
        return loaderIter->second(recordAsJson);
    }
    return internal::make_unique<Record>(recordAsJson);
}

bool RecordLoader::canLoad(std::string const &type) const {
    return typeLoaders.count(type) > 0;
}

RecordLoader createRecordLoaderWithAllKnownTypes() {
    RecordLoader loader;
    addRunLoader(loader);
    return loader;
}
}
