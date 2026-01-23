#!/bin/bash
set -euxo pipefail
# Run inside docker

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" 1>/dev/null 2>&1
nvm install 24 1>/dev/null 2>&1
node --version
export PATH="${PATH}:/root/.nvm/versions/node/v24.11.1/bin"

# shellcheck source=/dev/null
. /opt/venv/bin/activate
#workflodocker
#cd /opt
## TODO: Checkout specific commit
## only clone if not existing
#if [ -d /opt/openeo-geopyspark-driver ]; then
#  echo "/opt/openeo-geopyspark-driver already exists, skipping git clone"
#else
#  git clone --recursive --shallow-submodules https://github.com/Open-EO/openeo-geopyspark-driver --depth 1
#fi
#cd /opt/openeo-geopyspark-driver
#
## jep is difficult to install and is not needed, so disable:
#sed -i '/jep==/ s/^/# /' setup.py
#
## Avoid "Command 'krb5-config --libs gssapi' returned non-zero exit status 127."
#sed -i '/gssapi>/ s/^/# /' setup.py
#
## first pip install could fail, so run twice:
#python3 -m pip install -q -e . --extra-index-url https://artifactory.vgt.vito.be/api/pypi/python-openeo/simple || echo "Command failed, but ignored"
#python3 -m pip install -q -e . --extra-index-url https://artifactory.vgt.vito.be/api/pypi/python-openeo/simple
#
## TODO: Make get-jars available as package script, so not the whole repo needs to be downloaded
#python3 scripts/get-jars.py --python-version 3.11 jars

cd "$SCRIPT_DIR"
# General dependencies are probably already installed. Now download test dependencies:
python -m pip install -q -e ".[dev]"
python -m pytest

# mypy has error, only on GitHub Actions CI:
# tests/testutils.py:35: error: Value of type variable "_ArrayT" of "append" cannot be "ndarray[Any, Any] | DataArray | ndarray[tuple[Any, ...], dtype[Any]]"  [type-var]
# mypy --ignore-missing-imports --no-strict-optional --allow-untyped-globals --allow-redefinition --no-warn-unreachable sar/sar_coherence.py
