#!/usr/bin/env bash
# detdrift 60-second demo: green on identical schemas, red when CommandLine → cmd
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v detdrift >/dev/null 2>&1; then
  echo "detdrift not on PATH — install with: pip install -e '.[dev]'" >&2
  exit 2
fi

echo "==> Green path: before vs before (expect exit 0)"
set +e
detdrift diff --before fixtures/before --after fixtures/before --rules rules
green=$?
set -e
echo "exit=$green"
echo

echo "==> Red path: before vs after (CommandLine renamed to cmd — expect exit 1)"
set +e
detdrift diff --before fixtures/before --after fixtures/after --rules rules
red=$?
set -e
echo "exit=$red"
echo

if [[ "$green" -eq 0 && "$red" -eq 1 ]]; then
  echo "Demo OK — schema drift correctly flagged the whoami rule."
  exit 0
fi

echo "Demo unexpected: green=$green (want 0), red=$red (want 1)" >&2
exit 1
