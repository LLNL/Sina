/// @file

#include "sina/Datum.hpp"
#include "conduit/conduit.hpp"

#include <utility>
#include <sstream>
#include <stdexcept>

namespace {

char const VALUE_FIELD[] = "value";
char const UNITS_FIELD[] = "units";
char const TAGS_FIELD[] = "tags";
char const DATA_PARENT_TYPE[] = "data";

}

namespace sina {

Datum::Datum(std::string value_) :
        stringValue{std::move(value_)}{
    //Set type to String, as we know it uses strings
    type = ValueType::String;
}

Datum::Datum(double value_) :
        scalarValue{std::move(value_)}{
    //Set type to Scalar, as we know it uses doubles
    type = ValueType::Scalar;
}

Datum::Datum(std::vector<std::string> value_) :
        stringArrayValue{std::move(value_)}{
    //Set type to StringArray, as we know it uses an array of strings
    type = ValueType::StringArray;
}

Datum::Datum(std::vector<double> value_) :
        scalarArrayValue{std::move(value_)}{
    //Set type to ScalarArray, as we know it uses an array of doubles
    type = ValueType::ScalarArray;
}

Datum::Datum(conduit::Node const &asNode) {
    //Need to determine what type of Datum we have: Scalar (double), String,
    //or list of one of those two.
    conduit::Node valueNode = getRequiredField(VALUE_FIELD, asNode, DATA_PARENT_TYPE);
    if(valueNode.dtype().is_string()){
        stringValue = std::string(valueNode.value());
    }
    else if(valueNode.dtype().is_number()){
        scalarValue = double(valueNode.value());
    }
    else if(valueNode.dtype().is_list()){
        //An empty list is assumed to be an empty list of doubles.
        //This only works because this field is immutable!
        //If this ever changes, or if Datum's type is used directly to make
        //decisions (ex: Sina deciding where to store data), this logic
        //should be revisited.
        if(valueNode.number_of_children() == 0 || valueNode[0].dtype().is_number()){
            type = ValueType::ScalarArray;
        }
        else if(valueNode[0].dtype().is_string()){
            type = ValueType::StringArray;
        }
        else {
            std::ostringstream message;
            message << "The only valid types for an array '" << VALUE_FIELD
                    << "' are strings and numbers.";
            throw std::invalid_argument(message.str());
        }

        auto itr = asNode.children();
        while(itr.has_next())
        {
            conduit::Node const &entry = itr.next();
            if(entry.dtype().is_string() && type == ValueType::StringArray){
                stringArrayValue.emplace_back(std::string(entry.value()));
            }
            else if(entry.dtype().is_number() && type == ValueType::ScalarArray){
                scalarArrayValue.emplace_back(double(entry.value()));
            }
            else {
                std::ostringstream message;
                message << "If the required field '" << VALUE_FIELD
                        << "' is an array, it must consist of only strings or only numbers.";
                throw std::invalid_argument(message.str());
            }
        }
    }
    else {
        std::ostringstream message;
        message << "The required field '" << VALUE_FIELD
                << "' must be a string, double, list of strings, or list of doubles.";
        throw std::invalid_argument(message.str());
    }

    //Get the units, if there are any
    units = getOptionalString(UNITS_FIELD, asNode, DATA_PARENT_TYPE);

    //Need to grab the tags and add them to a vector of strings
    if(asNode.has_child(TAGS_FIELD)){
      auto tagNodeIter = asNode[TAGS_FIELD].children();
      while(tagNodeIter.has_next()){
        auto tag = tagNodeIter.next();
        if(tag.dtype().is_string()){
          tags.emplace_back(std::string(tag.value()));
        } else {
          std::ostringstream message;
          message << "The optional field '" << TAGS_FIELD
                  << "' must be an array of strings. Found '"
                  << tag.dtype().name() << "' instead.";
          throw std::invalid_argument(message.str());
         }
      }
   }
}

void Datum::setUnits(std::string units_) {
    units = std::move(units_);
}

void Datum::setTags(std::vector<std::string> tags_){
    tags = std::move(tags_);
}

conduit::Node Datum::toNode() const {
    conduit::Node asNode;
    switch(type){
        case ValueType::Scalar:
            asNode[VALUE_FIELD] = scalarValue;
            break;
        case ValueType::String:
            asNode[VALUE_FIELD] = stringValue;
            break;
        case ValueType::ScalarArray:
            asNode[VALUE_FIELD] = scalarArrayValue;
            break;
        case ValueType::StringArray:
            std::vector<std::string> stringArrayValCopy(stringArrayValue);
            addStringsToNode(asNode, VALUE_FIELD, stringArrayValCopy);
            break;
    }
    if(tags.size() > 0){
        std::vector<std::string> stringArrayValCopy(stringArrayValue);
        addStringsToNode(asNode, TAGS_FIELD, stringArrayValCopy);
    }
    if(!units.empty())
        asNode[UNITS_FIELD] = units;
    return asNode;
};


}
