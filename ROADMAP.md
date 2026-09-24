# Roadmap

Plan for detdrift by phase. Each phase should ship something you can run. Later phases do not block earlier ones.

## Phase map

| Phase | Name | Outcome | Status |
|-------|------|---------|--------|
| **0** | Foundation | Public repo, working CLI, demo fixtures, CI, docs | Shipped |
| **1** | Harden | Better field extraction; reusable Action | Shipped (v0.2) |
| **2** | Assist | Optional propose-patch helper and agent skill | Shipped (v0.3) |
| **3** | Connect | Import common export formats; SARIF / PR notes | Shipped (v0.4) |
| **4** | Broaden | Optional support for other rule languages | Started (v0.5) |

## Phase 0: Foundation (v0.1)

**Goal:** Clone it, run the demo in about a minute.

- [x] `detdrift diff` before/after impact report
- [x] `detdrift fields` for one rule
- [x] `detdrift init` sample project
- [x] Demo fixtures (`CommandLine` to `cmd`)
- [x] pytest suite
- [x] CI workflow (in repo)
- [x] README, ARCHITECTURE, ROADMAP
- [x] Public repo `chriswayneh/detdrift`
- [x] Tag `v0.1.0`

**Done when:** repo is public and `pip install -e .` plus the demo script behave as documented.

## Phase 1: Harden (v0.2)

**Goal:** Hold up against real detection repos without turning into a matcher.

- [x] Stronger Sigma field extraction (lists under selections, common nested paths)
- [x] Recursive rules discovery with clear ignore patterns
- [x] Documented, versioned JSON report shape (`schema_version`: 1)
- [x] `--fail-on-severity` / `--fail-on-tag` filters
- [x] Reusable GitHub Action (`action.yml`, `uses: chriswayneh/detdrift@...`)
- [x] CONTRIBUTING and SECURITY docs

**Done when:** it runs cleanly on a public Sigma sample set, and another repo can call the Action.

**Dogfood (v0.2.0 / v0.2.1):** Sparse SigmaHQ rules/windows/process_creation (~1185 rules), synthetic CommandLine to cmd. Result: 914 IMPACTED / 271 SAFE. UTF-8 BOM from PowerShell handled as of v0.2.1. See [docs/dogfood.md](docs/dogfood.md).

## Phase 2: Assist (v0.3)

**Goal:** Optional helpers that draft fixes you still review yourself.

- [x] `detdrift propose-patch` with `--format notes` (default) and `--format patch`
- [x] Heuristic renames when obvious (e.g. `CommandLine` removed + `cmd` added); otherwise mapping notes only
- [x] No in-place rule edits by default; stdout / `--output` only; no auto-commit; offline
- [x] Coding-agent skill at `skills/detdrift/SKILL.md` wrapping `diff`, `fields`, and propose
- [x] Tests for notes, patch, and non-modification of rules

**Done when:** the propose flow is documented, and `diff` / `fields` still work offline with no API keys.

**Shipped:** v0.3.0

## Phase 3: Connect (v0.4)

**Goal:** Meet people where their samples already are. Still based on files you provide.

- [x] Importers for common export shapes: flat JSON field map, `{"fields": [...]}`, JSON event array; Sysmon-flat NDJSON already worked (v0.4.2; docs/importers.md)
- Optional OCSF profile hints (not the main product story)
- [x] SARIF output and PR check annotations (v0.4.1; see docs/ci/sarif-example.yml)
- [x] Warn when an after sample is empty or clearly incomplete (an empty file is not the same as "nothing removed") (v0.4.0)

**Done when:** one importer and a SARIF path show up in a CI example.

**Shipped:** v0.4.0 warnings; v0.4.1 SARIF; v0.4.2 flat JSON / fields-list / event-array samples + docs/importers.md + docs/ci/sarif-example.yml.

## Phase 4: Broaden (v1.x, optional)

**Goal:** Same question for more rule languages, only if earlier phases stick.

- [x] Pluggable field extractors — simple **KQL** field refs (v0.5.0; `--dialect sigma|kql|auto`)
- [ ] Optional SPL field refs (same CLI contract; not started)
- [ ] Stable 1.0 contract for schema and report JSON
- [ ] Publish on PyPI: `pip install detdrift`

**Shipped so far:** v0.5.0 adds offline KQL extraction (`where` / `project` / `summarize by` / `sort by`). Not a query engine. Sigma remains the default. See README "Other dialects".

**Done when:** a second rule dialect works behind the same CLI, and the version is 1.0.

## Not on the roadmap

- Building a SIEM, lake, or federated search product
- Full Sigma condition evaluation or a correlation engine
- Folding this into [local-mcp-toolbox](https://github.com/chriswayneh/local-mcp-toolbox) (related tools, separate repos)
- Requiring live credentials to a customer SIEM or lake
- Exploitation, brute force, or attack simulation features

## How we will know it is useful

| Signal | Why it matters |
|--------|----------------|
| Someone clones and runs the demo quickly | The install path works |
| Another repo uses the Action | It helps real CI |
| Issues about field extraction on real rules | People are using it beyond the sample |
| People ask for match evaluation and we keep saying no | The scope stays clear |

## Suggested order

1. Finish Phase 0 polish (docs voice, workflow in `.github/workflows`).
2. Run Phase 1 against a real rules folder or a public Sigma pack. (Done: see docs/dogfood.md)
3. Phase 2 Assist shipped (v0.3.0): propose-patch + skill. Keep offline; no auto-apply.
