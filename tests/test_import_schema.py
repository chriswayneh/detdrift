"""Tests for flat JSON schema document import."""

import json
from pathlib import Path

from detdrift.diff import diff_rules
from detdrift.schema import load_schema_sample, schema_from_path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules"
BEFORE = ROOT / "fixtures" / "before"
FLAT = ROOT / "fixtures" / "schema-flat"


def test_flat_json_object_keys_are_fields(tmp_path):
    p = tmp_path / "schema.json"
    p.write_text(json.dumps({"Image": 1, "CommandLine": "x", "User": None}), encoding="utf-8")
    sample = load_schema_sample(p)
    assert sample.fields == {"Image", "CommandLine", "User"}
    assert sample.event_count == 1


def test_fields_list_document(tmp_path):
    p = tmp_path / "fields.json"
    p.write_text(json.dumps({"fields": ["Image", "cmd", "User"], "meta": "ignored"}), encoding="utf-8")
    # When "fields" is a list of strings, use that list (meta key ignored)
    sample = load_schema_sample(p)
    assert sample.fields == {"Image", "cmd", "User"}


def test_json_array_of_events(tmp_path):
    p = tmp_path / "events.json"
    p.write_text(
        json.dumps([
            {"Image": "a.exe", "CommandLine": "a"},
            {"Image": "b.exe", "User": "u"},
        ]),
        encoding="utf-8",
    )
    sample = load_schema_sample(p)
    assert sample.fields == {"Image", "CommandLine", "User"}
    assert sample.event_count == 2


def test_ndjson_still_works():
    schema = schema_from_path(BEFORE)
    assert "CommandLine" in schema


def test_diff_with_flat_after_schema():
    report = diff_rules(BEFORE, FLAT / "after_fields.json", RULES)
    assert "CommandLine" in report.removed_fields
    assert report.has_impacts


def test_cli_flat_json_after():
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
            str(FLAT / "fields_list.json"),
            "--rules",
            str(RULES),
        ],
    )
    assert result.exit_code == 1
    assert "CommandLine" in result.output
