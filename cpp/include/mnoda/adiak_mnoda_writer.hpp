#ifndef MNODA_DATUM_HPP
#define MNODA_DATUM_HPP

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
 * * Take an adiak value, convert it to a form Sina recognizes, then hand it off
 * * to our currently-live Record.
 * **/
void add_to_record(const char *name, adiak_value_t *val, adiak_datatype_t *t);

// Register the sina callback with Adiak
void adiak_sina_callback(const char *name, adiak_category_t category, adiak_value_t *value, adiak_datatype_t *t, void *opaque_value);

// Create a new record
void initRecord(std::string id, std::string type);

// Write the current record to stdout
void flush_record();
}
#endif
