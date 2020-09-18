#include "sina/testing/ConduitTestUtils.hpp"

namespace sina { namespace testing {

conduit::Node parseJsonValue(std::string const &valueAsString) {
    conduit::Node node;
    std::string fullContents = "{\"TEST_KEY\": ";
    fullContents += valueAsString;
    fullContents += "}";
    node.parse(fullContents, "json");
    return node.child("TEST_KEY");
}
}}
