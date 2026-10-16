#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <target>"
  exit 1
fi

TARGET="$1"
ARTIFACTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/artifacts"
mkdir -p "$ARTIFACTS_DIR"
REPORT="$ARTIFACTS_DIR/zap_report.html"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to run ZAP."
  exit 2
fi

docker run --rm -v "$ARTIFACTS_DIR:/zap/wrk" owasp/zap2docker-stable zap-baseline.py -t "$TARGET" -r /zap/wrk/$(basename "$REPORT") -q
echo "ZAP report generated at $REPORT"
