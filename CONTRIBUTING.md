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

## Installed-package check

From the repository root, with your development environment activated:

```bash
python -m pip install build
python -m build --wheel
python scripts/check-installed.py
```

The check expects exactly one `detdrift-*.whl` in `dist/`. It installs that wheel
and its runtime dependencies in a temporary virtual environment, then checks
the console command, module entry point, generated demo, JSON report, and exit
codes `0`, `1`, and `2` outside the checkout. It requires access to the package
index to install dependencies. CI runs it on Linux and Windows.

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
