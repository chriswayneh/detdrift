# Roadmap

Phased plan for `detdrift`. Each phase ships something people can run. Later phases do not unlock earlier ones.

## Phase map

| Phase | Name | Outcome | Status |
|-------|------|---------|--------|
| **0** | Foundation | Public repo, working CLI, demo fixtures, CI, docs | **Now** |
| **1** | Harden | Real-world Sigma/field extraction; better CI packaging | Next |
| **2** | Assist | Opt-in AI propose-patch + coding-agent skill | Later |
| **3** | Connect | Snapshot importers (exports only) + SARIF/PR annotations | Later |
| **4** | Broaden | Optional non-Sigma rule dialects behind the same blast-radius contract | Optional |

---

## Phase 0 — Foundation (v0.1) ✅ in progress

**Goal:** Something original people can clone and run in under a minute.

- [x] `detdrift diff` before/after blast radius
- [x] `detdrift fields` debug extraction
- [x] `detdrift init` sample project
- [x] Demo fixtures (`CommandLine` → `cmd`)
- [x] pytest suite
- [x] GitHub Actions workflow
- [x] README + ARCHITECTURE + ROADMAP
- [ ] Public GitHub repository `chriswayneh/detdrift`
- [ ] First tagged release `v0.1.0`

**Exit criteria:** Repo public; `pip install -e .` + demo script green/red as documented.

---

## Phase 1 — Harden (v0.2)

**Goal:** Survive real detection repos without becoming a matcher.

- Stronger Sigma field extraction (lists under selections, common nested ECS-style paths)
- Multi-file / recursive rules discovery with clear ignore patterns
- JSON report schema documented and versioned
- `--fail-on` thresholds (e.g. only fail on high-severity titles / tags)
- GitHub Action published for reuse (`uses: chriswayneh/detdrift/...`)
- CONTRIBUTING + SECURITY docs aligned with chriswayneh OSS norms

**Exit criteria:** Run cleanly against a public Sigma subset fixture pack; Action usable from an external repo.

---

## Phase 2 — Assist (v0.3)

**Goal:** AI where it helps, never where it hides risk.

- `detdrift propose-patch` (opt-in): draft mapping notes or fixture/rule patches when fields disappear
- Coding-agent skill wrapping `diff` + `fields` + propose
- No auto-commit; output is a patch or PR body for humans

**Exit criteria:** Documented skill + CLI propose flow; works offline for `diff`/`fields` without API keys.

---

## Phase 3 — Connect (v0.4)

**Goal:** Meet teams where their samples already are — still snapshot-based.

- Importers for common **export** shapes (e.g. flattened CloudTrail/Sysmon NDJSON packs)
- Optional OCSF *profile* hints (not an OCSF-first product brand)
- SARIF output + PR check annotations
- Completeness note in reports when after-sample is empty/partial (empty sample ≠ “no fields removed” without warning)

**Exit criteria:** One importer + SARIF path used in CI example.

---

## Phase 4 — Broaden (v1.x, optional)

**Goal:** Same blast-radius question for more rule languages — only if Phase 1–3 stick.

- Pluggable rule field extractors (KQL stubs, simple SPL field refs)
- Stable 1.0 contract for schema + report JSON
- Package on PyPI: `pip install detdrift`

**Exit criteria:** Second dialect behind the same CLI; semver 1.0.

---

## Explicitly not on the roadmap

- Building a SIEM, lake, or federated search product
- Full Sigma condition evaluation / correlation engine
- Folding into [local-mcp-toolbox](https://github.com/chriswayneh/local-mcp-toolbox) (complementary; keep separate)
- Live credentials to customer SIEM/lake as a required path
- Exploitation, brute force, or attack-simulation features

## Success metrics (lightweight)

| Signal | Why it matters |
|--------|----------------|
| Clone → demo under 60s | Adoption filter we designed for |
| External repo uses the Action | Real CI value |
| Issues about field extraction accuracy | People are running it on real rules |
| Resist feature requests that turn it into a matcher | Stay original |

## Suggested sequencing for maintainers

1. Ship Phase 0 (this week).
2. Eat dogfood: point Phase 1 at a real rules folder Chris already maintains or a public Sigma pack.
3. Only then Phase 2 AI assist — packaging follows usage, not hype.
