# detdrift

**If this telemetry field mapping changes, which detection rules go silent?**

`detdrift` is a tiny CLI + CI check: point it at Sigma rules and a before/after NDJSON sample (or schema), and it reports which rules reference fields that existed *before* but vanished *after*. Schema drift → detection blast radius. Not a SIEM. Not a full Sigma match engine.

```
CommandLine → cmd   ──►  proc_whoami.yml goes dark
```

## Why

Pipelines rename fields. ECS mappings shift. A vendor agent update quietly drops `CommandLine` for `cmd`. Your Sigma library still deploys. Nothing alerts — because nothing *can* alert.

Most tools ask "does this event match?" detdrift asks **"will this rule ever see its fields again?"**

## 60-second demo

```bash
pip install -e ".[dev]"

# identical schemas → green
detdrift diff --before fixtures/before --after fixtures/before --rules rules
# exit 0

# CommandLine renamed to cmd → red
detdrift diff --before fixtures/before --after fixtures/after --rules rules
# exit 1 — IMPACTED: proc_whoami.yml (missing: CommandLine)

# or:
./examples/demo.sh
```

Sample output (drift case):

```
detdrift — schema → detection blast radius
================================================
Rules scanned:    1
Before fields:    3
After fields:     3
Removed fields:   CommandLine

IMPACTED (1) — rules that would go silent:
  ✗ proc_whoami.yml
      title:   Whoami Execution
      missing: CommandLine
      refs:    CommandLine, Image

Result: FAIL — detection coverage at risk.
```

## Install

```bash
pip install -e ".[dev]"   # from a clone
# or once published:
# pip install detdrift
```

Requires Python 3.12+.

## Commands

| Command | Purpose |
|--------|---------|
| `detdrift diff -b BEFORE -a AFTER -r RULES` | Main: blast-radius report; exit **1** if any rule impacted |
| `detdrift fields RULE.yml` | Debug: list field refs extracted from one rule |
| `detdrift init [DIR]` | Drop sample rules + before/after fixtures |

Options for `diff`:

- `--json` — machine-readable report
- `-o/--output PATH` — also write the report to a file

`BEFORE` / `AFTER` may be a single NDJSON/JSONL file or a directory of them.

## How it works

1. **Schema** — union of top-level keys across NDJSON events (plus one-level dotted paths for nested objects).
2. **Fields** — walk each Sigma `detection` block; collect selection keys; strip modifiers after `|` (`CommandLine|contains` → `CommandLine`).
3. **Diff** — for each rule, if any referenced field ∈ before and ∉ after → **IMPACTED**.

Exit codes (CI-friendly):

| Code | Meaning |
|------|---------|
| 0 | No impacted rules |
| 1 | ≥1 rule would go silent |
| 2 | Bad paths / parse errors |

## GitHub Action / CI

CI workflow definition lives at [`docs/ci/detdrift.yml`](docs/ci/detdrift.yml) (copy into `.github/workflows/` in your fork or this repo once your GitHub token has the `workflow` scope). It runs pytest and asserts:

- before vs before → exit 0
- before vs after (demo rename) → exit 1

Wire it into your own pipeline:

```yaml
- run: pip install detdrift
- run: detdrift diff --before samples/before.jsonl --after samples/after.jsonl --rules detections/
```

## Scope (sharp edges)

**This is**

- Schema blast-radius analysis for Sigma field references
- A CI gate for telemetry mapping changes
- A debug aid (`fields`) for what a rule actually touches

**This is not**

- A Sigma matcher / correlator / SIEM
- A full Sigma compiler (no `condition` evaluation, no pipelines, no backends)
- A guarantee that a "SAFE" rule will fire — only that its *referenced fields still exist*

Known limitations of the MVP:

- Keyword-only detections (no field keys) are not meaningful here
- Nested paths beyond one level under event dicts are not expanded
- Modifiers are stripped; lists/maps under fields are not semantically validated
- Multi-document YAML and rule correlations are out of scope

## Docs

- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md) — phases 0–4

## License

MIT © 2026 Christopher Hickman
