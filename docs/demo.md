# Terminal demo

The README GIF replays actual output captured from the published
`detdrift` **v1.1.0** package on 2026-11-05 (America/Chicago), using only the
fictional starter fixtures from `detdrift init`. Timing is adjusted for README
readability. It is a recorded replay, not a live CI run.

## What it shows

1. Confirm the installed version (`1.1.0`).
2. `detdrift init .` writes a sample Sigma rule and before/after NDJSON where
   `CommandLine` is renamed to `cmd`.
3. Identical schemas (`before` vs `before`) exit **0** — the whoami rule is SAFE.
4. Drifted schemas (`before` vs `after`) exit **1** — the whoami rule is IMPACTED
   because it still references the removed `CommandLine` field.

## Run it yourself

Use Python 3.12 or newer in an isolated environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install "git+https://github.com/chriswayneh/detdrift.git@v1.1.0"

mkdir detdrift-demo && cd detdrift-demo
../.venv/bin/detdrift --version
../.venv/bin/detdrift init .
../.venv/bin/detdrift diff --before fixtures/before --after fixtures/before --rules rules
../.venv/bin/detdrift diff --before fixtures/before --after fixtures/after --rules rules
```

The second `diff` intentionally exits with code **1**. That is the expected demo
result, not an installation error. The package is not on PyPI; install from the
versioned GitHub URL above. Checks run locally and offline after install.

## Re-record the GIF

Requires [vhs](https://github.com/charmbracelet/vhs) (and `ttyd`) plus a
monospace font such as JetBrains Mono:

```bash
./scripts/record-demo.sh
```

That script installs the v1.1.0 package into a throwaway venv, records
`docs/assets/demo.gif` from `scripts/demo.tape`, and starts no Docker containers.

## Text alternative

The [Quick start](../README.md#quick-start) section shows the same output in
text, including the JSON report excerpt.
