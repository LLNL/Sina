/// @file

#include "sina/File.hpp"

#include <stdexcept>
#include <utility>
#include <sstream>

#include "sina/JsonUtil.hpp"

namespace sina {

namespace {
char const MIMETYPE_KEY[] = "mimetype";
char const FILE_TYPE_NAME[] = "File";
char const TAGS_KEY[] = "tags";
}

File::File(std::string uri_) : uri{std::move(uri_)} {}

File::File(char const *uri_) : uri{uri_} {}

File::File(std::string uri_, nlohmann::json const &asJson) :
    uri{std::move(uri_)},
    mimeType{getOptionalString(MIMETYPE_KEY, asJson, FILE_TYPE_NAME)} {
        auto tagsIter = asJson.find(TAGS_KEY);
        if(tagsIter != asJson.end()){
            for(auto &tag : *tagsIter){
                if(tag.is_string())
                    tags.emplace_back(tag.get<std::string>());
                else {
                    std::ostringstream message;
                    message << "The optional field '" << TAGS_KEY
                        << "' must be an array of strings. Found '"
                        << tag.type_name() << "' instead.";
                    throw std::invalid_argument(message.str());
                }
            }
        }

    }

void File::setMimeType(std::string mimeType_) {
    File::mimeType = std::move(mimeType_);
}

void File::setTags(std::vector<std::string> tags_) {
    File::tags = std::move(tags_);
}

nlohmann::json File::toJson() const {
    nlohmann::json asJson;
    if (!mimeType.empty()) {
        asJson[MIMETYPE_KEY] = mimeType;
    }
    if(tags.size() > 0) {
        asJson[TAGS_KEY] = tags;
    }
    return asJson;
}

}
