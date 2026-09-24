"""Tests for schema→rule blast-radius diff."""

from pathlib import Path

from detdrift.diff import DEFAULT_IGNORE_DIRS, diff_rules, discover_rules

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
    assert whoami.level == "low"


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
    assert data["schema_version"] == 1
    assert data["impacted_count"] >= 1
    assert "CommandLine" in data["removed_fields"]
    impact = data["impacts"][0]
    assert "level" in impact
    assert "tags" in impact


def test_discover_rules_recursive(tmp_path):
    (tmp_path / "windows").mkdir()
    (tmp_path / "windows" / "nested").mkdir()
    (tmp_path / "windows" / "a.yml").write_text("title: a\ndetection:\n  selection:\n    Image: x\n  condition: selection\n")
    (tmp_path / "windows" / "nested" / "b.yaml").write_text("title: b\ndetection:\n  selection:\n    User: y\n  condition: selection\n")
    # ignored dirs
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "secret.yml").write_text("title: no\ndetection:\n  selection:\n    Image: z\n  condition: selection\n")
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "skip.yml").write_text("title: no\ndetection:\n  selection:\n    Image: z\n  condition: selection\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "fixture.yml").write_text("title: no\ndetection:\n  selection:\n    Image: z\n  condition: selection\n")

    found = discover_rules(tmp_path)
    names = sorted(p.name for p in found)
    assert names == ["a.yml", "b.yaml"]
    assert ".git" in DEFAULT_IGNORE_DIRS
    assert "vendor" in DEFAULT_IGNORE_DIRS


def test_discover_rules_ignore_glob(tmp_path):
    (tmp_path / "keep.yml").write_text("title: k\ndetection:\n  selection:\n    Image: x\n  condition: selection\n")
    (tmp_path / "skip_test.yml").write_text("title: s\ndetection:\n  selection:\n    Image: x\n  condition: selection\n")
    found = discover_rules(tmp_path, ignore=["*_test.yml"])
    assert [p.name for p in found] == ["keep.yml"]


def test_fail_on_severity_filters_exit(tmp_path):
    """Whoami is level low; --fail-on-severity high should pass despite IMPACTED."""
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()

    # IMPACTED but low severity: filter high => exit 0
    filtered = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(BEFORE),
            "--after",
            str(AFTER),
            "--rules",
            str(RULES),
            "--fail-on-severity",
            "high,critical",
        ],
    )
    assert filtered.exit_code == 0, filtered.output
    assert "IMPACTED" in filtered.output
    assert "PASS" in filtered.output

    # Same without filter => exit 1
    unfiltered = runner.invoke(
        app,
        ["diff", "--before", str(BEFORE), "--after", str(AFTER), "--rules", str(RULES)],
    )
    assert unfiltered.exit_code == 1


def test_fail_on_severity_matches_high(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "high.yml").write_text(
        "title: High Rule\n"
        "level: high\n"
        "tags:\n  - attack.t1059\n"
        "detection:\n"
        "  selection:\n"
        "    CommandLine|contains: whoami\n"
        "  condition: selection\n"
    )
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
            str(rules_dir),
            "--fail-on-severity",
            "high",
        ],
    )
    assert result.exit_code == 1, result.output
    assert "Fail matches: 1" in result.output


def test_fail_on_tag(tmp_path):
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "tagged.yml").write_text(
        "title: Tagged\n"
        "level: low\n"
        "tags:\n  - attack.t1059.001\n  - execution\n"
        "detection:\n"
        "  selection:\n"
        "    CommandLine|contains: whoami\n"
        "  condition: selection\n"
    )
    from typer.testing import CliRunner

    from detdrift.cli import app

    runner = CliRunner()

    hit = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(BEFORE),
            "--after",
            str(AFTER),
            "--rules",
            str(rules_dir),
            "--fail-on-tag",
            "attack.t1059",
        ],
    )
    assert hit.exit_code == 1, hit.output

    miss = runner.invoke(
        app,
        [
            "diff",
            "--before",
            str(BEFORE),
            "--after",
            str(AFTER),
            "--rules",
            str(rules_dir),
            "--fail-on-tag",
            "attack.t9999",
        ],
    )
    assert miss.exit_code == 0, miss.output
