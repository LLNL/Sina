/// @file

#include "sina/File.hpp"
#include "sina/ConduitUtil.hpp"

#include <stdexcept>
#include <utility>
#include <sstream>

#include "conduit/conduit.hpp"

namespace sina {

namespace {
char const MIMETYPE_KEY[] = "mimetype";
char const FILE_TYPE_NAME[] = "File";
char const TAGS_KEY[] = "tags";
}

File::File(std::string uri_) : uri{std::move(uri_)} {}

File::File(char const *uri_) : uri{uri_} {}

File::File(std::string uri_, conduit::Node const &asNode) :
    uri{std::move(uri_)},
    mimeType{getOptionalString(MIMETYPE_KEY, asNode, FILE_TYPE_NAME)} {
        auto tagsIter = asNode[TAGS_KEY].children();
        while(tagsIter.has_next()){
            conduit::Node tag = tagsIter.next();
            if(tag.dtype().is_string())
                tags.emplace_back(tag.value());
            else {
                std::ostringstream message;
                message << "The optional field '" << TAGS_KEY
                    << "' must be an array of strings. Found '"
                    << tag.dtype().name() << "' instead.";
                throw std::invalid_argument(message.str());
            }
        }

    }

void File::setMimeType(std::string mimeType_) {
    File::mimeType = std::move(mimeType_);
}

void File::setTags(std::vector<std::string> tags_) {
    File::tags = std::move(tags_);
}

conduit::Node File::toNode() const {
    conduit::Node asNode;
    if (!mimeType.empty()) {
        asNode[MIMETYPE_KEY] = mimeType;
    }
    if(tags.size() > 0) {
      std::vector<std::string> tags_copy(tags);
      addStringsToNode(asNode, TAGS_KEY, tags_copy);
    }
    return asNode;
}

}
