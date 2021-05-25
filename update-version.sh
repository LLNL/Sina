#!/bin/bash

set -e

MAJOR=1
MINOR=9
PATCH=5
FULL=${MAJOR}.${MINOR}.${PATCH}

# For compatibility between OSX and Unix, we need to set a backup file and then delete it

BACKUP_EXT=version_backup

sed -i.${BACKUP_EXT} "s/set(SINA_VERSION_MAJOR .*)/set(SINA_VERSION_MAJOR ${MAJOR})/" cpp/CMakeLists.txt
sed -i.${BACKUP_EXT} "s/set(SINA_VERSION_MINOR .*)/set(SINA_VERSION_MINOR ${MINOR})/" cpp/CMakeLists.txt
sed -i.${BACKUP_EXT} "s/set(SINA_VERSION_PATCH .*)/set(SINA_VERSION_PATCH ${PATCH})/" cpp/CMakeLists.txt

sed -i.${BACKUP_EXT} "s/__VERSION__ =.*/__VERSION__ = \"${FULL}\"/" python/sina/__init__.py
sed -i.${BACKUP_EXT} "s/VERSION =.*/VERSION = \"${FULL}\"/" python/setup.py

# cleanup
find . -name "*.${BACKUP_EXT}" -delete
