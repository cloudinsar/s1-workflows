#!/bin/bash
# Run inside docker

. /opt/venv/bin/activate

# get containing folder:
cd "$(dirname "$0")"
python -m pip install -e ".[dev]"
python -m pytest
