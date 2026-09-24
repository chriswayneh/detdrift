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
      level:   low
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
| `detdrift diff -b BEFORE -a AFTER -r RULES` | Main check. Exit 1 if any rule is impacted (or if a fail-on filter matches). |
| `detdrift fields RULE.yml` | List field names pulled from one rule. |
| `detdrift init [DIR]` | Write sample rules and before/after fixtures. |
| `detdrift propose-patch -b BEFORE -a AFTER -r RULES` | Draft mapping notes (default) or a unified diff (`--format patch`). Review only; no in-place edits. |

Useful `diff` flags:

- `--json` for a machine-readable report (see [JSON report](docs/json-report.md))
- `--format sarif` (or `--format json`) for SARIF 2.1.0 / JSON; upload via docs/ci/sarif-example.yml
- `-o` / `--output PATH` to also write the report to a file
- `--fail-on-severity high,critical` to exit 1 only when an IMPACTED rule is at least that severe (still prints all IMPACTED rules)
- `--fail-on-tag attack.t1059` to exit 1 only when an IMPACTED rule has a matching tag (substring, case-insensitive)
- `--ignore GLOB` to skip extra rule paths (repeatable). Default ignored directory names include `.git`, `.github`, `vendor`, and `tests`
- Empty or clearly incomplete **after** samples produce a WARNING (stderr + report). An empty file is not the same as "nothing removed".

`BEFORE` and `AFTER` can be one NDJSON/JSONL file or a directory of them. Rules under `--rules` are found recursively (`*.yml` / `*.yaml`).

### Fail-on example

The demo whoami rule is `level: low`. With a rename that impacts it:

```bash
# still prints IMPACTED, but exit 0 because low is below the filter
detdrift diff -b fixtures/before -a fixtures/after -r rules --fail-on-severity high,critical

# exit 1 only if an IMPACTED rule carries a matching tag
detdrift diff -b fixtures/before -a fixtures/after -r rules --fail-on-tag attack.t1059
```

When both filters are set, a rule must match severity and tag.


## Propose a fix (Phase 2)

When `diff` reports IMPACTED rules, draft mapping notes or a patch for human review:

```bash
# mapping notes (default): heuristic CommandLine -> cmd when obvious
detdrift propose-patch --before fixtures/before --after fixtures/after --rules rules

# unified diff draft (still does not touch rule files)
detdrift propose-patch --before fixtures/before --after fixtures/after --rules rules --format patch -o draft.patch
```

Heuristics suggest a rename only when the mapping is obvious (known aliases or a single clear added field). Otherwise you get notes listing unclear removals. Nothing is written into the rules tree unless you apply a draft yourself. No auto-commit. Offline; no API keys.

Agent skill: [`skills/detdrift/SKILL.md`](skills/detdrift/SKILL.md).

## How it works

1. Build a field set from the before samples (top-level keys, plus one level of nested keys).
2. Do the same for the after samples.
3. Walk each Sigma `detection` block, collect selection field names (including lists of maps and common nested paths), and drop modifiers after `|` (so `CommandLine|contains` becomes `CommandLine`).
4. If a rule references a field that exists before and is missing after, mark it IMPACTED.

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | No failing IMPACTED rules (none at all, or none matching `--fail-on-*`) |
| 1 | At least one rule would go quiet (or matched the fail-on filter) |
| 2 | Bad paths or parse errors |

## CI

The workflow file is at [`.github/workflows/detdrift.yml`](.github/workflows/detdrift.yml). It runs the tests and checks the demo exit codes.

### Reusable Action

Other repos can call the composite action at the repo root (`action.yml`):

```yaml
- uses: chriswayneh/detdrift@main
  with:
    before: samples/before.jsonl
    after: samples/after.jsonl
    rules: detections/
    # optional:
    # fail-on-severity: high,critical
    # fail-on-tag: attack.t1059
```

Pin a release tag when you have one (for example `@v0.2.0`) instead of `@main`.

Or install and run the CLI yourself:

```yaml
- run: pip install "detdrift @ git+https://github.com/chriswayneh/detdrift.git@main"
- run: detdrift diff --before samples/before.jsonl --after samples/after.jsonl --rules detections/
```

## What this is and is not

**Is:** a check for Sigma field references against a schema change. A CI gate for mapping edits. Small helpers (`fields`, `propose-patch`) for seeing what a rule touches and drafting mapping notes.

**Is not:** a Sigma matcher, correlator, or SIEM. It does not evaluate `condition` blocks. A rule that is not IMPACTED still might not fire for other reasons. This only says the fields it names are still present.

Current limits:

- Keyword-only detections (no field keys) do not produce references, so they will not show as IMPACTED
- Nested event paths deeper than one level in NDJSON samples are not expanded
- Modifiers are stripped; values are not validated
- Multi-document YAML and correlations are out of scope

## Docs

- [Architecture](ARCHITECTURE.md)
- [Roadmap](ROADMAP.md) (phases 0 to 4)
- [JSON report schema](docs/json-report.md)
- [Dogfood notes](docs/dogfood.md) (SigmaHQ process_creation pack)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)

## License

MIT (c) 2026 Christopher Hickman
