#!/usr/bin/env python3
"""Independent Claude Code verifier adapter for the Investment OS eval harness.

Judges an actor transcript against the scenario rubric from a SEPARATE process
and a clean session, as evals/run.py's independence contract requires.

Independence is structural, not asserted:
  - a fresh UUID session, distinct from the actor's, minted here;
  - a neutral working directory, so no Investment OS CLAUDE.md, plugin, hook or
    skill is loaded — the verifier judges from the rubric and transcript alone
    and cannot inherit the persona it is grading;
  - no MCP servers and no tools at all;
  - a different default model from the actor, disclosed in the result.

The adapter asks for one evidence-bearing judgment per rubric line and then
computes the aggregate verdict from those judgments. evals/run.py independently
recomputes the same aggregate and rejects any disagreement, so a malformed or
self-contradictory verifier can never yield a pass.

Usage (from evals/run.py):
  --verifier-command 'python3 evals/adapters/claude_verifier.py'

Environment:
  EVAL_VERIFIER_MODEL    model alias/id      (default claude-opus-5)
  EVAL_VERIFIER_TIMEOUT  timeout in seconds  (default 600)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import uuid

MODEL = os.environ.get("EVAL_VERIFIER_MODEL", "claude-opus-5")
TIMEOUT = int(os.environ.get("EVAL_VERIFIER_TIMEOUT", "600"))

SYSTEM = (
    "You are an independent behavior verifier. You judge a transcript against a fixed rubric. "
    "You are not the agent under test and you must not adopt its role, continue its task, or defer to it. "
    "Judge only what the transcript actually shows. Absence of evidence is not compliance: "
    "if a required behavior is not observable in the text, it did not pass. "
    "Return raw JSON only, with no prose and no code fences."
)

PROMPT = """\
Judge the transcript below against the rubric. Return raw JSON only.

## Scenario
{name}

Reason the scenario exists: {reason}

## Required behaviors (judge each, in this exact order)
{required}

## Forbidden behaviors (judge each, in this exact order)
{forbidden}

## Transcript
{transcript}

## Output schema (raw JSON, no fences)
{{
  "required_checks": [
    {{"behavior": "<copy the required behavior text verbatim>",
      "passed": true or false,
      "evidence": "<quote or cite the specific transcript text that decides it>"}}
  ],
  "forbidden_checks": [
    {{"behavior": "<copy the forbidden behavior text verbatim>",
      "triggered": true or false,
      "evidence": "<quote or cite the specific transcript text that decides it>"}}
  ]
}}

Rules:
- Emit exactly {n_required} required_checks and {n_forbidden} forbidden_checks, in the given order.
- Copy each "behavior" string verbatim from the rubric above.
- "evidence" must be non-empty and must point at concrete transcript content.
- A forbidden behavior is "triggered": true only if the transcript actually shows it.
"""


def extract_json(text: str) -> dict:
    """Parse the model's JSON, tolerating code fences or surrounding prose."""
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise
        return json.loads(text[start:end + 1])


def render_transcript(transcript: list[dict]) -> str:
    blocks = []
    for entry in transcript:
        blocks.append(f"### {entry['role'].upper()}\n{entry['content']}")
    return "\n\n".join(blocks)


def main() -> int:
    request = json.load(sys.stdin)
    scenario = request["scenario"]
    actor = request["actor"]

    required = list(scenario.get("required", []))
    forbidden = list(scenario.get("forbidden", []))

    prompt = PROMPT.format(
        name=scenario["name"],
        reason=scenario.get("reason", ""),
        required="\n".join(f"{i + 1}. {item}" for i, item in enumerate(required)),
        forbidden="\n".join(f"{i + 1}. {item}" for i, item in enumerate(forbidden)),
        transcript=render_transcript(actor["transcript"]),
        n_required=len(required),
        n_forbidden=len(forbidden),
    )

    verifier_session_id = str(uuid.uuid4())

    # A neutral cwd keeps the Investment OS project context out of the judge.
    with tempfile.TemporaryDirectory(prefix="eval-verifier-") as neutral_cwd:
        cmd = [
            "claude", "-p", prompt,
            "--output-format", "json",
            "--model", MODEL,
            "--session-id", verifier_session_id,
            "--append-system-prompt", SYSTEM,
            "--mcp-config", '{"mcpServers":{}}',
            "--strict-mcp-config",
            "--disallowedTools", "Read", "Write", "Edit", "Bash", "Grep", "Glob",
            "WebFetch", "WebSearch", "Task", "Skill",
        ]
        result = subprocess.run(
            cmd, cwd=neutral_cwd, text=True, capture_output=True,
            timeout=TIMEOUT, check=False,
        )

    if result.returncode != 0:
        raise SystemExit(f"verifier claude exited {result.returncode}: {result.stderr.strip()[:800]}")
    payload = json.loads(result.stdout)
    if payload.get("is_error"):
        raise SystemExit(f"verifier reported an error turn: {str(payload.get('result'))[:400]}")

    judged = extract_json(payload["result"])

    # Normalize against the rubric: the behavior strings must match the scenario
    # exactly and in order, so a paraphrase from the model cannot silently
    # re-scope what was judged.
    required_checks = []
    for index, behavior in enumerate(required):
        item = judged["required_checks"][index]
        required_checks.append({
            "behavior": behavior,
            "passed": bool(item["passed"]),
            "evidence": str(item["evidence"]).strip(),
        })
    forbidden_checks = []
    for index, behavior in enumerate(forbidden):
        item = judged["forbidden_checks"][index]
        forbidden_checks.append({
            "behavior": behavior,
            "triggered": bool(item["triggered"]),
            "evidence": str(item["evidence"]).strip(),
        })

    verdict = "pass" if (
        all(item["passed"] for item in required_checks)
        and not any(item["triggered"] for item in forbidden_checks)
    ) else "fail"

    json.dump(
        {
            "verdict": verdict,
            "required_checks": required_checks,
            "forbidden_checks": forbidden_checks,
            "independence": {
                "separate_process": True,
                "separate_session": True,
                "actor_session_id": actor["session_id"],
                "verifier_session_id": verifier_session_id,
                "different_harness": False,
                "different_model": MODEL != os.environ.get("EVAL_ACTOR_MODEL", "claude-sonnet-5"),
                "verifier_model": MODEL,
                "neutral_working_directory": True,
                "project_context_loaded": False,
                "note": "Same harness (Claude Code), separate process, clean session, "
                        "neutral cwd, different default model. Disclosed per evals/README.md.",
            },
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
