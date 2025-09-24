#!/bin/bash
# Run inside docker

. /opt/venv/bin/activate

# get containing folder:
cd "$(dirname "$0")" || exit

cd /opt || exit
# TODO: Checkout specific commit
git clone --recursive --shallow-submodules https://github.com/Open-EO/openeo-geopyspark-driver --depth 1
cd /opt/openeo-geopyspark-driver || exit

# jep is difficult to install and is not needed, so disable:
sed -i '/jep==/ s/^/# /' setup.py

# Avoid "Command 'krb5-config --libs gssapi' returned non-zero exit status 127."
sed -i '/gssapi>/ s/^/# /' setup.py

# first pip install could fail, so run twice:
python3 -m pip install -e . --extra-index-url https://artifactory.vgt.vito.be/api/pypi/python-openeo/simple || echo "Command failed, but ignored"
python3 -m pip install -e . --extra-index-url https://artifactory.vgt.vito.be/api/pypi/python-openeo/simple

# TODO: Make get-jars available as package script, so not the whole repo needs to be downloaded
python3 scripts/get-jars.py --force-download jars

# General dependencies are probably already installed. Now download test dependencies:
python -m pip install -e ".[dev]"
python -m pytest
