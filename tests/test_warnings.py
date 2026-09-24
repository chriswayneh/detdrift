"""Tests for empty / incomplete after-sample warnings."""

from pathlib import Path

from detdrift.diff import diff_rules
from detdrift.schema import SchemaSample, load_schema_sample, sample_warnings

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules"
BEFORE = ROOT / "fixtures" / "before"


def test_load_schema_sample_counts_events():
    sample = load_schema_sample(BEFORE)
    assert sample.event_count == 3
    assert sample.file_count == 1
    assert "CommandLine" in sample.fields


def test_sample_warnings_empty_after():
    before = SchemaSample(fields={"a", "b", "c"}, event_count=3, file_count=1, path="before")
    after = SchemaSample(fields=set(), event_count=0, file_count=1, path="after.jsonl")
    msgs = sample_warnings(before, after)
    assert len(msgs) == 1
    assert "empty" in msgs[0].lower()
    assert "nothing removed" in msgs[0].lower()


def test_sample_warnings_incomplete_ratio():
    before = SchemaSample(
        fields={f"f{i}" for i in range(10)},
        event_count=10,
        file_count=1,
        path="before",
    )
    after = SchemaSample(fields={"f0"}, event_count=1, file_count=1, path="after")
    msgs = sample_warnings(before, after)
    assert any("incomplete" in m.lower() for m in msgs)


def test_sample_warnings_normal_rename_no_warn():
    before = SchemaSample(
        fields={"Image", "CommandLine", "User"},
        event_count=3,
        file_count=1,
        path="before",
    )
    after = SchemaSample(
        fields={"Image", "cmd", "User"},
        event_count=3,
        file_count=1,
        path="after",
    )
    assert sample_warnings(before, after) == []


def test_diff_empty_after_file_warns(tmp_path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    report = diff_rules(BEFORE, empty, RULES)
    assert report.warnings
    assert report.after_event_count == 0
    assert any("empty" in w.lower() for w in report.warnings)
    # Empty after => all before fields removed => whoami IMPACTED
    assert report.has_impacts
    data = report.to_dict()
    assert "warnings" in data
    assert data["after_event_count"] == 0


def test_cli_empty_after_stderr_warning(tmp_path):
    from typer.testing import CliRunner

    from detdrift.cli import app

    empty = tmp_path / "empty.jsonl"
    empty.write_text("\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["diff", "--before", str(BEFORE), "--after", str(empty), "--rules", str(RULES)],
    )
    assert result.exit_code == 1
    combined = (result.stdout or "") + (result.stderr or "")
    assert "WARNINGS" in combined or "warning:" in combined.lower()
    assert "empty" in combined.lower()
