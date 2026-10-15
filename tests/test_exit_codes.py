"""Inputs that make the result untrustworthy must exit 2, not 0."""
import json

from typer.testing import CliRunner

from detdrift.cli import app

runner = CliRunner()
RULE = """title: t
level: high
logsource: {product: windows}
detection:
  selection:
    Image: x
  condition: selection
"""


def _setup(tmp_path, before=None, rule=RULE):
    (tmp_path / "rules").mkdir()
    if rule is not None:
        (tmp_path / "rules" / "a.yml").write_text(rule)
    (tmp_path / "b.json").write_text(json.dumps(before if before is not None else {"Image": 1, "User": 1}))
    (tmp_path / "a.json").write_text(json.dumps({"User": 1}))
    return ["diff", "--before", str(tmp_path / "b.json"), "--after", str(tmp_path / "a.json"),
            "--rules", str(tmp_path / "rules")]


def test_unknown_fail_on_severity_exits_2(tmp_path):
    r = runner.invoke(app, _setup(tmp_path) + ["--fail-on-severity", "hgih"])
    assert r.exit_code == 2, r.output


def test_known_fail_on_severity_still_works(tmp_path):
    r = runner.invoke(app, _setup(tmp_path) + ["--fail-on-severity", "HIGH"])
    assert r.exit_code == 1, r.output


def test_empty_before_exits_2(tmp_path):
    r = runner.invoke(app, _setup(tmp_path, before={}))
    assert r.exit_code == 2, r.output


def test_no_rules_exits_2(tmp_path):
    r = runner.invoke(app, _setup(tmp_path, rule=None))
    assert r.exit_code == 2, r.output


def test_malformed_yaml_exits_2(tmp_path):
    args = _setup(tmp_path, rule="x: [\n")
    r = runner.invoke(app, args)
    assert r.exit_code == 2, r.output
    r = runner.invoke(app, ["fields", str(tmp_path / "rules" / "a.yml")])
    assert r.exit_code == 2, r.output
