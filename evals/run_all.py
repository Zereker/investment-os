#!/usr/bin/env python3
"""Run every registered synthetic behavior scenario and enforce one aggregate gate."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from run import normalize_turns, validate_actor_result, validate_verifier_result


ROOT = Path(__file__).resolve().parent
SCENARIOS = ROOT / "scenarios"
RUNNER = ROOT / "run.py"
PASS_EXIT = 0
FAIL_EXIT = 1
NOT_VERIFIED_EXIT = 2


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_registry() -> list[tuple[Path, dict[str, Any]]]:
    registry: list[tuple[Path, dict[str, Any]]] = []
    names: set[str] = set()
    for path in sorted(SCENARIOS.glob("*.yaml")):
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(scenario, dict) or scenario.get("synthetic") is not True:
            raise ValueError(f"registered scenario must be a synthetic object: {path.name}")
        name = scenario.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"registered scenario has no name: {path.name}")
        if name in names:
            raise ValueError(f"duplicate registered scenario name: {name}")
        if path.stem != name:
            raise ValueError(f"scenario filename/name mismatch: {path.stem} != {name}")
        names.add(name)
        registry.append((path, scenario))
    if not registry:
        raise ValueError("no registered behavior scenarios found")
    return registry


def violated_controls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    verifier = payload.get("verifier")
    if not isinstance(verifier, dict):
        return []
    violations: list[dict[str, Any]] = []
    for item in verifier.get("required_checks", []):
        if isinstance(item, dict) and item.get("passed") is False:
            violations.append({
                "kind": "required",
                "control": item.get("behavior"),
                "evidence": item.get("evidence"),
            })
    for item in verifier.get("forbidden_checks", []):
        if isinstance(item, dict) and item.get("triggered") is True:
            violations.append({
                "kind": "forbidden",
                "control": item.get("behavior"),
                "evidence": item.get("evidence"),
            })
    return violations


def validate_result(
    payload: dict[str, Any],
    scenario: dict[str, Any],
    returncode: int,
) -> tuple[str, str | None, str | None]:
    if payload.get("scenario", {}).get("name") != scenario["name"]:
        return "NOT VERIFIED", "result scenario does not match the registered scenario", None
    actor = payload.get("actor")
    if not isinstance(actor, dict):
        return "NOT VERIFIED", "result has no actor object", None
    try:
        turns = normalize_turns(scenario)
        validate_actor_result(actor, len(turns))
    except ValueError as exc:
        return "NOT VERIFIED", f"actor schema invalid: {exc}", None
    harness = actor.get("harness")
    if not isinstance(harness, dict) or harness.get("session_identity_verified") is not True:
        return "NOT VERIFIED", "actor session identity was asserted but not verified", None
    if harness.get("persistent_session") is not (len(turns) > 1):
        return "NOT VERIFIED", "actor persistence metadata conflicts with scenario turn count", None
    observations = harness.get("turn_observability")
    if not isinstance(observations, list) or len(observations) != len(turns):
        return "NOT VERIFIED", "actor did not preserve per-turn session observability", None
    observed_ids = {
        item.get("cli_session_id") for item in observations if isinstance(item, dict)
    }
    if observed_ids != {actor["session_id"]}:
        return "NOT VERIFIED", "actor turns did not prove one persistent CLI session", None

    status = payload.get("status")
    if status not in {"VERIFIED PASS", "VERIFIED FAIL"}:
        return "NOT VERIFIED", str(payload.get("verification_error") or f"invalid result status: {status!r}"), None
    verifier = payload.get("verifier")
    if not isinstance(verifier, dict):
        return "NOT VERIFIED", "verified result has no verifier object", None
    try:
        validate_verifier_result(verifier, scenario, actor["session_id"])
    except ValueError as exc:
        return "NOT VERIFIED", f"verifier schema invalid: {exc}", None
    independence = verifier["independence"]
    if independence.get("different_harness") is not True:
        return "NOT VERIFIED", "aggregate sweep requires a different verifier harness", None
    if independence.get("session_identity_verified") is not True:
        return "NOT VERIFIED", "verifier session identity was asserted but not verified", None
    if independence.get("isolated_home") is not True or independence.get("host_config_inherited") is not False:
        return "NOT VERIFIED", "verifier did not prove throwaway-HOME host-state isolation", None

    if status == "VERIFIED PASS" and returncode != 0:
        return "NOT VERIFIED", f"runner exited {returncode} for a claimed pass", None
    if status == "VERIFIED FAIL" and returncode == 0:
        return "NOT VERIFIED", "runner exited zero for a verified failure", None
    verifier_id = verifier["independence"]["verifier_session_id"]
    return status, None, verifier_id


def write_aggregate(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor-command", required=True)
    parser.add_argument("--verifier-command", required=True)
    parser.add_argument("--timeout", type=int, default=2400)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        registry = load_registry()
    except ValueError as exc:
        print(f"NOT VERIFIED: {exc}", file=sys.stderr)
        return NOT_VERIFIED_EXIT

    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        print(
            f"NOT VERIFIED: output directory is not empty; use a new run directory: {output_dir}",
            file=sys.stderr,
        )
        return NOT_VERIFIED_EXIT
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    aggregate_path = output_dir / "aggregate.json"
    started_at = now()
    rows: list[dict[str, Any]] = []
    actor_ids: list[str] = []
    verifier_ids: list[str] = []

    for path, scenario in registry:
        name = scenario["name"]
        scenario_dir = output_dir / name
        raw_dir = scenario_dir / "raw"
        scenario_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        raw_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        result_path = scenario_dir / "result.json"
        stdout_path = scenario_dir / "runner.stdout.log"
        stderr_path = scenario_dir / "runner.stderr.log"
        command = [
            sys.executable,
            str(RUNNER),
            str(path),
            "--actor-command", args.actor_command,
            "--verifier-command", args.verifier_command,
            "--timeout", str(args.timeout),
            "--output", str(result_path),
        ]
        env = os.environ.copy()
        env["EVAL_EVIDENCE_DIR"] = str(raw_dir)
        scenario_started = now()
        try:
            completed = subprocess.run(
                command,
                cwd=ROOT.parent,
                env=env,
                text=True,
                capture_output=True,
                # run.py applies --timeout to the actor and the verifier
                # SEPARATELY; an outer budget of timeout+30 killed legitimate
                # runs halfway through the verifier phase.
                timeout=2 * args.timeout + 60,
                check=False,
            )
            returncode: int | None = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            returncode = None
            stdout = exc.stdout if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr if isinstance(exc.stderr, str) else "") + "\naggregate runner timeout"
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")

        payload: dict[str, Any] | None = None
        error: str | None = None
        verifier_id: str | None = None
        if not result_path.is_file():
            status = "NOT VERIFIED"
            error = "scenario runner produced no result file"
        else:
            try:
                loaded = json.loads(result_path.read_text(encoding="utf-8"))
                if not isinstance(loaded, dict):
                    raise ValueError("result root is not an object")
                payload = loaded
                status, error, verifier_id = validate_result(
                    payload, scenario, returncode if returncode is not None else -1
                )
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                status = "NOT VERIFIED"
                error = f"result JSON invalid: {exc}"

        actor_id = payload.get("actor", {}).get("session_id") if payload else None
        if isinstance(actor_id, str):
            actor_ids.append(actor_id)
        if isinstance(verifier_id, str):
            verifier_ids.append(verifier_id)
        rows.append({
            "scenario": name,
            "status": status,
            "returncode": returncode,
            "started_at": scenario_started,
            "finished_at": now(),
            "result": str(result_path.relative_to(output_dir)),
            "stdout": str(stdout_path.relative_to(output_dir)),
            "stderr": str(stderr_path.relative_to(output_dir)),
            "raw_evidence": str(raw_dir.relative_to(output_dir)),
            "actor_session_id": actor_id,
            "verifier_session_id": verifier_id,
            "violated_controls": violated_controls(payload or {}),
            "error": error,
        })

        checkpoint = {
            "protocol_version": 1,
            "status": "RUNNING",
            "started_at": started_at,
            "registered_scenarios": [item[1]["name"] for item in registry],
            "completed": len(rows),
            "results": rows,
        }
        write_aggregate(aggregate_path, checkpoint)

    unique_actor_sessions = len(actor_ids) == len(registry) and len(set(actor_ids)) == len(actor_ids)
    unique_verifier_sessions = len(verifier_ids) == len(registry) and len(set(verifier_ids)) == len(verifier_ids)
    statuses = [row["status"] for row in rows]
    all_pass = all(status == "VERIFIED PASS" for status in statuses)
    aggregate_checks = {
        "registry_complete": len(rows) == len(registry),
        "result_files_complete": all((output_dir / row["result"]).is_file() for row in rows),
        "every_scenario_schema_valid": all(row["error"] is None for row in rows),
        "unique_actor_session_per_scenario": unique_actor_sessions,
        "unique_verifier_session_per_scenario": unique_verifier_sessions,
        "every_verifier_cross_harness_and_host_isolated": all(
            row["error"] is None for row in rows
        ),
        "every_scenario_verified_pass": all_pass,
    }
    if all(aggregate_checks.values()):
        overall = "VERIFIED PASS"
        exit_code = PASS_EXIT
    elif "NOT VERIFIED" in statuses or not all(
        value for key, value in aggregate_checks.items() if key != "every_scenario_verified_pass"
    ):
        overall = "NOT VERIFIED"
        exit_code = NOT_VERIFIED_EXIT
    else:
        overall = "VERIFIED FAIL"
        exit_code = FAIL_EXIT

    aggregate = {
        "protocol_version": 1,
        "status": overall,
        "started_at": started_at,
        "finished_at": now(),
        "actor_command": args.actor_command,
        "verifier_command": args.verifier_command,
        "registered_scenarios": [item[1]["name"] for item in registry],
        "scenario_count": len(registry),
        "counts": {
            "verified_pass": statuses.count("VERIFIED PASS"),
            "verified_fail": statuses.count("VERIFIED FAIL"),
            "not_verified": statuses.count("NOT VERIFIED"),
        },
        "aggregate_checks": aggregate_checks,
        "results": rows,
    }
    write_aggregate(aggregate_path, aggregate)
    stream = sys.stdout if exit_code == 0 else sys.stderr
    print(json.dumps(aggregate, indent=2, ensure_ascii=False), file=stream)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
