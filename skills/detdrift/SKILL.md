# detdrift skill

Help a human check whether a telemetry schema change would silence Sigma rules, and optionally draft mapping notes or a patch for review.

## When to use

- A pipeline, ECS mapping, or agent update renamed or dropped fields.
- Someone asks "which detections break if `CommandLine` becomes `cmd`?"
- CI or a local check needs a before/after field impact report.

## Tools (offline, no API keys)

| Command | Purpose |
|---------|---------|
| `detdrift diff -b BEFORE -a AFTER -r RULES` | IMPACTED / SAFE report. Exit 1 if any rule loses a before-field. |
| `detdrift fields RULE` | List field refs from one rule (Sigma / KQL / SPL; `--dialect auto` by extension). |
| `detdrift propose-patch -b BEFORE -a AFTER -r RULES` | Draft mapping notes (default) or a unified diff (`--format patch`). |
| `detdrift init [DIR]` | Write demo fixtures (`CommandLine` → `cmd`). |

`BEFORE` / `AFTER` are NDJSON/JSONL files or directories. Rules are discovered recursively under `-r`.

## Workflow

1. Run `detdrift diff` on the before/after samples and rules dir.
2. If IMPACTED, run `detdrift propose-patch` (notes first).
3. When renames are obvious (e.g. `CommandLine` removed and `cmd` added), notes suggest the mapping; `--format patch` emits a draft unified diff.
4. **Human reviews and applies.** Do not auto-commit. Do not edit rules in place unless the human explicitly asks after reviewing the draft.
5. Re-run `detdrift diff` after applying fixes; expect PASS / exit 0 when fields are restored under the new names.

## Dialects

Sigma is default for `diff`. Optional offline extractors: `--dialect kql` (`*.kql`), `--dialect spl` (`*.spl`), or `auto` (by extension). Not query engines.

## Guardrails

- Offline by default. No network, no SIEM credentials.
- `propose-patch` writes to stdout or `--output` only. It never modifies the rules tree by itself.
- SAFE means referenced fields still exist — not that the rule will fire.
- Do not evaluate Sigma `condition` logic; that is out of scope for detdrift.

## Demo (repo fixtures)

```bash
detdrift diff --before fixtures/before --after fixtures/after --rules rules
detdrift propose-patch --before fixtures/before --after fixtures/after --rules rules
detdrift propose-patch --before fixtures/before --after fixtures/after --rules rules --format patch
```
