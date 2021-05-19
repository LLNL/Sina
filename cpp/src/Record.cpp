/// @file

#include "sina/Record.hpp"

#include <stdexcept>
#include <utility>

#include "sina/CppBridge.hpp"
#include "sina/ConduitUtil.hpp"
#include "sina/DataHolder.hpp"
#include "sina/Run.hpp"

namespace {

char const LOCAL_ID_FIELD[] = "local_id";
char const GLOBAL_ID_FIELD[] = "id";
char const TYPE_FIELD[] = "type";
char const FILES_FIELD[] = "files";
char const USER_DEFINED_FIELD[] = "user_defined";

}

namespace sina {

Record::Record(ID id_, std::string type_) :
        DataHolder{},
        id{std::move(id_), LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{std::move(type_)} {}

conduit::Node Record::toNode() const {
    conduit::Node asNode = DataHolder::toNode();
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
    if(!userDefined.dtype().is_empty()){
      asNode[USER_DEFINED_FIELD] = userDefined;
    }
    return asNode;
}

Record::Record(conduit::Node const &asNode) :
        DataHolder{asNode},
        id{asNode, LOCAL_ID_FIELD, GLOBAL_ID_FIELD},
        type{getRequiredString(TYPE_FIELD, asNode, "record")} {

    if(asNode.has_child(FILES_FIELD)){
        auto filesIter = asNode[FILES_FIELD].children();
        while(filesIter.has_next()){
            auto &namedFile = filesIter.next();
            files.insert(File(filesIter.name(), namedFile));
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

void Record::add(File file) {
    auto existing = files.find(file);
    if (existing != files.end()) {
        files.erase(existing);
    }
    files.insert(std::move(file));
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
