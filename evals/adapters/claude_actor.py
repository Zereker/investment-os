#!/usr/bin/env python3
"""Claude Code actor adapter for the Investment OS behavior eval harness.

Runs a scenario against a REAL Claude Code session and returns the protocol
JSON that evals/run.py validates. This is the "harness command" the eval
contract leaves open: everything above it is deterministic, this is where a
real agent actually gets exercised.

Session discipline (the eval contract depends on it):
  - A fresh UUID is minted per run and passed with --session-id, so the actor
    never inherits the invoking session. Multi-turn scenarios --resume that
    same id, keeping all turns in ONE persistent session as required.

Isolation (why this cannot touch the real account):
  - --strict-mcp-config with an empty --mcp-config gives the actor NO MCP
    servers at all, so no broker connector is reachable even in principle.
  - Only read-only tools are allowed; writes and shell are denied.
  Scenarios are synthetic by construction; this makes that structural.

The Investment OS plugin itself IS the system under test, so it is loaded via
--plugin-dir: the SessionStart hook injects the router and the skills resolve.

Usage (from evals/run.py):
  --actor-command 'python3 evals/adapters/claude_actor.py'

Environment:
  EVAL_ACTOR_MODEL       model alias/id for the actor   (default claude-sonnet-5)
  EVAL_ACTOR_TIMEOUT     per-turn timeout in seconds    (default 300)
  EVAL_PLUGIN_DIR        Investment OS plugin root      (default: repo root)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL = os.environ.get("EVAL_ACTOR_MODEL", "claude-sonnet-5")
TIMEOUT = int(os.environ.get("EVAL_ACTOR_TIMEOUT", "300"))
PLUGIN_DIR = os.environ.get("EVAL_PLUGIN_DIR", str(REPO_ROOT))

# The agent may consult the published rules and RUN the deterministic engine,
# never mutate anything and never reach a broker.
#
# Scoped script execution is deliberate, not a loosening. The published rules
# require the deterministic engine — not the model — to produce a decision
# packet, so a routine review the agent cannot execute is a harness artifact
# that shows up as a behavior failure. Production sessions have this tool;
# withholding it makes the eval measure the harness instead of the system.
ALLOWED_TOOLS = [
    "Read", "Grep", "Glob", "Skill",
    "Bash(python3 scripts/*)",
    # Read-only git: the rules make repository HEAD the policy authority, so an
    # agent that cannot resolve it fails a grounding requirement for harness
    # reasons. Production sessions have git; these forms cannot mutate history.
    "Bash(git rev-parse*)", "Bash(git log*)", "Bash(git status*)", "Bash(git show*)",
]
DENIED_TOOLS = ["Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Task"]


def claude_turn(prompt: str, session_id: str, first: bool) -> tuple[str, dict]:
    """Run one turn; return the assistant's final text and observability metadata.

    The transcript carries final text only, so a behavior that shows up as tool
    use rather than prose is invisible to the verifier. `num_turns` and any
    permission denials are captured alongside it: num_turns == 1 means the
    model answered without calling a single tool, which distinguishes "did not
    attempt" from "attempted and was blocked" when a rubric asks whether the
    agent tried to resolve something.
    """
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--model", MODEL,
        # no MCP servers whatsoever -> the real broker is unreachable
        "--mcp-config", '{"mcpServers":{}}',
        "--strict-mcp-config",
        "--plugin-dir", PLUGIN_DIR,
        "--allowedTools", *ALLOWED_TOOLS,
        "--disallowedTools", *DENIED_TOOLS,
    ]
    # one persistent session across all turns
    cmd += ["--session-id", session_id] if first else ["--resume", session_id]

    result = subprocess.run(
        cmd, cwd=REPO_ROOT, text=True, capture_output=True,
        timeout=TIMEOUT, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude exited {result.returncode}: {result.stderr.strip()[:800]}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"claude did not return JSON: {exc}; stdout={result.stdout[:400]}") from exc
    if payload.get("is_error"):
        raise RuntimeError(f"claude reported an error turn: {str(payload.get('result'))[:400]}")
    text = payload.get("result")
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("claude returned an empty assistant turn")
    meta = {
        "num_turns": payload.get("num_turns"),
        "used_tools": isinstance(payload.get("num_turns"), int) and payload["num_turns"] > 1,
        "permission_denials": payload.get("permission_denials", []),
    }
    return text, meta


def main() -> int:
    request = json.load(sys.stdin)
    turns = request["turns"]

    # Minted here, never inherited: this is what makes the run a clean session.
    session_id = str(uuid.uuid4())

    transcript: list[dict[str, str]] = []
    turn_meta: list[dict] = []
    for index, turn in enumerate(turns):
        prompt = turn["prompt"]
        reply, meta = claude_turn(prompt, session_id, first=(index == 0))
        transcript.append({"role": "user", "content": prompt})
        transcript.append({"role": "assistant", "content": reply})
        turn_meta.append(meta)

    json.dump(
        {
            "session_id": session_id,
            "harness": {
                "name": "claude-code",
                "model": MODEL,
                "plugin": "investment-os",
                "mcp_servers": "none (--strict-mcp-config with empty config)",
                "tools": {"allowed": ALLOWED_TOOLS, "denied": DENIED_TOOLS},
                "persistent_session": len(turns) > 1,
                # Not judged by the verifier; kept so a reader can tell whether
                # a missing behavior was never attempted or merely unspoken.
                "turn_observability": turn_meta,
            },
            "transcript": transcript,
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
