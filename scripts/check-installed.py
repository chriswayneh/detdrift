"""Exercise the built wheel, without editable-install or checkout imports."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import venv


def main() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist"
    wheels = list(dist.glob("detdrift-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected one detdrift wheel in {dist}, found {len(wheels)}")

    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONIOENCODING"] = "utf-8"
    env["NO_COLOR"] = "1"

    # Spaces in paths also exercise Windows console-script handling.
    with tempfile.TemporaryDirectory(prefix="detdrift installed ") as directory:
        root = Path(directory).resolve()
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        bin_dir = environment / ("Scripts" if os.name == "nt" else "bin")
        python = bin_dir / ("python.exe" if os.name == "nt" else "python")
        cli = bin_dir / ("detdrift.exe" if os.name == "nt" else "detdrift")

        def run(*args: str | Path, expected: int = 0, cwd: Path = root) -> str:
            result = subprocess.run(
                [str(arg) for arg in args], cwd=cwd, env=env,
                capture_output=True, text=True, encoding="utf-8", timeout=180,
            )
            if result.returncode != expected:
                raise AssertionError(
                    f"{args}: expected exit {expected}, got {result.returncode}\n"
                    f"{result.stdout}\n{result.stderr}"
                )
            return result.stdout

        run(python, "-m", "pip", "install", "--quiet", wheels[0])
        metadata = json.loads(run(
            python, "-I", "-c",
            "import json, detdrift; "
            "from importlib.metadata import version; "
            "print(json.dumps({'path': detdrift.__file__, 'version': version('detdrift')}))",
        ))
        assert Path(metadata["path"]).resolve().is_relative_to(environment), metadata
        expected_version = f"detdrift {metadata['version']}"
        assert run(cli, "--version").strip() == expected_version
        assert run(python, "-m", "detdrift", "--version").strip() == expected_version

        run(cli, "init", "demo")
        demo = root / "demo"
        for relative in (
            "rules/proc_whoami.yml",
            "fixtures/before/process.jsonl",
            "fixtures/after/process.jsonl",
        ):
            assert (demo / relative).is_file(), relative

        def diff(after: str, expected: int) -> str:
            return run(
                cli, "diff", "--before", "fixtures/before", "--after", after,
                "--rules", "rules", "--json", expected=expected, cwd=demo,
            )

        unchanged = json.loads(diff("fixtures/before", 0))
        assert unchanged["removed_fields"] == [], unchanged
        assert unchanged["rules_scanned"] == unchanged["safe_count"] == 1, unchanged
        assert unchanged["impacted_count"] == 0, unchanged
        drift = json.loads(diff("fixtures/after", 1))
        assert drift["schema_version"] == 1, drift
        assert drift["removed_fields"] == ["CommandLine"], drift
        assert drift["rules_scanned"] == drift["impacted_count"] == 1, drift
        assert drift["safe_count"] == 0, drift
        assert drift["impacts"][0]["missing_fields"] == ["CommandLine"], drift
        diff("missing-sample", 2)

    print("Installed-package check passed: entry points, init, JSON, exit codes 0/1/2.")


if __name__ == "__main__":
    main()
