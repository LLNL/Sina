/// @file

#include "mnoda/Datum.hpp"

#include <utility>
#include <sstream>
#include <stdexcept>

namespace {

char const NAME_FIELD[] = "name";
char const VALUE_FIELD[] = "value";
char const UNITS_FIELD[] = "units";
char const TAGS_FIELD[] = "tags";

}

namespace mnoda {

Datum::Datum(std::string name_, std::string value_) :
        name{std::move(name_)},
        stringValue{std::move(value_)}{
    //Set type to Value, as we know it uses strings
    type = ValueType::Value;
}

Datum::Datum(std::string name_, double value_) :
        name{std::move(name_)},
        scalarValue{std::move(value_)}{
    //Set type to Scalar, as we know it uses doubles
    type = ValueType::Scalar;
}

Datum::Datum(nlohmann::json const &asJson) :
    name{getRequiredString(NAME_FIELD, asJson, "datum")} {
    //Need to determine what type of Datum we have: scalar (double) or value (string)
    nlohmann::json valueField = getRequiredField(VALUE_FIELD, asJson, "datum");
    if(valueField.is_string()){
        stringValue = valueField.get<std::string>();
    }
    else if(valueField.is_number()){
        scalarValue = valueField.get<double>();
    }
    else {
        std::ostringstream message;
        message << "The required field '" << VALUE_FIELD
                << "' must be a string or a double";
        throw std::invalid_argument(message.str());
    }

    //Get the units, if there are any
    units = getOptionalString(UNITS_FIELD, asJson, "datum");

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
    asJson[NAME_FIELD] = name;
    switch(type){
        case ValueType::Scalar:
            asJson[VALUE_FIELD] = scalarValue;
            break;
        case ValueType::Value:
            asJson[VALUE_FIELD] = stringValue;
            break;
        default:
            std::ostringstream message;
            message << "The field '" << VALUE_FIELD
                    << "' must be a string or double.";
            throw std::invalid_argument(message.str());

    }
    if(tags.size() > 0)
        asJson[TAGS_FIELD] = tags;
    if(!units.empty())
        asJson[UNITS_FIELD] = units;
    return asJson;
};


}
