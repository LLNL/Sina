/// @file

#include "sina/Document.hpp"

#include <cstdio>
#include <fstream>
#include <ios>
#include <iostream>
#include <utility>
#include <sstream>
#include <stdexcept>

namespace sina {

namespace {
char const RECORDS_KEY[] = "records";
char const RELATIONSHIPS_KEY[] = "relationships";
char const SAVE_TMP_FILE_EXTENSION[] = ".sina.tmp";
}

void Document::add(std::unique_ptr<Record> record) {
    records.emplace_back(std::move(record));
}

void Document::add(Relationship relationship) {
    relationships.emplace_back(std::move(relationship));
}

nlohmann::json Document::toJson() const {
    nlohmann::json recordsList;
    if(!records.empty()){
      for (auto &record : records) {
          recordsList.emplace_back(record->toJson());
      }
    } else {
      recordsList = nlohmann::json::array({});
    }

    nlohmann::json relationshipsList;
    if(!relationships.empty()){
      for (auto &relationship : relationships) {
          relationshipsList.emplace_back(relationship.toJson());
      }
    } else {
      relationshipsList = nlohmann::json::array({});
    }

    return nlohmann::json{
            {RECORDS_KEY, recordsList},
            {RELATIONSHIPS_KEY, relationshipsList},
    };
}

Document::Document(nlohmann::json const &asJson,
        RecordLoader const &recordLoader) {
    auto recordsIter = asJson.find(RECORDS_KEY);
    if (recordsIter != asJson.end()) {
        if (recordsIter->is_array()) {
            for (auto const &record : *recordsIter) {
                add(recordLoader.load(record));
            }
        } else if (!recordsIter->is_null()) {
            std::ostringstream message;
            message << "The '" << RECORDS_KEY
                    << "' element of a document must be an array";
            throw std::invalid_argument(message.str());
        }
    }

    auto relationshipsIter = asJson.find(RELATIONSHIPS_KEY);
    if (relationshipsIter != asJson.end()) {
        if (relationshipsIter->is_array()) {
            for (auto const &relationship : *relationshipsIter) {
                add(Relationship{relationship});
            }
        } else if (!relationshipsIter->is_null()){
            std::ostringstream message;
            message << "The '" << RELATIONSHIPS_KEY
                    << "' element of a document must be an array";
            throw std::invalid_argument(message.str());
        }
    }

}

void saveDocument(Document const &document, std::string const &fileName) {
    // It is a common use case for users to want to overwrite their files as
    // the simulation progresses. However, this operation should be atomic so
    // that if a write fails, the old file is left intact. For this reason,
    // we write to a temporary file first and then move the file. The temporary
    // file is in the same directory to ensure that it is part of the same
    // file system as the destination file so that the move operation is
    // atomic.
    std::string tmpFileName = fileName + SAVE_TMP_FILE_EXTENSION;
    auto asJson = document.toJson();
    std::ofstream fout{tmpFileName};
    fout.exceptions(std::ostream::failbit | std::ostream::badbit);
    fout << asJson;
    fout.close();

    if (rename(tmpFileName.c_str(), fileName.c_str()) != 0) {
        std::string message{"Could not save to '"};
        message += fileName;
        message += "'";
        throw std::ios::failure{message};
    }
}

Document loadDocument(std::string const &path) {
    return loadDocument(path, createRecordLoaderWithAllKnownTypes());
}

Document loadDocument(std::string const &path,
        RecordLoader const &recordLoader) {
    nlohmann::json documentAsJson;
    std::ifstream fin{path};
    fin >> documentAsJson;
    return Document{documentAsJson, recordLoader};
}

}
