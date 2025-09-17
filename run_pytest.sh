#!/bin/bash
# Run inside docker

. /opt/venv/bin/activate

python -m pip install -e ".[dev]"
python -m pytest