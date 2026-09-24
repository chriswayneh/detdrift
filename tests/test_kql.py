"""Tests for optional KQL dialect field extraction (Phase 4)."""

from pathlib import Path

from detdrift.dialects import (
    detect_dialect,
    extract_fields_from_file,
    normalize_dialect,
    rule_globs_for_dialect,
)
from detdrift.dialects.kql import extract_fields_from_kql
from detdrift.diff import diff_rules, discover_rules

ROOT = Path(__file__).resolve().parents[1]
KQL_RULES = ROOT / "examples" / "kql" / "rules"
KQL_BEFORE = ROOT / "fixtures" / "kql" / "before"
KQL_AFTER = ROOT / "fixtures" / "kql" / "after"
SIGMA_RULES = ROOT / "rules"
BEFORE = ROOT / "fixtures" / "before"
AFTER = ROOT / "fixtures" / "after"


def test_normalize_and_detect():
    assert normalize_dialect(None) == "sigma"
    assert normalize_dialect("KQL") == "kql"
    assert normalize_dialect("auto") == "auto"
    assert detect_dialect("x.kql") == "kql"
    assert detect_dialect("x.yml") == "sigma"
    assert detect_dialect("x.yaml") == "sigma"


def test_rule_globs():
    assert rule_globs_for_dialect("sigma") == ("**/*.yml", "**/*.yaml")
    assert rule_globs_for_dialect("kql") == ("**/*.kql",)
    assert "**/*.kql" in rule_globs_for_dialect("auto")


def test_kql_where_and_project():
    text = """
    DeviceProcessEvents
    | where FileName =~ "whoami.exe" and ProcessCommandLine contains "whoami"
    | project Timestamp, DeviceName, FileName, ProcessCommandLine
    | sort by Timestamp
    """
    fields = extract_fields_from_kql(text)
    assert fields == {
        "FileName",
        "ProcessCommandLine",
        "Timestamp",
        "DeviceName",
    }


def test_kql_summarize_by():
    text = "events | summarize count() by AccountName, DeviceName"
    assert extract_fields_from_kql(text) == {"AccountName", "DeviceName"}


def test_kql_project_alias_rhs():
    text = "T | project Renamed = ProcessCommandLine, FileName"
    fields = extract_fields_from_kql(text)
    assert "ProcessCommandLine" in fields
    assert "FileName" in fields
    # Alias is not a schema field ref from the operator alone
    assert "Renamed" not in fields


def test_kql_sample_file():
    fields = extract_fields_from_file(
        KQL_RULES / "whoami_process.kql", dialect="kql"
    )
    assert "FileName" in fields
    assert "ProcessCommandLine" in fields
    assert "AccountName" in fields


def test_fields_auto_detect_extension():
    fields = extract_fields_from_file(KQL_RULES / "whoami_process.kql", dialect="auto")
    assert "ProcessCommandLine" in fields


def test_discover_kql_only():
    found = discover_rules(KQL_RULES, dialect="kql")
    assert len(found) == 1
    assert found[0].suffix == ".kql"
    # sigma dialect should not pick up .kql
    assert discover_rules(KQL_RULES, dialect="sigma") == []


def test_diff_kql_processcommandline_rename():
    report = diff_rules(KQL_BEFORE, KQL_AFTER, KQL_RULES, dialect="kql")
    assert report.has_impacts
    assert "ProcessCommandLine" in report.removed_fields
    whoami = report.impacted[0]
    assert "ProcessCommandLine" in whoami.missing_fields
    assert whoami.status == "IMPACTED"


def test_diff_sigma_default_ignores_kql_tree():
    """Default sigma dialect still only scans YAML under rules/."""
    report = diff_rules(BEFORE, AFTER, SIGMA_RULES, dialect="sigma")
    assert report.rules_scanned >= 1
    assert all(i.rule.endswith((".yml", ".yaml")) for i in report.impacts)


def test_cli_fields_and_diff_kql():
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()
    fields = runner.invoke(
        app, ["fields", str(KQL_RULES / "whoami_process.kql"), "--dialect", "auto"]
    )
    assert fields.exit_code == 0, fields.output
    assert "ProcessCommandLine" in fields.output

    ok = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(KQL_BEFORE),
            "--after",
            str(KQL_BEFORE),
            "--rules",
            str(KQL_RULES),
            "--dialect",
            "kql",
        ],
    )
    assert ok.exit_code == 0, ok.output

    bad = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(KQL_BEFORE),
            "--after",
            str(KQL_AFTER),
            "--rules",
            str(KQL_RULES),
            "--dialect",
            "kql",
        ],
    )
    assert bad.exit_code == 1, bad.output
    assert "ProcessCommandLine" in bad.output
    assert "IMPACTED" in bad.output
