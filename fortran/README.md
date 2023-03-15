# Quick Start Guide

Sina's Fortran component is bound to, and built with, its C++ component.

As such, in order to make efficient use of filespace and reduce the chance of something breaking, it piggybacks off of the C++
component's build resources.

In order to build the Fortran interface, ensure you've completed the C++ build (see the C++ Readme) and run `make install`, then:

	mkdir build
        cd build
	export Sina_DIR="../../cpp/build-clang/install/lib/cmake/sina"
	cmake -C ../../cpp/CMake/host-configs/sina-linux-rhel7-ivybridge-clang@14.0.6.cmake -DCMAKE_TOOLCHAIN_FILE=../../cpp/CMake/Platform/toss_4_x86_64_clang.cmake .. -DCMAKE_INSTALL_PREFIX=install
        make

Note that you will, of course, need a Fortran compiler available! The host-config referenced above should find it, so long as you're on LC. Also note that the above is the "standard" installation (assuming clang, using Sina built right in the cpp dir, etc).


# Usage

Usage is similar to Sina C++. See [tests/example.f90](tests/example.f90), under the `USAGE` heading.

# A Very Simple Example

First, you will need to create a record with a unique identifier. This ID can be whatever you'd like, but it must be unique. 
```
call create_document_and_record(record_id)
```

Now, let's add some data! In its current form, you can add key/value pairs, and associate a single tag and units in the following fashion.
```
call sina_add(key_name, key_value, units, tag)
```

Let's add a curveset!
```
call sina_add_curveset(curveset_name)
```

We have support for independent and dependent curves within that curveset.
Note that the last parameter indicates whether the curve is independent or not. 
```
call sina_add_curve(curveset_name, curve_name, curve_data_type, curve_size, independent)
```

Let's write out the data to a JSON file. This can be ingested into a datastore using Sina's CLI or Python API
```
call write_sina_document(sina_json_filename)
```
