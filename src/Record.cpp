/// @file

#include "mnoda/Record.hpp"

#include <stdexcept>
#include <utility>

#include "mnoda/CppBridge.hpp"
#include "mnoda/JsonUtil.hpp"
#include "mnoda/Run.hpp"
#include "mnoda/Value.hpp"

namespace {

char const LOCAL_ID_FIELD[] = "local_id";
char const GLOBAL_ID_FIELD[] = "id";
char const VALUES_FIELD[] = "values";
char const TYPE_FIELD[] = "type";
char const FILES_FIELD[] = "files";

}

namespace mnoda {

Record::Record(ID id_, std::string type_) :
        id{std::move(id_), LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{std::move(type_)} {}

nlohmann::json Record::toJson() const {
    nlohmann::json asJson;
    asJson[TYPE_FIELD] = type;
    for (auto &file : files) {
        asJson[FILES_FIELD].emplace_back(file.toJson());
    }
    id.addTo(asJson);
    //Loop through vector of values and append Json
    nlohmann::json valueRef;
    for(auto &value : values)
        valueRef.emplace_back(value.toJson());
    asJson[VALUES_FIELD] = valueRef;
    return asJson;
}

Record::Record(nlohmann::json const &asJson) :
        id{asJson, LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{getRequiredString(TYPE_FIELD, asJson, "record")} {
    auto valuesIter = asJson.find(VALUES_FIELD);
    if(valuesIter != asJson.end()){
        for(auto &value : *valuesIter){
            values.emplace_back(value);
       }
    }
    auto filesIter = asJson.find(FILES_FIELD);
    if (filesIter != asJson.end()) {
        for (auto &file : *filesIter) {
            files.emplace_back(file);
        }
    }
}

void Record::add(Value value) {
    values.emplace_back(std::move(value));
}

void Record::add(File file) {
    files.emplace_back(std::move(file));
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
