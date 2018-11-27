#ifndef MNODA_FILE_HPP
#define MNODA_FILE_HPP

/// @file

#include <string>
#include <vector>

#include "nlohmann/json.hpp"

namespace mnoda {
/**
 * A File tracks the location (URI) and mimetype of a file on the file system. In the Mnoda schema, a File always
 * belongs to a Record or one of Record's inheriting types.
 *
 * Every File must have a URI, while mimetype and tags are optional.
 *
 * \code
 * mnoda::File myFile{"/path/to/file.png"};
 * myFile.setMimeType("image/png");
 * mnoda::File myOtherFile{"/path/to/other/file.txt"};
 * myOtherFile.setTags({"these","are","tags"});
 * myRecord->add(myFile);
 * myRecord->add(myOtherFile);
 * \endcode
 */
class File {
public:
    /**
     * Construct a new File.
     *
     * @param uri the location of the file
     */
    explicit File(std::string uri);

    /**
     * Construct a new File.
     *
     * @param uri the location of the file
     */
    // Note: without this, the constructors taking a std::string and a
    // nlohmann::json are ambiguous if a string literal is used
    explicit File(char const *uri);

    /**
     * Construct a new File.
     *
     * @param asJson the JSON representation of the file
     */
    explicit File(nlohmann::json const &asJson);

    /**
     * Get the File's URI.
     *
     * @return the URI
     */
    std::string const &getUri() const noexcept {
        return uri;
    }

    /**
     * Get the File's MIME type.
     *
     * @return the MIME type
     */
    std::string const &getMimeType() const noexcept {
        return mimeType;
    }

    /**
     * Get the File's tags.
     *
     * @return the tags
     */
    std::vector<std::string> const &getTags() const noexcept {
        return tags;
    }

    /**
     * Set the File's MIME type.
     *
     * @param mimeType the MIME type
     */
    void setMimeType(std::string mimeType);

    /**
     * Set the File's tags.
     *
     * @param tags the File's tags
     */
    void setTags(std::vector<std::string> tags);

    /**
     * Convert this File to its JSON representation.
     *
     * @return the File in its JSON representation
     */
    nlohmann::json toJson() const;

private:
    std::string uri;
    std::string mimeType;
    std::vector<std::string> tags;
};
}

#endif //MNODA_FILE_HPP
