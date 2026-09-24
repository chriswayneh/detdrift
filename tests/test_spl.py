"""Tests for optional SPL dialect field extraction (Phase 4)."""

from pathlib import Path

from detdrift.dialects import (
    detect_dialect,
    extract_fields_from_file,
    normalize_dialect,
    rule_globs_for_dialect,
)
from detdrift.dialects.spl import extract_fields_from_spl
from detdrift.diff import diff_rules, discover_rules

ROOT = Path(__file__).resolve().parents[1]
SPL_RULES = ROOT / "examples" / "spl" / "rules"
SPL_BEFORE = ROOT / "fixtures" / "spl" / "before"
SPL_AFTER = ROOT / "fixtures" / "spl" / "after"
SIGMA_RULES = ROOT / "rules"
BEFORE = ROOT / "fixtures" / "before"
AFTER = ROOT / "fixtures" / "after"


def test_normalize_and_detect_spl():
    assert normalize_dialect("SPL") == "spl"
    assert normalize_dialect("auto") == "auto"
    assert detect_dialect("x.spl") == "spl"
    assert detect_dialect("x.kql") == "kql"
    assert detect_dialect("x.yml") == "sigma"


def test_rule_globs_include_spl():
    assert rule_globs_for_dialect("spl") == ("**/*.spl",)
    globs = rule_globs_for_dialect("auto")
    assert "**/*.spl" in globs
    assert "**/*.kql" in globs


def test_spl_field_eq_and_table():
    text = """
    index=main sourcetype=WinEventLog
    | search Image="*whoami.exe*" ProcessCommandLine="*whoami*"
    | table _time, Image, ProcessCommandLine, AccountName
    """
    fields = extract_fields_from_spl(text)
    assert "Image" in fields
    assert "ProcessCommandLine" in fields
    assert "AccountName" in fields
    assert "_time" in fields
    assert "index" in fields
    assert "sourcetype" in fields


def test_spl_stats_by():
    text = "events | stats count by AccountName, DeviceName"
    assert extract_fields_from_spl(text) == {"AccountName", "DeviceName"}


def test_spl_rex_field():
    text = r'| rex field=ProcessCommandLine "whoami\s+(?<args>.*)"'
    fields = extract_fields_from_spl(text)
    assert "ProcessCommandLine" in fields
    # keyword "field" must not appear
    assert "field" not in fields


def test_spl_sample_file():
    fields = extract_fields_from_file(
        SPL_RULES / "whoami_process.spl", dialect="spl"
    )
    assert "Image" in fields
    assert "ProcessCommandLine" in fields
    assert "AccountName" in fields


def test_fields_auto_detect_spl_extension():
    fields = extract_fields_from_file(
        SPL_RULES / "whoami_process.spl", dialect="auto"
    )
    assert "ProcessCommandLine" in fields


def test_discover_spl_only():
    found = discover_rules(SPL_RULES, dialect="spl")
    assert len(found) == 1
    assert found[0].suffix == ".spl"
    assert discover_rules(SPL_RULES, dialect="sigma") == []
    assert discover_rules(SPL_RULES, dialect="kql") == []


def test_diff_spl_processcommandline_rename():
    report = diff_rules(SPL_BEFORE, SPL_AFTER, SPL_RULES, dialect="spl")
    assert report.has_impacts
    assert "ProcessCommandLine" in report.removed_fields
    whoami = report.impacted[0]
    assert "ProcessCommandLine" in whoami.missing_fields
    assert whoami.status == "IMPACTED"


def test_diff_sigma_default_ignores_spl_tree():
    report = diff_rules(BEFORE, AFTER, SIGMA_RULES, dialect="sigma")
    assert report.rules_scanned >= 1
    assert all(i.rule.endswith((".yml", ".yaml")) for i in report.impacts)


def test_cli_fields_and_diff_spl():
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()
    fields = runner.invoke(
        app, ["fields", str(SPL_RULES / "whoami_process.spl"), "--dialect", "auto"]
    )
    assert fields.exit_code == 0, fields.output
    assert "ProcessCommandLine" in fields.output

    ok = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(SPL_BEFORE),
            "--after",
            str(SPL_BEFORE),
            "--rules",
            str(SPL_RULES),
            "--dialect",
            "spl",
        ],
    )
    assert ok.exit_code == 0, ok.output

    bad = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(SPL_BEFORE),
            "--after",
            str(SPL_AFTER),
            "--rules",
            str(SPL_RULES),
            "--dialect",
            "spl",
        ],
    )
    assert bad.exit_code == 1, bad.output
    assert "ProcessCommandLine" in bad.output
    assert "IMPACTED" in bad.output
