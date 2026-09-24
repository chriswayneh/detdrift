# JSON report schema

`detdrift diff --json` prints a versioned report. The top-level field
`schema_version` is an integer. Consumers should check it before relying on
new keys.

Current version: **1**

## Shape (schema_version 1)

```json
{
  "schema_version": 1,
  "before_fields": ["CommandLine", "Image", "User"],
  "after_fields": ["Image", "User", "cmd"],
  "removed_fields": ["CommandLine"],
  "rules_scanned": 1,
  "impacted_count": 1,
  "safe_count": 0,
  "impacts": [
    {
      "rule": "proc_whoami.yml",
      "title": "Whoami Execution",
      "status": "IMPACTED",
      "referenced_fields": ["CommandLine", "Image"],
      "missing_fields": ["CommandLine"],
      "never_in_before": [],
      "level": "low",
      "tags": []
    }
  ]
}
```

When `--fail-on-severity` and/or `--fail-on-tag` are set, an extra object is
included:

```json
{
  "fail_on": {
    "severity": ["high", "critical"],
    "tags": ["attack.t1059"],
    "matched_count": 0,
    "matched_rules": []
  }
}
```

## Field notes

| Key | Meaning |
|-----|---------|
| `schema_version` | Report contract version. Bump only on breaking JSON changes. |
| `before_fields` / `after_fields` | Sorted field paths seen in each sample set. |
| `removed_fields` | Present in before, absent in after. |
| `rules_scanned` | Number of YAML rule files discovered. |
| `impacted_count` / `safe_count` | Counts by `status`. UNKNOWN is neither. |
| `impacts[].status` | `IMPACTED`, `SAFE`, or `UNKNOWN`. |
| `impacts[].missing_fields` | Referenced fields in before and missing from after. |
| `impacts[].never_in_before` | Referenced fields that were not in the before sample (informational). |
| `impacts[].level` | Sigma `level` (or `severity`), lowercased, or empty. |
| `impacts[].tags` | Sigma `tags` list as strings. |
| `fail_on` | Only present when fail-on CLI filters were used. |
| `before_event_count` / `after_event_count` | Parsed event lines in each sample set (optional additive keys). |
| `warnings` | Only present when the after sample looks empty or incomplete. |

## Compatibility

- New optional keys may appear in a minor release without bumping
  `schema_version`.
- Removing or renaming a key, or changing value types, bumps
  `schema_version`.
