/// @file
#include <stdexcept>
#include <utility>
#include <iostream>

extern "C" {
#include "adiak_tool.h"
}

#include "mnoda/CppBridge.hpp"
#include "mnoda/JsonUtil.hpp"
#include "mnoda/Record.hpp"
#include "mnoda/Datum.hpp"
#include "mnoda/Document.hpp"
#include "mnoda/AdiakWriter.hpp"


namespace mnoda{
/**
* Initial draft is pretty bare-bones.
* We'll dump a "Document" consisting of a single Record and nothing else.
* Also, hardcoded id and type. All fixable once there's a need.
* NOTES:
* Adiak doesn't have rec_id, rec_type, or rec_app analogues, but does have version
**/
std::unique_ptr<mnoda::Record> record_ptr;

void initRecord(std::string id, std::string type){
    mnoda::ID rec_id{id, mnoda::IDType::Local};
    record_ptr.reset(new mnoda::Record{rec_id, type});
}

void flushRecord(std::string filename){
    //In the future, we might want more than one record per document
    mnoda::Document doc; 
    doc.add(record_ptr);
    save(doc, filename);
}

template <typename T>
void addDatum(std::string name, T sina_safe_val, adiak_datatype_t* type){
    mnoda::Datum datum{sina_safe_val};
    datum.setTags({type->print_name});
    record_ptr->add(name, datum);
}

void addFile(std::string name, std::string uri){
    mnoda::File file{uri};
    file.setTags({name});
    record_ptr->add(std::move(file));
}

const SinaType findSinaType(adiak_datatype_t *t){
    switch (t->dtype){
        case adiak_long:
        case adiak_ulong:
        case adiak_int:
        case adiak_uint:
        case adiak_double:
        case adiak_timeval:
            return sina_scalar;
        case adiak_date:
        case adiak_version:
        case adiak_string:
        case adiak_catstring:
            return sina_string;
        case adiak_path:
            return sina_file;
        case adiak_set:
        case adiak_tuple:
        case adiak_range:
        case adiak_list:
            return sina_list;
        case adiak_type_unset:
        default:
            return sina_unknown;
    }
}

// Intentionally do not have one for lists, we should not have nested lists at this stage
double toScalar(adiak_value_t *val, adiak_datatype_t *t){
    switch (t->dtype){
        case adiak_long:
        case adiak_ulong:
            return static_cast<double>(val->v_long);
        case adiak_int:
        case adiak_uint:
            return static_cast<double>(val->v_int);
        case adiak_double:
            return val->v_double;
        case adiak_timeval:
	    struct timeval *tval = static_cast<struct timeval *>(val->v_ptr);
	    return tval->tv_sec + (tval->tv_usec / 1000000.0);
       default:
            printf("ERROR: adiak-to-sina double converter given something not convertible to double"); 
            throw 1;
    }
}

std::string toString(adiak_value_t *val, adiak_datatype_t *t){
    switch (t->dtype){
        case adiak_date:
	    char datestr[512];
	    signed long seconds_since_epoch = static_cast<signed long>(val->v_long);
	    struct tm *loc = localtime(&seconds_since_epoch);
	    strftime(datestr, sizeof(datestr), "%a, %d %b %Y %T %z", loc); 
	    return static_cast<std::string>(datestr);
        case adiak_version:
        case adiak_string:
        case adiak_catstring:
        case adiak_path:
            return std::string{static_cast<char *>(val->v_ptr)};
       default:
            printf("ERROR: adiak-to-sina string converter given something not convertible to string");
            throw 1;
    }
}

// There's probably an elegant way to unify these two functions. Revisit.
std::vector<double> toScalarList(adiak_value_t *subvals, adiak_datatype_t *t){
    std::vector<double> sina_safe_list;
    int i;
    for (i = 0; i < t->num_elements; i++) {
        sina_safe_list.emplace_back(convert_adiak_value_to_scalar(subvals+i, t));
    }
    return sina_safe_list;
}

std::vector<std::string> toStringList(adiak_value_t *subvals, adiak_datatype_t *t){
    std::vector<std::string> sina_safe_list;
    int i;
    for (i = 0; i < t->num_elements; i++) {
        sina_safe_list.emplace_back(convert_adiak_value_to_string(subvals+i, t));
    }
    return sina_safe_list;
}

void addToRecord(const char *name, adiak_value_t *val, adiak_datatype_t *t)
{
    if (!t)
        //TODO: something better for this when I understand what it "means"
        printf("ERROR");
    const SinaType sina_type = findSinaType(t);
    switch (sina_type) {
        case sina_unknown:
            // If we don't know what it is, we can't store it, so as above...
            printf("ERROR: type must be set for data to be added to a Sina record"); 
            break;
        case sina_scalar:
            addDatum(name, toScalar(val, t), t);
            break;
        case sina_string:
           addDatum(name, toString(val, t), t);
           break;
        case sina_file:
           addFile(name, toString(val, t));
           break;
        case sina_list: {
         // Sina doesn't really know/care the difference between list, tuple, set
         // Further simplification: everything has to be the same type
         // Even further simplification: nothing nested. In the future, depth>1 lists
         // should be sent to user_defined
         adiak_value_t *subvals = (adiak_value_t *) val->v_ptr;
         SinaType list_type = findSinaType(t->subtype[0]); 
         switch (list_type) {
             case sina_string:
                 addDatum(name, toStringList(subvals, t), t);
             // Weird case wherein we're given a list of filenames, which we can somewhat manage
             case sina_file:
                 int i;
                 for (i=0; i < t->num_elements; i++) {
                     addFile(name, toString(subvals+i));
                 }
             case sina_scalar:
                 add_datum(name, toScalarList(subvals, t), t);
             case sina_unknown:
             default:
                 printf("ERROR: type must be set for list entries to be added to a Sina record");
         }
         break;
     }
   }
}

// What's "category" equivalent to for us?
// Opaque_value is where we'll eventually pass a pointer to the Record object 
void adiakSinaCallback(const char *name, adiak_category_t category, adiak_value_t *value, adiak_datatype_t *t, void *opaque_value)
{
   mnoda::addToRecord(name, value, t);
}
}
