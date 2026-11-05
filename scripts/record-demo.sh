#!/usr/bin/env bash
# Re-record docs/assets/demo.gif from the published detdrift v1.1.0 package.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="${TMPDIR:-/tmp}/detdrift-demo-record-$$"
VENV="$STAGE/venv"

cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT

command -v vhs >/dev/null || { echo "vhs is required" >&2; exit 1; }
command -v ttyd >/dev/null || { echo "ttyd is required by vhs" >&2; exit 1; }

mkdir -p "$STAGE/work"
cp "$ROOT/scripts/demo.tape" "$STAGE/work/demo.tape"

python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -q "git+https://github.com/chriswayneh/detdrift.git@v1.1.0"

export DETDRIFT_BIN_DIR="$VENV/bin"
export DETDRIFT_DEMO_HOME="$STAGE/work"
export PATH="$DETDRIFT_BIN_DIR:$PATH"

( cd "$STAGE/work" && vhs demo.tape )

mkdir -p "$ROOT/docs/assets"
cp "$STAGE/work/demo.gif" "$ROOT/docs/assets/demo.gif"
echo "Wrote $ROOT/docs/assets/demo.gif"
