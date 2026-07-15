#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE:-http://localhost:8000}"
for path in /health / /work; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE$path")
  echo "$path -> $code"
  [ "$code" = "200" ] || { echo "FAIL: $path returned $code"; exit 1; }
done
echo "smoke OK"
