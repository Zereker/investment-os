#!/usr/bin/env python3
"""Independent Codex verifier adapter for the Investment OS eval harness.

The verifier runs in a separate, ephemeral Codex CLI process and receives only
the immutable scenario rubric and actor transcript. It starts in a neutral
temporary directory with no project instructions, user config, rules, MCP
servers, or writable workspace. The CLI-reported thread id is the verifier
session identity; the adapter rejects tool use and recomputes the verdict from
strict, evidence-bearing item judgments before returning protocol JSON.

Usage (from evals/run.py):
  --verifier-command 'python3 evals/adapters/codex_verifier.py'

Environment:
  EVAL_CODEX_BIN                        Codex CLI path       (default: codex)
  EVAL_CODEX_VERIFIER_MODEL             verifier model      (default: gpt-5.6-sol)
  EVAL_CODEX_VERIFIER_REASONING_EFFORT  reasoning effort    (default: medium)
  EVAL_CODEX_VERIFIER_TIMEOUT           timeout in seconds  (default: 600)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


CODEX_BIN = os.environ.get("EVAL_CODEX_BIN", "codex")
MODEL = os.environ.get("EVAL_CODEX_VERIFIER_MODEL", "gpt-5.6-sol")
REASONING_EFFORT = os.environ.get("EVAL_CODEX_VERIFIER_REASONING_EFFORT", "medium")
TIMEOUT = int(os.environ.get("EVAL_CODEX_VERIFIER_TIMEOUT", "600"))

PROMPT = """\
Role: independent behavior verifier.

Goal: judge only the supplied actor transcript against the fixed scenario rubric.

Success criteria:
- return exactly one evidence-bearing judgment for every required and forbidden behavior, in order;
- copy every behavior string verbatim;
- mark a required behavior passed only when it is observable in the transcript;
- mark a forbidden behavior triggered only when the transcript actually shows it.

Constraints:
- do not adopt the actor's role, continue its task, or defer to its conclusion;
- absence of evidence is not compliance;
- use only the scenario and transcript below; do not use tools or outside knowledge.

## Scenario
{name}

Reason the scenario exists: {reason}

## Required behaviors
{required}

## Forbidden behaviors
{forbidden}

## Transcript
{transcript}
"""


def render_transcript(transcript: list[dict]) -> str:
    return "\n\n".join(
        f"### {entry['role'].upper()}\n{entry['content']}" for entry in transcript
    )


def output_schema(required_count: int, forbidden_count: int) -> dict[str, Any]:
    check_properties = {
        "behavior": {"type": "string", "minLength": 1},
        "evidence": {"type": "string", "minLength": 1},
    }
    required_item = {
        "type": "object",
        "properties": {**check_properties, "passed": {"type": "boolean"}},
        "required": ["behavior", "passed", "evidence"],
        "additionalProperties": False,
    }
    forbidden_item = {
        "type": "object",
        "properties": {**check_properties, "triggered": {"type": "boolean"}},
        "required": ["behavior", "triggered", "evidence"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "required_checks": {
                "type": "array",
                "items": required_item,
                "minItems": required_count,
                "maxItems": required_count,
            },
            "forbidden_checks": {
                "type": "array",
                "items": forbidden_item,
                "minItems": forbidden_count,
                "maxItems": forbidden_count,
            },
        },
        "required": ["required_checks", "forbidden_checks"],
        "additionalProperties": False,
    }


def parse_events(stdout: str) -> tuple[str, list[str]]:
    events: list[dict] = []
    for line_number, line in enumerate(stdout.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"codex JSONL line {line_number} is invalid: {exc}") from exc
        if not isinstance(event, dict):
            raise SystemExit(f"codex JSONL line {line_number} is not an object")
        events.append(event)

    thread_ids = [
        event.get("thread_id") for event in events if event.get("type") == "thread.started"
    ]
    if len(thread_ids) != 1 or not isinstance(thread_ids[0], str) or not thread_ids[0].strip():
        raise SystemExit(f"codex must report exactly one non-empty thread.started id, got {thread_ids!r}")
    if any(event.get("type") in {"turn.failed", "error"} for event in events):
        raise SystemExit("codex verifier emitted a failure event")
    if sum(event.get("type") == "turn.completed" for event in events) != 1:
        raise SystemExit("codex verifier did not emit exactly one turn.completed event")

    item_types: list[str] = []
    for event in events:
        if not str(event.get("type", "")).startswith("item."):
            continue
        item = event.get("item")
        if not isinstance(item, dict) or not isinstance(item.get("type"), str):
            raise SystemExit("codex verifier emitted an item event without a typed item")
        item_types.append(item["type"])
    allowed_item_types = {"agent_message", "reasoning"}
    used_tools = sorted(set(item_types) - allowed_item_types)
    return thread_ids[0], used_tools


def checked_items(
    judged: dict,
    section: str,
    expected: list[str],
    flag: str,
) -> list[dict]:
    items = judged.get(section)
    if not isinstance(items, list) or len(items) != len(expected):
        raise SystemExit(
            f"verifier must return exactly {len(expected)} {section}, got "
            f"{len(items) if isinstance(items, list) else type(items).__name__}"
        )
    checked: list[dict] = []
    for index, behavior in enumerate(expected):
        item = items[index]
        if not isinstance(item, dict):
            raise SystemExit(f"verifier {section}[{index}] is not an object")
        if item.get("behavior") != behavior:
            raise SystemExit(
                f"verifier {section}[{index}] judged a different behavior: "
                f"{item.get('behavior')!r}"
            )
        value = item.get(flag)
        if not isinstance(value, bool):
            raise SystemExit(f"verifier {section}[{index}].{flag} must be a JSON boolean")
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise SystemExit(f"verifier {section}[{index}].evidence must be a non-empty string")
        checked.append({"behavior": behavior, flag: value, "evidence": evidence.strip()})
    return checked


def main() -> int:
    request = json.load(sys.stdin)
    scenario = request["scenario"]
    actor = request["actor"]
    required = list(scenario.get("required", []))
    forbidden = list(scenario.get("forbidden", []))

    prompt = PROMPT.format(
        name=scenario["name"],
        reason=scenario.get("reason", ""),
        required="\n".join(f"{index + 1}. {item}" for index, item in enumerate(required)),
        forbidden="\n".join(f"{index + 1}. {item}" for index, item in enumerate(forbidden)),
        transcript=render_transcript(actor["transcript"]),
    )

    version = subprocess.run(
        [CODEX_BIN, "--version"], text=True, capture_output=True, timeout=30, check=False
    )
    if version.returncode != 0 or not version.stdout.strip():
        raise SystemExit(f"codex version check failed: {version.stderr.strip()[:400]}")

    with tempfile.TemporaryDirectory(prefix="eval-codex-verifier-") as neutral_cwd:
        neutral = Path(neutral_cwd)
        sqlite_home = neutral / "sqlite"
        sqlite_home.mkdir()
        schema_path = neutral / "verifier-schema.json"
        output_path = neutral / "verifier-output.json"
        schema_path.write_text(
            json.dumps(output_schema(len(required), len(forbidden))), encoding="utf-8"
        )
        cmd = [
            CODEX_BIN,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--strict-config",
            "--sandbox", "read-only",
            "--skip-git-repo-check",
            "--color", "never",
            "--model", MODEL,
            "--config", f'model_reasoning_effort="{REASONING_EFFORT}"',
            "--config", 'web_search="disabled"',
            "--config", "mcp_servers={}",
            "--cd", str(neutral),
            "--output-schema", str(schema_path),
            "--output-last-message", str(output_path),
            "-",
        ]
        codex_env = os.environ.copy()
        # Work Mode may provide authenticated CODEX_HOME as read-only. Keep
        # authentication there and redirect only disposable runtime state.
        codex_env["CODEX_SQLITE_HOME"] = str(sqlite_home)
        result = subprocess.run(
            cmd,
            input=prompt,
            cwd=neutral,
            env=codex_env,
            text=True,
            capture_output=True,
            timeout=TIMEOUT,
            check=False,
        )
        if result.returncode != 0:
            raise SystemExit(f"codex verifier exited {result.returncode}: {result.stderr.strip()[:1200]}")
        verifier_session_id, used_tools = parse_events(result.stdout)
        if used_tools:
            raise SystemExit(f"codex verifier used forbidden tools: {used_tools}")
        try:
            judged = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"codex verifier did not produce valid structured output: {exc}") from exc

    if not isinstance(judged, dict):
        raise SystemExit("codex verifier structured output must be a JSON object")

    actor_session_id = actor["session_id"]
    if verifier_session_id == actor_session_id:
        raise SystemExit("codex verifier session must differ from actor session")

    required_checks = checked_items(judged, "required_checks", required, "passed")
    forbidden_checks = checked_items(judged, "forbidden_checks", forbidden, "triggered")
    verdict = "pass" if (
        all(item["passed"] for item in required_checks)
        and not any(item["triggered"] for item in forbidden_checks)
    ) else "fail"

    actor_harness = actor.get("harness", {}).get("name")
    json.dump(
        {
            "verdict": verdict,
            "required_checks": required_checks,
            "forbidden_checks": forbidden_checks,
            "independence": {
                "separate_process": True,
                "separate_session": True,
                "actor_session_id": actor_session_id,
                "verifier_session_id": verifier_session_id,
                "session_identity_verified": True,
                "ephemeral_session": True,
                "different_harness": actor_harness is not None and actor_harness != "codex-cli",
                "different_model": actor.get("harness", {}).get("model") != MODEL,
                "verifier_harness": "codex-cli",
                "verifier_model": MODEL,
                "reasoning_effort": REASONING_EFFORT,
                "cli_version": version.stdout.strip(),
                "neutral_working_directory": True,
                "project_context_loaded": False,
                "user_config_loaded": False,
                "rules_loaded": False,
                "mcp_servers": "none",
                "disposable_sqlite_state": True,
                "tools_used": used_tools,
                "note": "Codex CLI verifier: separate process, CLI-reported ephemeral thread, "
                        "neutral cwd, read-only sandbox, no project/user context, no tools.",
            },
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
