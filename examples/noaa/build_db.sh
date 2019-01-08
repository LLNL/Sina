#!/bin/bash
# Needs to be used while Sina is available; see README.md

set -e
mkdir temp
tar -C temp -xzf ../raw_data/noaa.tar.gz
python noaa_csv2mnoda.py --show-status temp/0123467/2.2/data/1-data/WCOA11-01-06-2015_data.csv .
sina ingest files/WCOA11-01-06-2015.json -d data.sqlite
rm -rf temp
