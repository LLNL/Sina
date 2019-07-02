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


namespace mnoda{
/**
* Initial draft is pretty bare-bones.
* We'll dump a "Document" consisting of a single Record and nothing else.
* Also, hardcoded id and type. All fixable once there's a need.
* NOTES:
* Adiak doesn't have rec_id, rec_type, or rec_app analogues, but does have version
**/
std::unique_ptr<mnoda::Record> record_ptr;

/**
* Create a brand-new Record, wiping out anything that might have been
* stored in the previous one. flush_record() first!
*
* @param id the global ID for the record (local ids not supported yet)
* @param type the record's type (ex: run, reset, msub, john_doe_trialrun)
**/
//TODO: carry camelcase throughout for funcnames
void initRecord(std::string id, std::string type){
  // Double-check which header gives us the IDs.
  mnoda::ID rec_id{id, mnoda::IDType::Local};
  record_ptr.reset(new mnoda::Record{rec_id, type});
}

/**
* Print the current record (set up by init_record()) to stdout.
* In the future, will probably do this into a file.
* Technically records aren't standalone (they live in a Document), but we
* don't care about that for now.
**/
void flush_record(){
  std::cout << record_ptr->toJson().dump() << std::endl;
}

/**
* Add a mnoda::Datum object to our current Record. These are the sina equivalent
* of an Adiak datapoint. Since we track slightly different info, this function
* harvests what it can and hands it off to the Record. Note the arbitrary type
* on the value--Datum's pretty flexible, but we do perform some conversions in
* add_to_record().
**/
template <typename T>
void add_datum(std::string name, T sina_safe_val, adiak_datatype_t* type){
  mnoda::Datum datum{sina_safe_val};
  // Apparently {foo} -> std::vector containing foo is a C++11 thing
  datum.setTags({type->print_name});
  record_ptr->add(name, datum);
}

void add_file(std::string name, std::string uri){
  mnoda::File file{uri};
  file.setTags({name});
  record_ptr->add(std::move(file));
}

// Utility method for pulling strings from adiak vals 
std::string string_from_adiak_val(adiak_value_t *val){
    return std::string{static_cast<char *>(val->v_ptr)};
}

/**
* Take an adiak value, convert it to a form Sina recognizes, then hand it off
* to our currently-live Record.
**/

void add_to_record(const char *name, adiak_value_t *val, adiak_datatype_t *t)
{
   if (!t)
      //TODO: something better for this when I understand what it "means"
      printf("ERROR");
   switch (t->dtype) {
      case adiak_type_unset:
         // If we don't know what it is, we can't store it, so as above...
         printf("ERROR"); 
         break;
      // Datum's presumably fine with the various double species
      case adiak_long:
      case adiak_ulong:
        add_datum(name, static_cast<double>(val->v_long), t);
        break;
      case adiak_int:
      case adiak_uint:
        add_datum(name, static_cast<double>(val->v_int), t);
        break;
      case adiak_double:
         add_datum(name, val->v_double, t);
         break;
      case adiak_date: {
         char datestr[512];
         signed long seconds_since_epoch = static_cast<signed long>(val->v_long);
         struct tm *loc = localtime(&seconds_since_epoch);
         strftime(datestr, sizeof(datestr), "%a, %d %b %Y %T %z", loc);
         add_datum(name, static_cast<std::string>(datestr), t);
         break;
      }
      case adiak_timeval: {
         struct timeval *tval = static_cast<struct timeval *>(val->v_ptr);
         double duration = tval->tv_sec + (tval->tv_usec / 1000000.0);
         add_datum(name, duration, t);
         break;
      }

      //This is part of what would make it a Run.
      //Revisit when not doing a minimal implementation.
      case adiak_version:
      case adiak_string:
      case adiak_catstring:
         add_datum(name, string_from_adiak_val(val), t);
         break;
      case adiak_path:
         add_file(name, string_from_adiak_val(val));
         break;
      case adiak_set:
      case adiak_tuple:
      // A range is just two numbers; we store it as a list.
      case adiak_range:
      case adiak_list: {
         // Sina doesn't really know/care the difference between list, tuple, set
         // Further simplification: everything has to be the same type
         adiak_value_t *subvals = (adiak_value_t *) val->v_ptr;
         switch (t->subtype[0]->dtype) {
	    case adiak_version:
            case adiak_string:
            case adiak_catstring: {
               std::vector<std::string> sina_safe_list;
               int i;
               for (i = 0; i < t->num_elements; i++) {
                  sina_safe_list.emplace_back(string_from_adiak_val(subvals+i));
               }
               add_datum(name, sina_safe_list, t->subtype[0]); 
               break;
            }
            default: {
               std::vector<double> sina_safe_list;
               int i;
               for (i = 0; i < t->num_elements; i++) {
                  sina_safe_list.emplace_back(static_cast<double>(subvals+i));
               }
               add_datum(name, sina_safe_list, t->subtype[0]); 
               break;
            }
         }
         break;
     }
   }
}

// What's "category" equivalent to for us?
// Opaque_value is where we'll eventually pass a pointer to the Record object 
void adiak_sina_callback(const char *name, adiak_category_t category, adiak_value_t *value, adiak_datatype_t *t, void *opaque_value)
{
   mnoda::add_to_record(name, value, t);
}
}
