# Sample importers

detdrift reads local files only. There is no live SIEM connector.

## Accepted sample shapes

`--before` and `--after` may be a file or a directory of files matching
`*.jsonl`, `*.ndjson`, or `*.json`.

| Shape | How it is read |
|-------|----------------|
| NDJSON / JSONL | One JSON object per line (existing default). |
| Flat JSON object | Object keys are field names. Values are ignored except nested dicts (one level). |
| `{"fields": ["a", "b"]}` | Uses the `fields` string list as the schema. |
| JSON array of objects | Union of field paths across array elements. |

Sysmon-style flat NDJSON packs already work via the NDJSON path: put one event
object per line under `fixtures/before` or `fixtures/after`.

## Example: flat schema dump

If your pipeline exports a field map instead of events:

```json
{
  "Image": true,
  "cmd": true,
  "User": true
}
```

```bash
detdrift diff --before fixtures/before --after path/to/after_fields.json --rules rules
```

## Not provided (on purpose)

- Live pulls from a SIEM, lake, or cloud API
- Auto-discovery of customer credentials
- Full CloudTrail/OCSF normalization beyond flat keys you already exported

Phase 3 stays file-based so the tool stays offline by default.
