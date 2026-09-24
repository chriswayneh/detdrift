"""Tests for SARIF output from detdrift diff."""

import json
from pathlib import Path

from detdrift.diff import diff_rules
from detdrift.sarif import format_sarif, report_to_sarif

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules"
BEFORE = ROOT / "fixtures" / "before"
AFTER = ROOT / "fixtures" / "after"


def test_sarif_structure_for_demo_drift():
    report = diff_rules(BEFORE, AFTER, RULES)
    doc = report_to_sarif(report)
    assert doc["version"] == "2.1.0"
    assert "$schema" in doc
    assert len(doc["runs"]) == 1
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "detdrift"
    rule_ids = {r["id"] for r in run["tool"]["driver"]["rules"]}
    assert "detdrift-field-missing" in rule_ids
    results = run["results"]
    assert any(r["ruleId"] == "detdrift-field-missing" for r in results)
    hit = next(r for r in results if r["ruleId"] == "detdrift-field-missing")
    assert "CommandLine" in hit["message"]["text"]
    assert hit["locations"][0]["physicalLocation"]["artifactLocation"]["uri"]


def test_sarif_empty_when_no_impact():
    report = diff_rules(BEFORE, BEFORE, RULES)
    doc = report_to_sarif(report)
    assert doc["runs"][0]["results"] == []


def test_cli_format_sarif():
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
            "--format",
            "sarif",
        ],
    )
    assert result.exit_code == 1, result.output
    data = json.loads(result.stdout)
    assert data["version"] == "2.1.0"
    assert data["runs"][0]["results"]


def test_format_sarif_roundtrip_json():
    report = diff_rules(BEFORE, AFTER, RULES)
    text = format_sarif(report)
    data = json.loads(text)
    assert data["runs"][0]["tool"]["driver"]["name"] == "detdrift"
