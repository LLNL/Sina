#!/bin/bash

# Register spack package and install it
SPACK=`which spack`

if [ -z "${SPACK}" ]; then
    >&2 echo Could not determine location of spack. Please ensure it is in your PATH.
    exit 1
fi

set -e
SCRIPT_DIR=`dirname ${BASH_SOURCE[0]}`
branch=$(git rev-parse --abbrev-ref HEAD)
repo_namespace=mnoda-${branch}

# During Bamboo builds, we can get a race condition between the builds for
# different machines (e.g. rzgenie and rzuseq). To avoid this, if SYS_TYPE
# is set, we append this to the Spack repo name (it is not set on non-LC,
# machines, so we can't do this unconditionally).
if [ ! -z ${SYS_TYPE+x} ]; then
    repo_namespace=${repo_namespace}-${SYS_TYPE}
fi

if [ -z ${SPACK_COMPILER+x} ]; then
    SPACK_COMPILER=clang
fi

temp_repo_location=spack_repo
ns_repo_location="${temp_repo_location}/${repo_namespace}"

# Do this before removing spack_repo or spack complains a lot
if [[ $($SPACK repo list | grep "${ns_repo_location}") ]]; then
    $SPACK repo remove ${ns_repo_location}
fi

rm -fr ${temp_repo_location}
mkdir -p ${temp_repo_location}
cd ${temp_repo_location}

$SPACK repo create $repo_namespace
$SPACK repo add $repo_namespace
cd ..
mkdir -p ${ns_repo_location}/packages/mnoda
cp ${SCRIPT_DIR}/package.py ${ns_repo_location}/packages/mnoda/
$SPACK setup ${repo_namespace}.mnoda@develop%${SPACK_COMPILER} ${@:1}

# Clean up since we don't need this any more
$SPACK repo remove ${ns_repo_location}
