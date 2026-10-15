"""Guard against GitHub Actions script injection in action.yml."""
from pathlib import Path

import yaml


def test_run_scripts_do_not_interpolate_expressions():
    action = yaml.safe_load((Path(__file__).parent.parent / "action.yml").read_text())
    for step in action["runs"]["steps"]:
        run = step.get("run")
        if run:
            assert "${{" not in run.replace("${{ github.action_path }}", ""), step.get("name")
