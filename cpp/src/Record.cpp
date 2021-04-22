/// @file

#include "sina/Record.hpp"

#include <stdexcept>
#include <utility>

#include "sina/CppBridge.hpp"
#include "sina/ConduitUtil.hpp"
#include "sina/Run.hpp"
#include "sina/Datum.hpp"

namespace {

char const LOCAL_ID_FIELD[] = "local_id";
char const GLOBAL_ID_FIELD[] = "id";
char const DATA_FIELD[] = "data";
char const CURVE_SETS_FIELD[] = "curve_sets";
char const TYPE_FIELD[] = "type";
char const FILES_FIELD[] = "files";
char const USER_DEFINED_FIELD[] = "user_defined";

}

namespace sina {

Record::Record(ID id_, std::string type_) :
        id{std::move(id_), LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{std::move(type_)} {}

conduit::Node Record::toNode() const {
    conduit::Node asNode;
    asNode[TYPE_FIELD] = type;
    id.addTo(asNode);
    // Optional fields
    if(!files.empty()){
      conduit::Node fileRef;
      for (auto &file : files) {
          auto &n = fileRef.add_child(file.getUri());
          n.set(file.toNode());
      asNode[FILES_FIELD] = fileRef;
      }
    }
    if(!data.empty()){
      //Loop through vector of data and append Json
      conduit::Node datumRef;
      for(auto &datum : data){
          datumRef.add_child(datum.first) = datum.second.toNode();
      }
      asNode[DATA_FIELD] = datumRef;
    }
    if(!curveSets.empty()){
      conduit::Node curveSetsNode;
      for(auto &entry : curveSets){
          curveSetsNode.add_child(entry.first) = entry.second.toNode();
      }
      asNode[CURVE_SETS_FIELD] = curveSetsNode;
    }
    if(!userDefined.dtype().is_empty()){
      asNode[USER_DEFINED_FIELD] = userDefined;
    }
    return asNode;
}

Record::Record(conduit::Node const &asNode) :
        id{asNode, LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{getRequiredString(TYPE_FIELD, asNode, "record")} {
    if(asNode.has_child(DATA_FIELD)){
        auto dataIter = asNode[DATA_FIELD].children();
        //Loop through DATA_FIELD objects and add them to data:
        while(dataIter.has_next()){
            auto &namedDatum = dataIter.next();
            data.emplace(std::make_pair(dataIter.name(), Datum(namedDatum)));
        }
    }
    if(asNode.has_child(FILES_FIELD)){
        auto filesIter = asNode[FILES_FIELD].children();
        while(filesIter.has_next()){
            auto &namedFile = filesIter.next();
            files.insert(File(filesIter.name(), namedFile));
        }
    }
    if (asNode.has_child(CURVE_SETS_FIELD)) {
        auto curveSetsIter = asNode[CURVE_SETS_FIELD].children();
        while(curveSetsIter.has_next()){
            auto &curveSetNode = curveSetsIter.next();
            std::string name = curveSetsIter.name();
            CurveSet cs{name, curveSetNode};
            curveSets.emplace(std::make_pair(std::move(name), std::move(cs)));
        }
    }
    if(asNode.has_child(USER_DEFINED_FIELD)){
        auto userDefinedNode = asNode[USER_DEFINED_FIELD];
        if (!userDefinedNode.dtype().is_empty()) {
            // Enforce that user_defined must be an object
            if (!userDefinedNode.dtype().is_object()) {
                throw std::invalid_argument("User_defined must be an object Node");
            }
            userDefined = userDefinedNode;
        }
    }
}

void Record::add(std::string name, Datum datum) {
    auto existing = data.find(name);
    if (existing == data.end()) {
        data.emplace(std::make_pair(name, datum));
    } else {
        existing->second = datum;
    }
}

void Record::add(File file) {
    auto existing = files.find(file);
    if (existing != files.end()) {
        files.erase(existing);
    }
    files.insert(std::move(file));
}
void Record::add(CurveSet curveSet) {
    auto name = curveSet.getName();
    auto existing = curveSets.find(name);
    if (existing == curveSets.end()) {
        curveSets.emplace(name, std::move(curveSet));
    } else {
        existing->second = std::move(curveSet);
    }
}

void Record::setUserDefinedContent(conduit::Node userDefined_) {
    userDefined = std::move(userDefined_);
}

void RecordLoader::addTypeLoader(std::string const &type, TypeLoader loader) {
    typeLoaders[type] = std::move(loader);
}

std::unique_ptr<Record>
RecordLoader::load(conduit::Node const &recordAsNode) const {
    auto loaderIter = typeLoaders.find(recordAsNode[TYPE_FIELD].as_string());
    if (loaderIter != typeLoaders.end()) {
        return loaderIter->second(recordAsNode);
    }
    return internal::make_unique<Record>(recordAsNode);
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
