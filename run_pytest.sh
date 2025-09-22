#!/bin/bash
# Run inside docker

. /opt/venv/bin/activate

# get containing folder:
cd "$(dirname "$0")"
# TODO: Make get-jars available as package script, so not the whole repo needs to be downloaded
#git clone --recursive https://github.com/Open-EO/openeo-geopyspark-driver --depth 1
cd openeo-geopyspark-driver
python scripts/get-jars.py --force-download jars
python -m pip install -e ".[dev]"
cd ..
apt-get install -y libkrb5-dev  # Avoid: "Command 'krb5-config --libs gssapi' returned non-zero exit status 127."
python -m pip install -e ".[dev]"
python -m pytest
