# Roadmap

Plan for detdrift by phase. Each phase should ship something you can run. Later phases do not block earlier ones.

## Phase map

| Phase | Name | Outcome | Status |
|-------|------|---------|--------|
| **0** | Foundation | Public repo, working CLI, demo fixtures, CI, docs | Shipped |
| **1** | Harden | Better field extraction; reusable Action | Shipped (v0.2) |
| **2** | Assist | Optional propose-patch helper and agent skill | Later |
| **3** | Connect | Import common export formats; SARIF / PR notes | Later |
| **4** | Broaden | Optional support for other rule languages | Optional |

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

- `detdrift propose-patch` (optional): draft mapping notes or fixture/rule patches when fields disappear
- A coding-agent skill that wraps `diff`, `fields`, and propose
- No auto-commit. Output is a patch or PR body for a human

**Done when:** the propose flow is documented, and `diff` / `fields` still work offline with no API keys.

## Phase 3: Connect (v0.4)

**Goal:** Meet people where their samples already are. Still based on files you provide.

- Importers for common export shapes (for example flattened CloudTrail or Sysmon NDJSON packs)
- Optional OCSF profile hints (not the main product story)
- SARIF output and PR check annotations
- Warn when an after sample is empty or clearly incomplete (an empty file is not the same as "nothing removed")

**Done when:** one importer and a SARIF path show up in a CI example.

## Phase 4: Broaden (v1.x, optional)

**Goal:** Same question for more rule languages, only if earlier phases stick.

- Pluggable field extractors (simple KQL or SPL field refs)
- Stable 1.0 contract for schema and report JSON
- Publish on PyPI: `pip install detdrift`

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
3. Add Phase 2 helpers only after people are actually running `diff` in CI.
