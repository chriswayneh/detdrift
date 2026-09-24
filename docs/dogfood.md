# Dogfood notes

Quick notes from running detdrift against a real public Sigma pack. Numbers are from one run; they are not a benchmark.

## SigmaHQ windows process_creation (v0.2.0)

- Pack: sparse clone of [SigmaHQ/sigma](https://github.com/SigmaHQ/sigma) `rules/windows/process_creation` (~1185 YAML rules).
- Synthetic schema change: `CommandLine` removed, `cmd` added (same idea as the repo fixtures).
- Result with detdrift **0.2.0**:
  - `schema_version`: 1
  - `removed`: `['CommandLine']`
  - **914 IMPACTED** (all missing `CommandLine`)
  - **271 SAFE**
  - 0 UNKNOWN (an earlier empty-missing count was a false alarm)

## UTF-8 BOM (fixed in v0.2.1)

PowerShell `Set-Content -Encoding utf8` writes a UTF-8 BOM. With 0.2.0 that made the first NDJSON pass exit 2 until the files were rewritten without a BOM. As of **0.2.1**, schema loaders open NDJSON/JSON with `encoding="utf-8-sig"`, so BOM-prefixed samples from Windows editors work without a rewrite.
