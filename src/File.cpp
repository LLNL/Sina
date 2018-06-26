/// @file

#include "mnoda/File.hpp"

#include <stdexcept>
#include <utility>

#include "mnoda/JsonUtil.hpp"

namespace mnoda {

namespace {
char const URI_KEY[] = "uri";
char const MIMETYPE_KEY[] = "mimetype";
char const FILE_TYPE_NAME[] = "File";
}

File::File(std::string uri_) : uri{std::move(uri_)}, mimeType{} {}

File::File(char const *uri_) : uri{uri_}, mimeType{} {}

File::File(std::string uri_, std::string mimeType_) :
        uri{std::move(uri_)},
        mimeType{std::move(mimeType_)} {}

File::File(nlohmann::json const &asJson) :
    uri{getRequiredString(URI_KEY, asJson, FILE_TYPE_NAME)},
    mimeType{getOptionalString(MIMETYPE_KEY, asJson, FILE_TYPE_NAME)} {}

void File::setMimeType(std::string mimeType_) {
    File::mimeType = std::move(mimeType_);
}

nlohmann::json File::toJson() const {
    nlohmann::json asJson{
            {URI_KEY, uri},
    };
    if (!mimeType.empty()) {
        asJson[MIMETYPE_KEY] = mimeType;
    }
    return asJson;
}

}
