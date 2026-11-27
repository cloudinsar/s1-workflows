#!/bin/bash
set -euxo pipefail
# Run inside docker

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="$HOME/.nvm"
# shellcheck source=/dev/null
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" 1>/dev/null 2>&1
nvm install 24 1>/dev/null 2>&1
node --version
export PATH="${PATH}:/root/.nvm/versions/node/v24.11.1/bin"

# shellcheck source=/dev/null
. /opt/venv/bin/activate

cd "$SCRIPT_DIR"
# General dependencies are probably already installed. Now download test dependencies:
python -m pip install -q -e ".[dev]"

mypy --ignore-missing-imports --no-strict-optional --allow-untyped-globals --allow-redefinition --no-warn-unreachable sar

python -m pytest
