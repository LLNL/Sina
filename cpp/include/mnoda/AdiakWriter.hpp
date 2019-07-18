#ifndef MNODA_ADIAK_HPP
#define MNODA_ADIAK_HPP

/// @file

#include <string>
#include <type_traits>

#include "mnoda/JsonUtil.hpp"
#include "nlohmann/json.hpp"

extern "C" {
#include "adiak_tool.h"
}

namespace mnoda {

/**
* POTENTIAL IMPROVEMENTS:
* -Print to file instead of stdout
* -Handle multiple Records (know what Documents are)
* -Store nested lists in UserDefined
* -Stop using a pointer to a Record, start using opaque_value 
**/ 

/**
* Create a brand-new Record, wiping out anything that might have been
* stored in the previous one. flush_record() first if you've stored anything!
*
* @param id the global ID for the record (local ids not supported yet)
* @param type the record's type (ex: run, reset, msub, john_doe_trialrun)
**/
void initRecord(std::string id, std::string type);

/**
* Print the current Record (set up by init_record()) to a file.
* Technically Records aren't standalone (they live in a Document), but we
* don't care about that for now, so it's just a Record alone in a Document.
**/
void flushRecord(std::string filename);

/**
* Add a mnoda::Datum object to our current Record. These are the sina equivalent
* of an Adiak datapoint. Since we track slightly different info, this function
* harvests what it can and hands it off to the Record.
**/
template <typename T>
void addDatum(std::string name, T sina_safe_val, adiak_datatype_t* type);

/**
* Add a mnoda::File object to our current Record. Adiak stores paths,
* which are essentially the same as Mnoda files.
**/
void addFile(std::string name, std::string uri);

/**
* Take an adiak value, convert it to a form Sina recognizes, then hand it off
* to our currently-live Record. This ends up calling addDatum or addFile.
**/
void addToRecord(const char *name, adiak_value_t *val, adiak_datatype_t *t);

/**
* Adiak has a much wider array of supported types than Sina. We will convert
* Adiak types to ones Sina understands; SinaType holds the possibilities.
**/
enum SinaType {sina_scalar, sina_string, sina_list, sina_file, sina_unknown};

/**
* Given an Adiak type, return its corresponding Sina type.
**/
SinaType findSinaType(adiak_datatype_t *t); 

/**
* Several Adiak types become what Sina views as a "scalar" (a double).
* Manage the conversions from various Adiak types to the final double
* representation
**/ 
double toScalar(adiak_value_t *val, adiak_datatype_t *t);

/**
* Other Adiak types become what Sina views as a string.
* Manage the conversions from various Adiak types to said string.
**/
std::string toString(adiak_value_t *val, adiak_datatype_t *t);

/**
* Other Adiak types become a list of some form. Sina, being concerned
* with queries and visualization, only handles lists that are all scalars
* or all strings. Manage conversions from various Adiak list types that
* contain scalars to a simple list (vector) of scalars.
**/
std::vector<double> toScalarList(adiak_value_t *subvals, adiak_datatype_t *t);

/**
* Partner method to the above, invoked when the children of an adiak list
* type are strings (according to Sina).
**/
std::vector<std::string> toStringList(adiak_value_t *subvals, adiak_datatype_t *t); 

// Register the sina callback with Adiak
void adiakSinaCallback(const char *name, adiak_category_t category, adiak_value_t *value, adiak_datatype_t *t, void *opaque_value);

}
#endif
