#!/bin/bash
# Needs to be used while Sina is available; see README.md

set -e
rm -rf temp && mkdir temp
tar -C temp -xzf ../raw_data/fukushima.tgz
rm -rf files && rm -f data.sqlite
python fukushima_csv2mnoda.py --show-status temp/data/AMS\ C12\ Sea\ Data.csv .
sina ingest files/AMS_C12_SeaData.json -d data.sqlite
rm -rf temp
