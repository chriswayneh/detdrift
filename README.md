# detdrift

If a telemetry field mapping changes, which Sigma rules go quiet?

detdrift is a small CLI you can run locally or in CI. Give it your Sigma rules plus a before and after NDJSON sample. It tells you which rules still need fields that disappeared after the change. It does not run detections, and it is not a SIEM.

Example: `CommandLine` gets renamed to `cmd`. A whoami rule that keys on `CommandLine` shows up as IMPACTED.

## Why bother

Pipelines rename fields. ECS mappings shift. A vendor agent update swaps `CommandLine` for `cmd`. Your Sigma pack still deploys. Nothing fires, because the fields the rules expect are gone.

Most tools ask whether an event matches a rule. detdrift asks whether the rule can still see the fields it depends on.

## Quick demo

```bash
pip install -e ".[dev]"

# same schema on both sides: exit 0
detdrift diff --before fixtures/before --after fixtures/before --rules rules

# CommandLine renamed to cmd: exit 1
detdrift diff --before fixtures/before --after fixtures/after --rules rules

./examples/demo.sh
```

Sample output when fields drift:

```
detdrift: schema change vs Sigma rules
================================================
Rules scanned:    1
Before fields:    3
After fields:     3
Removed fields:   CommandLine

IMPACTED (1): rules that would go quiet
  x proc_whoami.yml
      title:   Whoami Execution
      missing: CommandLine
      refs:    CommandLine, Image

Result: FAIL (detection coverage at risk)
```

## Install

```bash
pip install -e ".[dev]"
```

Python 3.12 or newer. PyPI install (`pip install detdrift`) comes later.

## Commands

| Command | What it does |
|--------|----------------|
| `detdrift diff -b BEFORE -a AFTER -r RULES` | Main check. Exit 1 if any rule is impacted. |
| `detdrift fields RULE.yml` | List field names pulled from one rule. |
| `detdrift init [DIR]` | Write sample rules and before/after fixtures. |

Useful `diff` flags:

- `--json` for a machine-readable report
- `-o` / `--output PATH` to also write the report to a file

`BEFORE` and `AFTER` can be one NDJSON/JSONL file or a directory of them.

## How it works

1. Build a field set from the before samples (top-level keys, plus one level of nested keys).
2. Do the same for the after samples.
3. Walk each Sigma `detection` block, collect selection field names, and drop modifiers after `|` (so `CommandLine|contains` becomes `CommandLine`).
4. If a rule references a field that exists before and is missing after, mark it IMPACTED.

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | No impacted rules |
| 1 | At least one rule would go quiet |
| 2 | Bad paths or parse errors |

## CI

The workflow file is at [`.github/workflows/detdrift.yml`](.github/workflows/detdrift.yml). It runs the tests and checks the demo exit codes.

In your own pipeline:

```yaml
- run: pip install detdrift
- run: detdrift diff --before samples/before.jsonl --after samples/after.jsonl --rules detections/
```

## What this is and is not

**Is:** a check for Sigma field references against a schema change. A CI gate for mapping edits. A small helper (`fields`) for seeing what a rule touches.

**Is not:** a Sigma matcher, correlator, or SIEM. It does not evaluate `condition` blocks. A rule that is not IMPACTED still might not fire for other reasons. This only says the fields it names are still present.

Current limits:

- Keyword-only detections (no field keys) do not produce references, so they will not show as IMPACTED
- Nested paths deeper than one level are not expanded
- Modifiers are stripped; values are not validated
- Multi-document YAML and correlations are out of scope

## Docs

- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md) (phases 0 to 4)

## License

MIT (c) 2026 Christopher Hickman
