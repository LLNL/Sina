#ifdef SINA_BUILD_ADIAK_BINDINGS

#ifndef SINA_ADIAK_HPP
#define SINA_ADIAK_HPP

/// @file

#include <string>
#include <type_traits>

#include "sina/ConduitUtil.hpp"
#include "sina/Record.hpp"
#include "sina/Run.hpp"

extern "C" {
#include "adiak_tool.h"
}

namespace sina {

/**
 * The callback function to pass to Adiak in order to write collected data to a Sina Record.
 **/ 
void adiakSinaCallback(const char *name, adiak_category_t category, const char *subcategory, adiak_value_t *value, adiak_datatype_t *t, void *opaque_value);

}
#endif

#endif // SINA_BUILD_ADIAK_BINDINGS
