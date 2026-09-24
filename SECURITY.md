# Security

## Reporting a vulnerability

Email or open a private GitHub security advisory on
[chriswayneh/detdrift](https://github.com/chriswayneh/detdrift) if you find a
security issue. Please include steps to reproduce and the affected version.

Do not file a public issue for unfixed vulnerabilities.

## Scope

detdrift is an offline CLI. It:

- Reads NDJSON/JSONL samples and Sigma YAML from paths you pass in
- Parses YAML with `yaml.safe_load` (no code execution from rule files)
- Writes reports to stdout or a file you choose
- Does not call cloud APIs or require credentials in the core path

Treat rule packs and fixtures as untrusted input. Malicious YAML can still be
large or deeply nested and may stress the parser or your disk. Run it on files
you trust or have reviewed, especially in CI that checks out third-party rules.

## Out of scope

- Social engineering against GitHub accounts
- Issues that need a local privileged process outside this tool
- Requests to turn detdrift into an exploit or attack simulator (not on the
  roadmap)

## Supported versions

Security fixes land on the latest release line on `main`. Older 0.x tags may
not receive backports while the project is pre-1.0.
