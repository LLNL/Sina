#!/bin/bash
# Needs to be used while Sina is available; see README.md

if [ $# -ne 0 ]; then
  SOURCE_DIR=$1
else
  SOURCE_DIR='.'
fi
echo "Building noaa database from source directory $SOURCE_DIR..."

rm -rf files data.sqlite

set -e

tar -xzf $SOURCE_DIR/../raw_data/noaa.tar.gz

python $SOURCE_DIR/noaa_csv2mnoda.py --show-status \
  0123467/2.2/data/1-data/WCOA11-01-06-2015_data.csv .
sina ingest files/WCOA11-01-06-2015.json -d data.sqlite

rm -rf 0123467
