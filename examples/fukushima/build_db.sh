#!/bin/bash
# Needs to be used while Sina is available; see README.md

set -e
mkdir temp
tar -C temp -xzf ../raw_data/fukushima.tgz
python fukushima_csv2mnoda.py -d temp/data/AMS\ C12\ Sea\ Data.csv .
sina ingest files/AMS_C12_SeaData.json -d data.sqlite
rm -rf temp
