#!/bin/bash
# Needs to be used while Sina is available; see README.md

if [ $# -ne 0 ]; then
  SOURCE_DIR=$1
else
  SOURCE_DIR='.'
fi
echo "Building fukushima database from source directory $SOURCE_DIR..."

rm -rf files data.sqlite

set -e

tar -xzf $SOURCE_DIR/../raw_data/fukushima.tgz
python $SOURCE_DIR/fukushima_csv2mnoda.py --show-status data/AMS\ C12\ Sea\ Data.csv .
sina ingest files/AMS_C12_SeaData.json -d data.sqlite

rm -rf data
