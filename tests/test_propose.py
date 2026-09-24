"""Tests for propose-patch (Phase 2 Assist)."""

from pathlib import Path

from detdrift.propose import (
    format_notes,
    format_patch,
    infer_renames,
    propose_from_paths,
)

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "rules"
BEFORE = ROOT / "fixtures" / "before"
AFTER = ROOT / "fixtures" / "after"


def test_infer_commandline_to_cmd():
    before = {"Image", "CommandLine", "User"}
    after = {"Image", "cmd", "User"}
    mapping = infer_renames(before, after)
    assert mapping == {"CommandLine": "cmd"}


def test_infer_unclear_when_many_added():
    before = {"CommandLine"}
    after = {"foo", "bar", "baz"}
    mapping = infer_renames(before, after)
    assert mapping["CommandLine"] is None


def test_infer_no_removed():
    assert infer_renames({"a", "b"}, {"a", "b"}) == {}


def test_propose_notes_fixture():
    result = propose_from_paths(BEFORE, AFTER, RULES)
    assert result.confident_renames["CommandLine"] == "cmd"
    assert len(result.report.impacted) >= 1
    text = format_notes(result)
    assert "CommandLine  ->  cmd" in text
    assert "proc_whoami.yml" in text
    assert "does not edit rule files" in text
    assert "does not auto-commit" in text


def test_propose_patch_fixture():
    result = propose_from_paths(BEFORE, AFTER, RULES)
    text = format_patch(result, RULES)
    assert "CommandLine->cmd" in text.replace(" ", "")
    assert "--- a/proc_whoami.yml" in text or "a/proc_whoami.yml" in text
    assert "-    CommandLine|contains" in text or "-    CommandLine|" in text
    assert "+    cmd|contains" in text or "+    cmd|" in text
    # Original rule file untouched
    original = (RULES / "proc_whoami.yml").read_text(encoding="utf-8")
    assert "CommandLine|contains" in original
    assert "cmd|contains" not in original


def test_propose_identical_schemas_notes():
    result = propose_from_paths(BEFORE, BEFORE, RULES)
    text = format_notes(result)
    assert "Nothing to propose" in text
    assert result.removed_fields == []


def test_cli_propose_patch_notes():
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "propose-patch",
            "--before",
            str(BEFORE),
            "--after",
            str(AFTER),
            "--rules",
            str(RULES),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "CommandLine  ->  cmd" in result.output
    assert "mapping notes" in result.output


def test_cli_propose_patch_format_patch():
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "propose-patch",
            "--before",
            str(BEFORE),
            "--after",
            str(AFTER),
            "--rules",
            str(RULES),
            "--format",
            "patch",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "cmd|contains" in result.output
    assert "No files were modified" in result.output


def test_cli_propose_patch_output_file(tmp_path):
    from typer.testing import CliRunner

    from detdrift.cli import app

    out = tmp_path / "notes.txt"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "propose-patch",
            "-b",
            str(BEFORE),
            "-a",
            str(AFTER),
            "-r",
            str(RULES),
            "-o",
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert "CommandLine  ->  cmd" in body
    # stdout still printed
    assert "CommandLine  ->  cmd" in result.output


def test_cli_propose_does_not_modify_rules():
    from typer.testing import CliRunner

    from detdrift.cli import app

    before_text = (RULES / "proc_whoami.yml").read_text(encoding="utf-8")
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "propose-patch",
            "-b",
            str(BEFORE),
            "-a",
            str(AFTER),
            "-r",
            str(RULES),
            "--format",
            "patch",
        ],
    )
    after_text = (RULES / "proc_whoami.yml").read_text(encoding="utf-8")
    assert before_text == after_text


def test_replace_keeps_modifiers():
    from detdrift.propose import _replace_field_keys_in_text

    src = "    CommandLine|contains|all:\n      - whoami\n"
    out = _replace_field_keys_in_text(src, {"CommandLine": "cmd"})
    assert out == "    cmd|contains|all:\n      - whoami\n"
