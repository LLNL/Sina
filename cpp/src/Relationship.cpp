/// @file

#include "sina/Relationship.hpp"

#include <utility>

#include "sina/JsonUtil.hpp"

namespace sina {

namespace {
char const GLOBAL_SUBJECT_KEY[] = "subject";
char const LOCAL_SUBJECT_KEY[] = "local_subject";
char const GLOBAL_OBJECT_KEY[] = "object";
char const LOCAL_OBJECT_KEY[] = "local_object";
char const PREDICATE_KEY[] = "predicate";
}

Relationship::Relationship(ID subject_, std::string predicate_, ID object_) :
        subject{std::move(subject_), LOCAL_SUBJECT_KEY, GLOBAL_SUBJECT_KEY},
        object{std::move(object_), LOCAL_OBJECT_KEY, GLOBAL_OBJECT_KEY},
        predicate{std::move(predicate_)} {}

Relationship::Relationship(nlohmann::json const &asJson) :
        subject{asJson, LOCAL_SUBJECT_KEY, GLOBAL_SUBJECT_KEY},
        object{asJson, LOCAL_OBJECT_KEY, GLOBAL_OBJECT_KEY},
        predicate{getRequiredString(PREDICATE_KEY, asJson, "Relationship")} {}

nlohmann::json Relationship::toJson() const {
    nlohmann::json value;
    value[PREDICATE_KEY] = predicate;
    subject.addTo(value);
    object.addTo(value);
    return value;
}

}
