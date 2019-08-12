/// @file
#include <stdexcept>
#include <utility>
#include <iostream>
#include <fstream>

extern "C" {
#include "adiak_tool.h"
}

#include "sina/CppBridge.hpp"
#include "sina/JsonUtil.hpp"
#include "sina/Record.hpp"
#include "sina/Datum.hpp"
#include "sina/Document.hpp"
#include "sina/AdiakWriter.hpp"


namespace sina{
/**
* Initial draft is pretty bare-bones.
* We'll dump a "Document" consisting of a single Record and nothing else.
* Also, hardcoded id and type. All fixable once there's a need.
* NOTES:
* Adiak doesn't have rec_id, rec_type, or rec_app analogues, but does have version
**/
void flushRecord(const std::string &filename, sina::Record *record){
    std::ofstream outfile(filename);
    if (outfile.is_open()) {
      outfile << record->toJson();
      outfile.close();
    }
    //In the future, we might want more than one record per document
    //sina::Document doc;
    //doc.add(record_ptr);
    //sina::saveDocument(doc, filename);
}

template <typename T>
// TODO: Check how to pass the std::vector, since we'll be moving it
void addDatum(const std::string &name, T sina_safe_val, std::vector<std::string> tags, sina::Record *record){
    sina::Datum datum{sina_safe_val};
    datum.setTags(std::move(tags));
    record->add(name, datum);
}

// We don't care about type here, there's only one adiak type that acts as a file
void addFile(const std::string &name, const std::string &uri, sina::Record *record){
    sina::File file{uri};
    // TODO: Isn't there a shortcut way of declaring vectors? combine 2 lines
    std::vector<std::string> tags = {name}; 
    file.setTags(std::move(tags));
    record->add(std::move(file));
}

SinaType findSinaType(adiak_datatype_t *t){
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
            return sina_unknown;
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
        case adiak_timeval: {
	    struct timeval *tval = static_cast<struct timeval *>(val->v_ptr);
	    return tval->tv_sec + (tval->tv_usec / 1000000.0);
        }
        default:
            printf("ERROR: adiak-to-sina double converter given something not convertible to double"); 
            throw 1;
    }
}

std::string toString(adiak_value_t *val, adiak_datatype_t *t){
    switch (t->dtype){
        case adiak_date: {
	    char datestr[512];
	    signed long seconds_since_epoch = static_cast<signed long>(val->v_long);
	    struct tm *loc = localtime(&seconds_since_epoch);
	    strftime(datestr, sizeof(datestr), "%a, %d %b %Y %T %z", loc); 
	    return static_cast<std::string>(datestr);
        }
        case adiak_catstring:
        case adiak_version:
        case adiak_string:
        case adiak_path:
            return std::string(static_cast<char *>(val->v_ptr));
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
        sina_safe_list.emplace_back(toScalar(subvals+i, t->subtype[0]));
    }
    return sina_safe_list;
}

std::vector<std::string> toStringList(adiak_value_t *subvals, adiak_datatype_t *t){
    std::vector<std::string> sina_safe_list;
    int i;
    for (i = 0; i < t->num_elements; i++) {
        sina_safe_list.emplace_back(toString(subvals+i, t->subtype[0]));
    }
    std::cout << std::flush;
    return sina_safe_list;
}

void adiakSinaCallback(const char *name, adiak_category_t category, const char *subcategory, adiak_value_t *val, adiak_datatype_t *t, void *void_record)
{
    if (!t){
        printf("ERROR: type must be specified for Adiak data");
        return;
    }
    const SinaType sina_type = findSinaType(t);
    sina::Record *record = static_cast<sina::Record *>(void_record);
    std::vector<std::string> tags {};
    if(subcategory && subcategory[0]!=0){
        tags.emplace_back(subcategory); 
    }
    switch (sina_type) {
        case sina_unknown:
            // If we don't know what it is, we can't store it, so as above...
            printf("ERROR: unknown Adiak type cannot be added to Sina record."); 
            break;
        case sina_scalar: {
            tags.emplace_back(adiak_type_to_string(t, 1));
            addDatum(name, toScalar(val, t), tags, record);
            break;
        }
        case sina_string: {
           // TODO: Feel like this info isn't useful for strings, but maybe?
           tags.emplace_back(adiak_type_to_string(t, 1));  
           addDatum(name, toString(val, t), tags, record);
           break;
        }
        case sina_file:
           addFile(name, toString(val, t), record);
           break;
        case sina_list: {
         // Sina doesn't really know/care the difference between list, tuple, set
         // Further simplification: everything has to be the same type
         // Even further simplification: nothing nested. In the future, depth>1 lists
         // should be sent to user_defined
         adiak_value_t *subvals = (adiak_value_t *) val->v_ptr;
         SinaType list_type = findSinaType(t->subtype[0]); 
         tags.emplace_back(adiak_type_to_string(t->subtype[0], 1));
         switch (list_type) {
             case sina_string:
                 addDatum(name, toStringList(subvals, t), tags, record);
                 break;
             // Weird case wherein we're given a list of filenames, which we can somewhat manage
             case sina_file:
                 int i;
                 for (i=0; i < t->num_elements; i++) {
                     addFile(name, toString(subvals+i, t->subtype[0]), record);
                 }
                 break;
             case sina_scalar:
                 addDatum(name, toScalarList(subvals, t), tags, record);
                 break;
             case sina_unknown:
                 printf("ERROR: type must not be unknown for list entries to be added to a Sina record");
                 throw 1;
             default:
                 printf("ERROR: type must be set for list entries to be added to a Sina record");
                 throw 1;
         }
         break;
     }
   }
}
}
