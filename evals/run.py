#!/usr/bin/env python3
"""Run a synthetic Investment OS behavior scenario against a real agent command.

The actor command receives the scenario prompt on stdin and must emit the full
assistant transcript on stdout. An optional verifier command receives a JSON
object containing the scenario and transcript on stdin and must exit zero only
when the behavior is compliant.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover - optional eval dependency
    raise SystemExit("Install PyYAML to run behavioral evals: python -m pip install pyyaml") from exc

ROOT = Path(__file__).resolve().parent


def run_command(command: str, stdin: str, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        shlex.split(command),
        input=stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", help="scenario name or YAML path")
    parser.add_argument("--actor-command", required=True, help="agent CLI command reading prompt from stdin")
    parser.add_argument("--verifier-command", help="optional verifier command reading JSON from stdin")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--output", type=Path, help="optional transcript JSON path; use only synthetic scenarios")
    args = parser.parse_args()

    path = Path(args.scenario)
    if not path.is_file():
        path = ROOT / "scenarios" / f"{args.scenario}.yaml"
    scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
    if scenario.get("synthetic") is not True:
        raise SystemExit("Refusing to run or persist a non-synthetic scenario")

    actor = run_command(args.actor_command, scenario["prompt"], args.timeout)
    payload = {
        "scenario": scenario,
        "actor_exit_code": actor.returncode,
        "transcript": actor.stdout,
        "actor_stderr": actor.stderr,
    }
    if actor.returncode != 0:
        print(json.dumps(payload, indent=2), file=sys.stderr)
        raise SystemExit("Actor command failed")

    if args.verifier_command:
        verifier = run_command(args.verifier_command, json.dumps(payload), args.timeout)
        payload["verifier_exit_code"] = verifier.returncode
        payload["verifier_stdout"] = verifier.stdout
        payload["verifier_stderr"] = verifier.stderr
        if verifier.returncode != 0:
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(json.dumps(payload, indent=2), file=sys.stderr)
            raise SystemExit("Behavior verifier rejected the transcript")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
