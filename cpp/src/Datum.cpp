/// @file

#include "sina/Datum.hpp"

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

Datum::Datum(nlohmann::json const &asJson) {
    //Need to determine what type of Datum we have: Scalar (double), String,
    //or list of one of those two.
    nlohmann::json valueField = getRequiredField(VALUE_FIELD, asJson, DATA_PARENT_TYPE);
    if(valueField.is_string()){
        stringValue = valueField.get<std::string>();
    }
    else if(valueField.is_number()){
        scalarValue = valueField.get<double>();
    }
    else if(valueField.is_array()){
        //An empty list is assumed to be an empty list of doubles.
        //This only works because this field is immutable!
        //If this ever changes, or if Datum's type is used directly to make
        //decisions (ex: Sina deciding where to store data), this logic
        //should be revisited.
        if(valueField.size() == 0 || valueField.at(0).is_number()){
            type = ValueType::ScalarArray;
        }
        else if(valueField.at(0).is_string()){
            type = ValueType::StringArray;
        }
        else {
            std::ostringstream message;
            message << "The only valid types for an array '" << VALUE_FIELD
                    << "' are strings and numbers.";
            throw std::invalid_argument(message.str());
        }

        for(auto &entry : valueField){
            if(entry.is_string() && type == ValueType::StringArray){
                stringArrayValue.emplace_back(entry.get<std::string>());
            }
            else if(entry.is_number() && type == ValueType::ScalarArray){
                scalarArrayValue.emplace_back(entry.get<double>());
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
    units = getOptionalString(UNITS_FIELD, asJson, DATA_PARENT_TYPE);

    //Need to grab the tags and add them to a vector of strings
    auto tagsIter = asJson.find(TAGS_FIELD);
    if(tagsIter != asJson.end()){
        for(auto &tag : *tagsIter){
            if(tag.is_string())
                tags.emplace_back(tag.get<std::string>());
            else {
                std::ostringstream message;
                message << "The optional field '" << TAGS_FIELD
                        << "' must be an array of strings. Found '"
                        << tag.type_name() << "' instead.";
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

nlohmann::json Datum::toJson() const {
    nlohmann::json asJson;
    switch(type){
        case ValueType::Scalar:
            asJson[VALUE_FIELD] = scalarValue;
            break;
        case ValueType::String:
            asJson[VALUE_FIELD] = stringValue;
            break;
        case ValueType::ScalarArray:
            asJson[VALUE_FIELD] = scalarArrayValue;
            break;
        case ValueType::StringArray:
            asJson[VALUE_FIELD] = stringArrayValue;
            break;
        default:
            std::ostringstream message;
            message << "The field '" << VALUE_FIELD
                    << "' must be a string, double, list of strings, or list of doubles.";
            throw std::invalid_argument(message.str());

    }
    if(tags.size() > 0)
        asJson[TAGS_FIELD] = tags;
    if(!units.empty())
        asJson[UNITS_FIELD] = units;
    return asJson;
};


}
