#ifdef SINA_BUILD_ADIAK_BINDINGS

#ifndef SINA_ADIAK_HPP
#define SINA_ADIAK_HPP

/// @file

#include <string>
#include <type_traits>

#include "sina/JsonUtil.hpp"
#include "sina/Record.hpp"
#include "sina/Run.hpp"
#include "nlohmann/json.hpp"

extern "C" {
#include "adiak_tool.h"
}

namespace sina {

/**
* POTENTIAL IMPROVEMENTS:
* -Print to stdout if no file specified
* -Store nested lists in UserDefined
**/

/**
* Add a sina::File object to our current Record. Adiak stores paths,
* which are essentially the same as Sina's idea of storing files.
**/
void addFile(const std::string &name, const std::string &uri, sina::Record *record);

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
void adiakSinaCallback(const char *name, adiak_category_t category, const char *subcategory, adiak_value_t *value, adiak_datatype_t *t, void *opaque_value);

}
#endif

#endif // SINA_BUILD_ADIAK_BINDINGS
