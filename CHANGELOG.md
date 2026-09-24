# Changelog

All notable changes to detdrift are summarized here in plain language.
Versions follow [SemVer](https://semver.org/). The JSON report uses a separate
integer `schema_version` (see [docs/json-report.md](docs/json-report.md)).

## 1.0.0 - 2026-09-24

Stable 1.0: Phase 4 dialects are in, and the report/CLI contract is frozen.

- **Stable report contract:** `schema_version` **1** is the 1.0 JSON report
  contract (additive optional keys allowed; breaking key changes bump the
  integer). Exit codes `0` / `1` / `2` stay part of the interface.
- **Dialects:** Sigma (default) plus optional KQL and SPL field extractors
  (`--dialect sigma|kql|spl|auto`). Reusable Action accepts `dialect`.
- **Install:** from GitHub for now (no PyPI publish in this release):
  `pip install git+https://github.com/chriswayneh/detdrift.git@v1.0.0`
- Pin the Action at `@v1.0.0` rather than `@main`.

## 0.6.1 - 2026-09-24

- Action `dialect` input wired to `detdrift diff --dialect`.
- CI dialect demos for KQL/SPL fixtures when present.

## 0.6.0 - 2026-09-24

- Optional **SPL** field extraction (`Field=`, `stats ... by`, `table`,
  `rex field=`). Not a search engine.

## 0.5.0 - 2026-09-24

- Optional **KQL** field extraction (`where` / `project` /
  `summarize ... by` / `sort by`). Not a query engine.
- `--dialect sigma|kql|auto` on `diff` / `fields`.

## 0.4.2 - 2026-09-24

- Flat JSON / fields-list / event-array sample importers.
- docs/importers.md and SARIF CI example.

## 0.4.1 - 2026-09-24

- SARIF 2.1.0 output (`--format sarif`) for CI / PR annotations.

## 0.4.0 - 2026-09-24

- Warn when the after sample looks empty or incomplete.

## 0.3.0 - 2026-09-24

- `detdrift propose-patch` (mapping notes or draft unified diff; review only).
- Agent skill at `skills/detdrift/SKILL.md`.

## 0.2.1 - 2026-09-24

- UTF-8 BOM-safe NDJSON/JSON loading (Windows editors).

## 0.2.0 - 2026-09-24

- Stronger Sigma field extraction; recursive rules discovery.
- Versioned JSON report (`schema_version`: 1).
- `--fail-on-severity` / `--fail-on-tag`.
- Reusable GitHub Action (`action.yml`).

## 0.1.0

- First public release: `diff`, `fields`, `init`, demo fixtures, pytest, CI.
