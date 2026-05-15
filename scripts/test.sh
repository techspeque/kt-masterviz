#!/usr/bin/env bash
#
# Run the test suite with coverage.
#
# Any extra arguments are forwarded to pytest, so you can do things like:
#   bash scripts/test.sh -k loader
#   bash scripts/test.sh tests/test_loader.py
#   bash scripts/test.sh -x --pdb
set -euo pipefail

cd "$(dirname "$0")/.."

uv run pytest tests/ \
    -v \
    --cov=kt_masterviz \
    --cov-report=term-missing \
    "$@"
