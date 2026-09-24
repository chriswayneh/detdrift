"""detdrift CLI: schema change vs Sigma field references."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import typer

from detdrift import __version__
from detdrift.diff import diff_rules, format_report_human
from detdrift.fields import extract_fields_from_file

app = typer.Typer(
    name="detdrift",
    help="Report which Sigma rules lose fields after a schema change.",
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
    json_out: bool = typer.Option(False, "--json", help="Emit machine-readable JSON report"),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Write report to file (in addition to stdout)"
    ),
) -> None:
    """Compare before/after schemas and report Sigma rules that would go silent."""
    try:
        report = diff_rules(before, after, rules)
    except FileNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(2) from exc

    if json_out:
        text = json.dumps(report.to_dict(), indent=2)
    else:
        text = format_report_human(report)

    typer.echo(text)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")

    raise typer.Exit(1 if report.has_impacts else 0)


@app.command("fields")
def fields_cmd(
    rule: Path = typer.Argument(..., help="Path to a Sigma YAML rule"),
) -> None:
    """List field references extracted from one rule (debug)."""
    try:
        fields = extract_fields_from_file(rule)
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
