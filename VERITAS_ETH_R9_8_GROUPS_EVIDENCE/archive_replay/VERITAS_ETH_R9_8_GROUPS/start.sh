#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -e ".[matching]"
exec uvicorn veritas.api.main:app --host 127.0.0.1 --port 8080
