#!/bin/bash
# Run inside docker

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

. /opt/venv/bin/activate

cd /opt || exit
# TODO: Checkout specific commit
# only clone if not existing
if [ -d /opt/openeo-geopyspark-driver ]; then
  echo "/opt/openeo-geopyspark-driver already exists, skipping git clone"
else
  git clone --recursive --shallow-submodules https://github.com/Open-EO/openeo-geopyspark-driver --depth 1
fi
cd /opt/openeo-geopyspark-driver || exit

# jep is difficult to install and is not needed, so disable:
sed -i '/jep==/ s/^/# /' setup.py

# Avoid "Command 'krb5-config --libs gssapi' returned non-zero exit status 127."
sed -i '/gssapi>/ s/^/# /' setup.py

# first pip install could fail, so run twice:
python3 -m pip install -q -e . --extra-index-url https://artifactory.vgt.vito.be/api/pypi/python-openeo/simple || echo "Command failed, but ignored"
python3 -m pip install -q -e . --extra-index-url https://artifactory.vgt.vito.be/api/pypi/python-openeo/simple

# TODO: Make get-jars available as package script, so not the whole repo needs to be downloaded
python3 scripts/get-jars.py --python-version 3.1 jars

cd "$SCRIPT_DIR" || exit
# General dependencies are probably already installed. Now download test dependencies:
python -m pip install -q -e ".[dev]"
python -m pytest
