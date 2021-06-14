# Quick Start Guide
The following steps will compile the Sina C++ library on TOSS 3 machines
with Clang. Read the more detailed instructions for building on different
platforms or different compilers.

```shell
cd /path/to/sina

# If you didn't clone with --recursive, get the submodules
git submodule init
git submodule update

# Get on a back-end node to not bog down the login nodes.
mxterm 1 36 60

# on backend node
cd cpp
mkdir build-clang
cd build-clang
cmake -C ../CMake/host-configs/sina-linux-rhel7-ivybridge-clang@11.0.1.cmake -DCMAKE_TOOLCHAIN_FILE=../CMake/Platform/toss_3_x86_64_clang.cmake ..
make -j all test
```

# Detailed Instructions
The Sina C++ library uses CMake with BLT to configure and build. Technically,
that is all that is really needed. To make development easier, it also uses
[Uberenv](https://uberenv.readthedocs.io/) and
[Spack](https://spack.readthedocs.io/) to build needed command-line tools
and third-party libraries.

The basic build steps are as follows:
1. If there isn't a configuration file for your system, run Uberenv to make
   it and to build the needed libraries
2. Create a directory in which to do the build.
3. Run `cmake` with the configuration file from step 1.
4. Run `make` to build the library.
5. Run `make test`


## Testing all CTS compilers
To simplify testing with all the different compilers on CTS systems,
you can simply run the `run-builds.py` script in the `cpp` directory.
This will build and test with each of the pre-existing host configurations
for LC CTS systems.

## Running Uberenv

[Uberenv](https://uberenv.readthedocs.io/) automates the process of building
packages with [Spack](https://spack.readthedocs.io/) and making them
available to your build system. Sina relies on libraries like Conduit and
(optionally) Adiak. Uberenv will have Spack create these and put them in your
build environment.

**NOTE:** For our LC platforms, there are many ready-made configuration files
in the `cpp/CMake/host-configs` directory. If there is one that suits your
purposes there, you can skip this step.

Running Uberenv will:

1. Clone spack and check out a specific version
2. Build all dependencies needed by Sina
3. Write a CMake configuration file with the paths to all the needed tools
   created in the previous steps.

**NOTE:** By default, the below will force Spack to build *a lot* of tools
that you probably don't want built, such as `python`, `perl`, `tar`, and
`find`. If you're on an LC system where we have existing configurations,
this won't happen. for details on how this works, see the [section on how it
all works](#uberenv-details) below.

To run Uberenv, from the `cpp` directory, simply run

```shell
python uberenv/uberenv.py --spec "+docs+adiak+test"
```

When successful, Uberenv will create a file named
`sina-<platform>.cmake` in the current directory.

The `--spec "+docs+adiak+test"` option will pass the `+docs+adiak+test`
options to Spack to build Sian with these `dev` options.

To specify the compiler, simply add it to the `--spec` option:

```shell
python uberenv/uberenv.py --spec "+docs+adiak+test%clang"
python uberenv/uberenv.py --spec "+docs+adiak+test%intel"
python uberenv/uberenv.py --spec "+docs+adiak+test%gcc"
```

## Running Cmake & Make

Once you have a host-config file created by Uberenv (or if you're using
a pre-made one from `cpp/CMake,host-configs`), you can use that to
run `cmake` and then `make`. The compiler will be the one specified in that
file.

```shell
mkdir build
cd build
cmake -C ../<my-host-config>.cmake
```

In addition to pre-built host-config files, Sina provides pre-built
CMake toolchain files. These list many useful compiler flags that help detect
errors. We use these for our CI builds, so you should use them for your
manual builds, too. Otherwise, you risk your your branch failing to build
properly due to extra compiler warnings and warnings being treated as
errors.

The example below shows how to configure a build using clang with the
same toolchain file we use in our CI builds.

```shell
cd cpp
mkdir build-clang
cd build-clang
cmake -C ../CMake/host-configs/sina-linux-rhel7-ivybridge-clang@11.0.1.cmake -DCMAKE_TOOLCHAIN_FILE=../CMake/Platform/toss_3_x86_64_clang.cmake ..
```

Once `cmake` has succeeded, you can run `make` to build the code. The main
targets to keeps in mind are:

1. `all` will build all the code
2. `test` will run the unit tests. Note that this DOES NOT run `all`, even
   if the code for the tests was updated.
3. `docs` will build the Doxygen documentations

Some common examples are:

```shell
# Build the code
make -j all

# Build the code and run the tests
make -j all test

# Run what the CI build will run
make -j all docs test
```

If any of the unit tests fail, you can get more details by running the
binary directly rather than running `make test`.

```shell
bin/unittests
```

# Uberenv Details

For full details of how Uberenv works, it is best to see the
[Uberenv documentation](https://uberenv.readthedocs.io/). This section gives
a simple overview.

Uberenv works by reading the `.uberenv_config.json` file in the `cpp`
directory. This tells it where to find spack and which hash of spack to
check out. It also tells it where to find spack configurations and what
packages it needs to build.

Spack configurations live in the `cpp/scripts/spack/configs` directory.
In there, there are platform specific directories, each of which has a
`package.yaml` and `compilers.yaml`. Uberenv will automatically use these
to tell Spack about the compilers that are available on the machine, and
where to find common packages.

You can override the location of where Uberenv will look for its Spack
configuration via the `--spack-config-dir` option. This can be useful
for building on a laptop.

```shell
python uberenv/uberenv.py --spec "+test+docs" --spack-config-dir ~/common_spack_config/
```

Your configuration directory can have a `packages.yaml` and `compilers.yaml`
to tell Spack where to find common packages and which compilers to use.

Another useful option of Uberenv is the ability to specify where to put
Spack. This can be used to create a shared installation of libraries or to
reuse a single copy among multiple checkouts of Sina. If you do not specify
this location, an `uberenv_libs` directory will be created in the `cpp`
directory. In the example below, Spack will be check out into
`~/SINA_TPL`, and all the libraries it builds will go in that
directory.

```shell
python uberenv/uberenv.py --prefix ~/SINA_TPL --spec "+test" --spack-config-dir ~/common_spack_config/
```

# Building Shared Libraries & Host Configuration Files

The essence of the example at the top of this file is very simple:
```shell
mkdir -p cpp/build-clang && cd cpp/build-clang
cmake -C ../CMake/host-configs/sina-linux-rhel7-ivybridge-clang@11.0.1.cmake -DCMAKE_TOOLCHAIN_FILE=../CMake/Platform/toss_3_x86_64_clang.cmake ..
make -j all test
```

It also runs quite quickly since it doesn't require any third party libraries
or tools to be built. The reason this works is because the file
`cpp/CMake/host-configs/sina-linux-rhel7-ivybridge-clang@11.0.1.cmake` already
exists and points to publicly-accessible libraries and tools installed at
`/collab/usr/gapps/wf/dev/SINA_TPL`.

To create more of these host-configs and the associated libraries, you need to
run Uberenv as the `workflow` service account, giving it the right options.
Before this though, you may need to update or create the appropriate
files in `scripts/configs` to tell Spack about a new compiler or where to
find system packages on the new platform. If you're creating a new shared
configuration, chances are it's because you're updating the list of compilers
or adding a new machine, so you will have to do this.

Once you have the right `packages.yaml` and `compilers.yaml`, run the below
**on a backend node**. These commands will potentially build a lot of
libraries, so you will want to make sure you're not impacting others on
the login nodes.

```shell
# Make sure to run as the workflow service account
xsu workflow

# Get xterm backend node. E.g. on rzgenie:
mxterm 1 36 60

# Commands below should be on the backend node

# check out the latest, or the specific branch you want 
cd ~/sina/cpp
git checkout develop
git pull

# Switch to "wf_dev" and set the right umask to ensure files can be
# accessed by everyone in that group.
newgrp - wf_dev
umask 0027

# The above starts a new shell, so make sure to get back to the right place
cd path/to/sina/cpp

# Use "--prefix /collab/usr/gapps/wf/dev/SINA_TPL", but set the correct spec
python uberenv/uberenv.py --prefix /collab/usr/gapps/wf/dev/SINA_TPL --spec "+test+clang+docs%clang"
```

The above will create a host configuration file at the cpp directory level.
Make sure it works by giving it to your own account and trying to run cmake
with it.

```shell
# As you, not wf_dev
cd sina/cpp
mkdir build-test
cd build-test
cmake -C ../<new-host-config>.cmake ..
make -j all test
```

If the above doesn't work, determine what went wrong and start over.

Once the above works, you should also create a toolchain file with the
right options to turn on as many compiler warnings as possible and configure
the compiler to report warnings as errors. You can see example files in
`cpp/CMake/Platform`

Once you have everything working, move your new host configuration file to
`cpp/CMake/host-configs`. Move your platform file to `cpp/CMake/Platform`.
Check everything in to git, and push it. If appropriate, also set up a CI build
to run with this configuration on a regular basis.

