#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "evals" / "run_all.py"
ACTOR = ROOT / "tests" / "fixtures" / "fake_eval_actor.py"
VERIFIER = ROOT / "tests" / "fixtures" / "fake_eval_verifier.py"
REGISTERED = sorted(path.stem for path in (ROOT / "evals" / "scenarios").glob("*.yaml"))


def run_sweep(output: Path, **extra_env: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(extra_env)
    return subprocess.run(
        [
            sys.executable,
            str(SWEEP),
            "--actor-command", f"{sys.executable} {ACTOR}",
            "--verifier-command", f"{sys.executable} {VERIFIER}",
            "--timeout", "30",
            "--output-dir", str(output),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="eval-sweep-test-") as temp:
        root = Path(temp)
        success_dir = root / "success"
        success = run_sweep(success_dir)
        if success.returncode != 0:
            raise AssertionError(f"all-pass sweep failed: {success.stderr}")
        aggregate = json.loads((success_dir / "aggregate.json").read_text(encoding="utf-8"))
        if aggregate["status"] != "VERIFIED PASS":
            raise AssertionError("all-pass sweep did not produce VERIFIED PASS")
        if aggregate["registered_scenarios"] != REGISTERED:
            raise AssertionError("sweep did not enumerate the exact registered scenario set")
        if aggregate["scenario_count"] != len(REGISTERED):
            raise AssertionError("aggregate scenario count is wrong")
        if not all(aggregate["aggregate_checks"].values()):
            raise AssertionError("an aggregate pass check was false")
        for scenario in REGISTERED:
            scenario_dir = success_dir / scenario
            for relative in (
                "result.json",
                "runner.stdout.log",
                "runner.stderr.log",
                "raw/actor-adapter.stdout.json",
                "raw/actor-adapter.process.json",
                "raw/verifier-adapter.stdout.json",
                "raw/verifier-adapter.process.json",
            ):
                if not (scenario_dir / relative).is_file():
                    raise AssertionError(f"missing sweep evidence: {scenario}/{relative}")

        # A same-harness verifier (the shipped claude_verifier shape: honest
        # different_harness=False, HOME not isolated) must never aggregate to a
        # verified sweep — the cross-harness claim requires a foreign judge.
        same_dir = root / "same-harness"
        same = run_sweep(same_dir, FAKE_EVAL_SAME_HARNESS="1")
        if same.returncode == 0:
            raise AssertionError("same-harness sweep must not exit zero")
        same_aggregate = json.loads((same_dir / "aggregate.json").read_text(encoding="utf-8"))
        if same_aggregate["status"] == "VERIFIED PASS":
            raise AssertionError("same-harness sweep must not aggregate to VERIFIED PASS")
        if "different verifier harness" not in json.dumps(same_aggregate):
            raise AssertionError("same-harness rejection must name the different-harness requirement")

        stale = run_sweep(success_dir)
        if stale.returncode != 2 or "output directory is not empty" not in stale.stderr:
            raise AssertionError("sweep must fail closed instead of reusing stale evidence")

        failed_name = REGISTERED[0]
        failure_dir = root / "failure"
        failure = run_sweep(failure_dir, FAKE_EVAL_FAIL_SCENARIO=failed_name)
        if failure.returncode != 1:
            raise AssertionError(f"verified failure must exit 1, got {failure.returncode}: {failure.stderr}")
        aggregate = json.loads((failure_dir / "aggregate.json").read_text(encoding="utf-8"))
        if aggregate["status"] != "VERIFIED FAIL":
            raise AssertionError("one verifier rejection must aggregate to VERIFIED FAIL")
        failed = next(row for row in aggregate["results"] if row["scenario"] == failed_name)
        if failed["status"] != "VERIFIED FAIL":
            raise AssertionError("exact failed scenario was not identified")
        if not failed["violated_controls"]:
            raise AssertionError("failed scenario did not preserve the violated control")
        violation = failed["violated_controls"][0]
        if violation["kind"] != "required" or violation["evidence"] != "forced regression evidence":
            raise AssertionError("failed scenario did not preserve reproduction evidence")

    print("Full eval sweep aggregate regression tests passed.")


if __name__ == "__main__":
    main()
