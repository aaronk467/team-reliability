#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install --no-deps -e .
(cd frontend && npm ci --cache "${TMPDIR:-/tmp}/responsewatch-npm-cache" && npm run build)
.venv/bin/python -m pytest -q
