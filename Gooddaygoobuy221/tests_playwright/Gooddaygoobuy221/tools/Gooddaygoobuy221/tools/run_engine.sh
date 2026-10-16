#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
SCRIPT="$ROOT_DIR/tools/autotest_engine.py"

if [ $# -lt 1 ]; then
  echo "Usage: $0 <target-url>"
  echo "Example: $0 https://staging.example.com"
  exit 1
fi

TARGET="$1"
shift

python3 "$SCRIPT" init
python3 "$SCRIPT" run --target "$TARGET" --do-load --do-security
