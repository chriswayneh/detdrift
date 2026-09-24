# Contributing

Thanks for taking a look. detdrift is a small offline CLI. Keep changes
focused on schema-vs-rule field impact. It is not a Sigma matcher.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest -q
```

Python 3.12 or newer.

## Pull requests

- Run the tests above before opening a PR.
- Prefer small, reviewable diffs.
- Match the existing voice in docs: plain language, no marketing fluff.
- Do not use em dashes or en dashes in user-facing text. Use commas, periods,
  or plain hyphens.
- Do not invent star counts, download numbers, or other fake claims.
- New CLI flags need a short README note and a test when practical.
- Keep the core contract: IMPACTED means a referenced field was in the before
  schema and is missing from the after schema.

## Scope reminders

In scope: field extraction, rules discovery, reports, CI helpers, docs.

Out of scope for now: full Sigma condition evaluation, live SIEM connectors,
auto-applied patches, and LLM features (see ROADMAP Phase 2).

## Code layout

| Path | Role |
|------|------|
| `src/detdrift/` | Library and CLI |
| `tests/` | pytest |
| `rules/`, `fixtures/` | Demo samples |
| `action.yml` | Reusable GitHub Action |
| `docs/json-report.md` | JSON report contract |

## Questions

Open an issue on GitHub if something is unclear. Say what you ran and what
you expected.
