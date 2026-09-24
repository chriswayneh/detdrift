"""detdrift CLI: schema change vs detection field references."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer

from detdrift import __version__
from detdrift.dialects import extract_fields_from_file, normalize_dialect
from detdrift.diff import diff_rules, format_report_human
from detdrift.propose import format_propose, propose_from_paths
from detdrift.sarif import format_sarif

app = typer.Typer(
    name="detdrift",
    help="Report which detection rules lose fields after a schema change (Sigma default; optional KQL/SPL).",
    no_args_is_help=True,
    add_completion=False,
)

# Bundled samples live next to the installed package's parents in editable mode,
# or we embed minimal copies for `init`. Prefer repo-relative paths when present.
_PKG_ROOT = Path(__file__).resolve().parents[2]  # .../src/detdrift → repo root in editable


def _repo_root() -> Path:
    """Best-effort path to the project root (editable install or cwd)."""
    candidate = _PKG_ROOT
    if (candidate / "rules").is_dir() and (candidate / "fixtures").is_dir():
        return candidate
    cwd = Path.cwd()
    if (cwd / "rules").is_dir() and (cwd / "fixtures").is_dir():
        return cwd
    return candidate


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"detdrift {__version__}")
        raise typer.Exit(0)


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Compare before/after schemas to Sigma rules."""


@app.command("diff")
def diff_cmd(
    before: Path = typer.Option(..., "--before", "-b", help="Before NDJSON file or directory"),
    after: Path = typer.Option(..., "--after", "-a", help="After NDJSON file or directory"),
    rules: Path = typer.Option(..., "--rules", "-r", help="Directory of Sigma YAML rules"),
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON report (alias for --format json)"),
    format_opt: Optional[str] = typer.Option(
        None,
        "--format",
        help="Report format: human (default), json, or sarif (for PR annotations)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write report to file (in addition to stdout)"
    ),
    fail_on_severity: Optional[str] = typer.Option(
        None,
        "--fail-on-severity",
        help=(
            "Only exit 1 when an IMPACTED rule has this severity or higher. "
            "Comma-separated Sigma levels, e.g. high,critical. "
            "Without this flag, any IMPACTED rule fails the run."
        ),
    ),
    fail_on_tag: Optional[str] = typer.Option(
        None,
        "--fail-on-tag",
        help=(
            "Only exit 1 when an IMPACTED rule has a matching tag. "
            "Comma-separated substrings matched case-insensitively against rule tags, "
            "e.g. attack.t1059,persistence. "
            "Can combine with --fail-on-severity (both must match)."
        ),
    ),
    ignore: Optional[list[str]] = typer.Option(
        None,
        "--ignore",
        help=(
            "Extra fnmatch glob to skip under --rules (repeatable). "
            "Default ignored dir names: .git, .github, vendor, tests, and similar. "
            "Example: --ignore '*_test.yml' --ignore 'fixtures/**'"
        ),
    ),
    dialect: str = typer.Option(
        "sigma",
        "--dialect",
        "-d",
        help=(
            "Rule dialect: sigma (default, *.yml/*.yaml), kql (*.kql), "
            "spl (*.spl), or auto (pick per file by extension)."
        ),
    ),
) -> None:
    """Compare before/after schemas and report rules that would go silent."""
    try:
        dialect_norm = normalize_dialect(dialect)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    try:
        report = diff_rules(before, after, rules, ignore=ignore, dialect=dialect_norm)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    # Always surface sample warnings on stderr (also in human/JSON report body).
    for msg in report.warnings:
        typer.secho(f"warning: {msg}", fg=typer.colors.YELLOW, err=True)

    sev_filters = _split_csv(fail_on_severity)
    tag_filters = _split_csv(fail_on_tag)
    filters_active = bool(sev_filters or tag_filters)
    fail_matches = report.matching_impacts(
        fail_on_severity=sev_filters or None,
        fail_on_tags=tag_filters or None,
    )

    fmt = (format_opt or "").strip().lower()
    if json_out and not fmt:
        fmt = "json"
    if not fmt:
        fmt = "human"
    if fmt not in {"human", "json", "sarif"}:
        typer.secho(
            f"Unknown --format {format_opt!r}; use human, json, or sarif",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    if fmt == "json":
        payload = report.to_dict()
        if filters_active:
            payload["fail_on"] = {
                "severity": sev_filters,
                "tags": tag_filters,
                "matched_count": len(fail_matches),
                "matched_rules": [m.rule for m in fail_matches],
            }
        text = json.dumps(payload, indent=2)
    elif fmt == "sarif":
        text = format_sarif(report)
    else:
        text = format_report_human(
            report,
            fail_matches=fail_matches if filters_active else None,
            fail_on_severity=sev_filters if filters_active else None,
            fail_on_tags=tag_filters if filters_active else None,
        )

    typer.echo(text)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")

    if filters_active:
        raise typer.Exit(1 if fail_matches else 0)
    raise typer.Exit(1 if report.has_impacts else 0)


@app.command("fields")
def fields_cmd(
    rule: Path = typer.Argument(..., help="Path to a rule file (Sigma YAML, .kql, or .spl)"),
    dialect: str = typer.Option(
        "auto",
        "--dialect",
        "-d",
        help=(
            "Rule dialect: auto (default; by extension), sigma, kql, or spl. "
            ".yml/.yaml -> sigma, .kql -> kql, .spl -> spl."
        ),
    ),
) -> None:
    """List field references extracted from one rule (debug)."""
    try:
        dialect_norm = normalize_dialect(dialect)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    try:
        fields = extract_fields_from_file(rule, dialect=dialect_norm)
    except (OSError, ValueError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    if not fields:
        typer.echo("(no field references found)")
        raise typer.Exit(0)

    for name in sorted(fields):
        typer.echo(name)


_SAMPLE_RULE = '''title: Whoami Execution
id: detdrift-demo-whoami
status: experimental
description: Detects execution of whoami via process command line.
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    Image|endswith:
      - '\\whoami.exe'
      - '/whoami'
    CommandLine|contains: 'whoami'
  condition: selection
level: low
falsepositives:
  - Legitimate admin troubleshooting
'''

_SAMPLE_BEFORE = '''{"Image": "C:\\\\Windows\\\\System32\\\\whoami.exe", "CommandLine": "whoami /all", "User": "CORP\\\\alice"}
{"Image": "C:\\\\Windows\\\\System32\\\\cmd.exe", "CommandLine": "cmd.exe /c whoami", "User": "CORP\\\\bob"}
{"Image": "C:\\\\Windows\\\\System32\\\\notepad.exe", "CommandLine": "notepad.exe", "User": "CORP\\\\alice"}
'''

_SAMPLE_AFTER = '''{"Image": "C:\\\\Windows\\\\System32\\\\whoami.exe", "cmd": "whoami /all", "User": "CORP\\\\alice"}
{"Image": "C:\\\\Windows\\\\System32\\\\cmd.exe", "cmd": "cmd.exe /c whoami", "User": "CORP\\\\bob"}
{"Image": "C:\\\\Windows\\\\System32\\\\notepad.exe", "cmd": "notepad.exe", "User": "CORP\\\\alice"}
'''


@app.command("propose-patch")
def propose_patch_cmd(
    before: Path = typer.Option(..., "--before", "-b", help="Before NDJSON file or directory"),
    after: Path = typer.Option(..., "--after", "-a", help="After NDJSON file or directory"),
    rules: Path = typer.Option(..., "--rules", "-r", help="Directory of Sigma YAML rules"),
    fmt: str = typer.Option(
        "notes",
        "--format",
        "-f",
        help="Output format: notes (default mapping notes) or patch (unified diff draft)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write draft to file (in addition to stdout)"
    ),
    ignore: Optional[list[str]] = typer.Option(
        None,
        "--ignore",
        help="Extra fnmatch glob to skip under --rules (repeatable).",
    ),
) -> None:
    """Draft mapping notes or a rule patch for IMPACTED fields (review only; no in-place edits)."""
    fmt_norm = (fmt or "notes").strip().lower()
    if fmt_norm not in {"notes", "patch"}:
        typer.secho(
            f"Unknown --format {fmt!r}; use notes or patch",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(2)

    try:
        result = propose_from_paths(before, after, rules, ignore=ignore)
        text = format_propose(result, rules, fmt_norm)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    out_text = text if text.endswith("\n") else text + "\n"
    typer.echo(out_text, nl=False)
    if output is not None:
        output.write_text(out_text, encoding="utf-8")

    raise typer.Exit(0)


@app.command("init")
def init_cmd(
    dest: Path = typer.Argument(
        Path("."),
        help="Directory to write sample rules + fixtures into",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing sample files"),
) -> None:
    """Write sample rules + before/after fixtures demonstrating a CommandLine rename."""
    dest = dest.resolve()
    rules_dir = dest / "rules"
    before_dir = dest / "fixtures" / "before"
    after_dir = dest / "fixtures" / "after"

    targets = {
        rules_dir / "proc_whoami.yml": _SAMPLE_RULE,
        before_dir / "process.jsonl": _SAMPLE_BEFORE,
        after_dir / "process.jsonl": _SAMPLE_AFTER,
    }

    # Prefer copying from packaged repo samples when available
    root = _repo_root()
    copy_map = {
        rules_dir / "proc_whoami.yml": root / "rules" / "proc_whoami.yml",
        before_dir / "process.jsonl": root / "fixtures" / "before" / "process.jsonl",
        after_dir / "process.jsonl": root / "fixtures" / "after" / "process.jsonl",
    }

    written: list[str] = []
    for target, embedded in targets.items():
        if target.exists() and not force:
            typer.secho(f"skip (exists): {target}", fg=typer.colors.YELLOW)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        src = copy_map.get(target)
        if src is not None and src.is_file():
            shutil.copy2(src, target)
        else:
            target.write_text(embedded, encoding="utf-8")
        written.append(str(target))
        typer.secho(f"wrote {target}", fg=typer.colors.GREEN)

    typer.echo("")
    typer.echo("Try the demo:")
    typer.echo(
        f"  detdrift diff --before {before_dir} --after {before_dir} --rules {rules_dir}"
    )
    typer.echo("  # expect exit 0 (identical schemas)")
    typer.echo(
        f"  detdrift diff --before {before_dir} --after {after_dir} --rules {rules_dir}"
    )
    typer.echo("  # expect exit 1: CommandLine gone, whoami rule IMPACTED")


if __name__ == "__main__":
    app()
