#!/bin/bash
# Run inside docker

. /opt/venv/bin/activate

# get containing folder:
cd "$(dirname "$0")"
apt-get install -y libkrb5-dev  # Avoid: "Command 'krb5-config --libs gssapi' returned non-zero exit status 127."
python -m pip install -e ".[dev]"
python -m pytest
