#!/usr/bin/env bash
# tools/run_engine.sh
# Simple one-button runner for local use.
set -euo pipefail
ROOT_DIR=$(dirname "$(dirname "$0")")
SCRIPT="$ROOT_DIR/Gooddaygoobuy221/tools/autotest_engine.py"
if [ ! -f "$SCRIPT" ]; then
  SCRIPT="$ROOT_DIR/Gooddaygoobuy221/tools/autotest_engine.py"
fi
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <target-url>"
  echo "Example: $0 https://staging.example.com"
  exit 1
fi
TARGET=$1
shift
# initialize venv and playwright if missing
python3 "$SCRIPT" init
# run full pipeline: smoke + e2e + load + security (load & security optional)
python3 "$SCRIPT" run --target "$TARGET" --do-load --do-security
