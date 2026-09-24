"""Tests for schema→rule blast-radius diff."""

from pathlib import Path

import pytest

from detdrift.diff import diff_rules

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules"
BEFORE = ROOT / "fixtures" / "before"
AFTER = ROOT / "fixtures" / "after"


def test_identical_schemas_no_impact():
    report = diff_rules(BEFORE, BEFORE, RULES)
    assert not report.has_impacts
    assert report.impacted == []
    assert any(i.status == "SAFE" for i in report.impacts)


def test_commandline_rename_impacts_whoami():
    report = diff_rules(BEFORE, AFTER, RULES)
    assert report.has_impacts
    assert "CommandLine" in report.removed_fields

    impacted = report.impacted
    assert len(impacted) >= 1
    whoami = next(i for i in impacted if "whoami" in i.rule.lower() or "whoami" in i.title.lower())
    assert "CommandLine" in whoami.missing_fields
    assert whoami.status == "IMPACTED"


def test_cli_exit_codes(tmp_path):
    """Exercise CLI exit codes via Typer's CliRunner."""
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()

    ok = runner.invoke(
        app,
        ["diff", "--before", str(BEFORE), "--after", str(BEFORE), "--rules", str(RULES)],
    )
    assert ok.exit_code == 0, ok.output
    assert "PASS" in ok.output or "SAFE" in ok.output

    bad = runner.invoke(
        app,
        ["diff", "--before", str(BEFORE), "--after", str(AFTER), "--rules", str(RULES)],
    )
    assert bad.exit_code == 1, bad.output
    assert "CommandLine" in bad.output
    assert "IMPACTED" in bad.output


def test_fields_command():
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["fields", str(RULES / "proc_whoami.yml")])
    assert result.exit_code == 0
    assert "CommandLine" in result.output
    assert "Image" in result.output
    # modifiers stripped
    assert "|contains" not in result.output


def test_json_report():
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(BEFORE),
            "--after",
            str(AFTER),
            "--rules",
            str(RULES),
            "--json",
        ],
    )
    assert result.exit_code == 1
    import json

    data = json.loads(result.output)
    assert data["impacted_count"] >= 1
    assert "CommandLine" in data["removed_fields"]
