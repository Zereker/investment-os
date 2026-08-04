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
  - The plugin is copied to a disposable, git-less distribution. The actor may
    run only the distribution's deterministic Python scripts, and any writes
    they make land in that disposable copy rather than the source checkout.
  - Direct write tools, network tools and unrestricted shell are denied.
  Scenarios are synthetic by construction; this makes that structural.

The Investment OS plugin itself IS the system under test, so its one native
Skill is loaded from a disposable distribution via --plugin-dir.

Usage (from evals/run.py):
  --actor-command 'python3 evals/adapters/claude_actor.py'

Environment:
  EVAL_ACTOR_MODEL       model alias/id for the actor   (default claude-sonnet-5)
  EVAL_ACTOR_TIMEOUT     per-turn timeout in seconds    (default 600)
  EVAL_PLUGIN_DIR        Investment OS plugin root      (default: nested plugin)
  EVAL_EVIDENCE_DIR      optional raw per-turn evidence directory
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "investment-os"

MODEL = os.environ.get("EVAL_ACTOR_MODEL", "claude-sonnet-5")
# A timeout is a harness artifact that leaves no result rather than a behavior signal.
TIMEOUT = int(os.environ.get("EVAL_ACTOR_TIMEOUT", "600"))
SOURCE_PLUGIN_DIR = Path(os.environ.get("EVAL_PLUGIN_DIR", str(PLUGIN_ROOT))).resolve()

# The agent may consult the published rules and run their deterministic math
# and safety tools, but may never mutate anything or reach a broker.
ALLOWED_TOOLS = [
    "Read", "Grep", "Glob", "Skill",
    "Bash(python3 skills/*/scripts/*)",
]
DENIED_TOOLS = ["Write", "Edit", "NotebookEdit", "WebFetch", "WebSearch", "Task"]


def copy_distribution(source: Path, destination: Path) -> None:
    """Copy the shipped plugin without repository or prior-run state."""
    if not source.is_dir():
        raise RuntimeError(f"EVAL_PLUGIN_DIR is not a directory: {source}")

    source = source.resolve()

    def ignored(directory: str, names: list[str]) -> set[str]:
        omitted = {
            name for name in names
            if name == ".git" or name == "__pycache__" or name.endswith((".pyc", ".pyo"))
        }
        relative = Path(directory).resolve().relative_to(source)
        if relative == Path("evals") and "results" in names:
            omitted.add("results")
        return omitted

    shutil.copytree(source, destination, ignore=ignored)
    if any(destination.rglob(".git")):
        raise RuntimeError("disposable actor distribution unexpectedly contains git metadata")


def claude_turn(
    prompt: str,
    session_id: str,
    first: bool,
    runtime_root: Path,
    turn_index: int,
) -> tuple[str, dict]:
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
        "--plugin-dir", str(runtime_root),
        "--allowedTools", *ALLOWED_TOOLS,
        "--disallowedTools", *DENIED_TOOLS,
    ]
    # one persistent session across all turns
    cmd += ["--session-id", session_id] if first else ["--resume", session_id]

    result = subprocess.run(
        cmd, cwd=runtime_root, text=True, capture_output=True,
        timeout=TIMEOUT, check=False,
    )
    evidence_root = os.environ.get("EVAL_EVIDENCE_DIR")
    if evidence_root:
        evidence = Path(evidence_root) / "claude-actor"
        evidence.mkdir(mode=0o700, parents=True, exist_ok=True)
        prefix = f"turn-{turn_index + 1:03d}"
        (evidence / f"{prefix}.stdout.json").write_text(result.stdout, encoding="utf-8")
        (evidence / f"{prefix}.stderr.log").write_text(result.stderr, encoding="utf-8")
        (evidence / f"{prefix}.metadata.json").write_text(
            json.dumps({
                "returncode": result.returncode,
                "requested_session_id": session_id,
                "session_operation": "create" if first else "resume",
            }, indent=2),
            encoding="utf-8",
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
    # Minting a UUID is not proof. `claude -p` reuses the caller's session when
    # none is passed, so a clean-session claim has to be checked against what
    # the CLI actually reports, not against what we asked for.
    reported = payload.get("session_id")
    if reported != session_id:
        raise RuntimeError(
            f"session identity unverified: asked for {session_id}, CLI reported {reported!r}"
        )
    meta = {
        "num_turns": payload.get("num_turns"),
        "used_tools": isinstance(payload.get("num_turns"), int) and payload["num_turns"] > 1,
        "permission_denials": payload.get("permission_denials", []),
        "cli_session_id": reported,
    }
    return text, meta


def main() -> int:
    request = json.load(sys.stdin)
    turns = request["turns"]

    # Minted here, never inherited: this is what makes the run a clean session.
    session_id = str(uuid.uuid4())

    transcript: list[dict[str, str]] = []
    turn_meta: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="eval-actor-") as temp_root:
        runtime_root = Path(temp_root) / "investment-os"
        copy_distribution(SOURCE_PLUGIN_DIR, runtime_root)
        git_metadata_present = any(runtime_root.rglob(".git"))
        prior_results_present = (runtime_root / "evals" / "results").exists()

        for index, turn in enumerate(turns):
            prompt = turn["prompt"]
            reply, meta = claude_turn(
                prompt,
                session_id,
                first=(index == 0),
                runtime_root=runtime_root,
                turn_index=index,
            )
            transcript.append({"role": "user", "content": prompt})
            transcript.append({"role": "assistant", "content": reply})
            turn_meta.append(meta)

    # Every turn must have run in the one session; a resumed turn that reported
    # a different id would mean the transcript is not a single conversation.
    reported_ids = {m["cli_session_id"] for m in turn_meta}
    if reported_ids != {session_id}:
        raise RuntimeError(f"turns did not share one session: {sorted(reported_ids)}")

    json.dump(
        {
            "session_id": session_id,
            "harness": {
                "name": "claude-code",
                "model": MODEL,
                "plugin": "investment-os",
                "mcp_servers": "none (--strict-mcp-config with empty config)",
                "tools": {"allowed": ALLOWED_TOOLS, "denied": DENIED_TOOLS},
                "disposable_distribution": True,
                "git_metadata_present": git_metadata_present,
                "prior_eval_results_present": prior_results_present,
                "persistent_session": len(turns) > 1,
                "session_identity_verified": True,
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
