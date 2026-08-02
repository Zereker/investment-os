#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "evals" / "run.py"
SCENARIO = ROOT / "evals" / "scenarios" / "rewording-does-not-reset-intent.yaml"
ACTOR = ROOT / "tests" / "fixtures" / "fake_eval_actor.py"
VERIFIER = ROOT / "tests" / "fixtures" / "fake_eval_verifier.py"


def run(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(SCENARIO),
            "--actor-command",
            f"{sys.executable} {ACTOR}",
            *extra,
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    missing = run()
    if missing.returncode == 0 or "NOT VERIFIED: no verifier configured" not in missing.stderr:
        raise AssertionError("missing verifier must be non-zero and explicitly NOT VERIFIED")

    actor_only = run("--actor-only")
    if actor_only.returncode == 0 or "NOT VERIFIED: actor-only smoke run" not in actor_only.stderr:
        raise AssertionError("actor-only mode must never report verified success")
    actor_payload = json.loads(actor_only.stdout)
    if actor_payload["status"] != "NOT VERIFIED":
        raise AssertionError("actor-only payload must remain NOT VERIFIED")
    transcript = actor_payload["actor"]["transcript"]
    if len([item for item in transcript if item["role"] == "user"]) != 2:
        raise AssertionError("multi-turn scenario was not preserved in one actor transcript")

    verified = run("--verifier-command", f"{sys.executable} {VERIFIER}")
    if verified.returncode != 0:
        raise AssertionError(f"valid independent verifier should pass: {verified.stderr}")
    payload = json.loads(verified.stdout)
    if payload["status"] != "VERIFIED PASS":
        raise AssertionError("verified run did not produce VERIFIED PASS")
    if payload["actor"]["session_id"] == payload["verifier"]["independence"]["verifier_session_id"]:
        raise AssertionError("actor and verifier sessions must differ")

    print("Eval integrity regression tests passed.")


if __name__ == "__main__":
    main()
