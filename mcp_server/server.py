"""Remote MCP entry point for using Investment OS from ChatGPT."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.policy import load_task_context, supported_tasks

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_SCRIPTS = ROOT / "skills" / "investment-os" / "scripts"
sys.path.insert(0, str(RUNTIME_SCRIPTS))

from broker_runtime import validate_runtime  # noqa: E402

SERVER_INSTRUCTIONS = """
Investment OS is a rules-first, read-only portfolio decision plugin.
Before answering an Investment OS task, call load_investment_os with the matching
task and apply the returned canonical Skill and references. Never infer live
account state. Account-dependent paths require fresh authoritative broker data
and validate_broker_runtime must return PASS. Missing, stale, conflicting, or
manually supplied account data leaves only the affected path DATA INCOMPLETE.
This server never submits broker orders and never persists portfolio data.
"""

mcp = FastMCP(
    "Investment OS",
    instructions=SERVER_INSTRUCTIONS.strip(),
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    stateless_http=True,
    json_response=True,
)


@mcp.tool()
def load_investment_os(task: str) -> dict[str, object]:
    """Load canonical rules for one task. Call this before an Investment OS answer.

    Supported tasks are daily, monthly_funding, periodic_review,
    transaction_judgment, research, broker_execution, and system_audit.
    The response contains the canonical SKILL.md and only the required policy
    references. It contains no portfolio data.
    """
    return load_task_context(task)


@mcp.tool()
def list_investment_os_tasks() -> dict[str, object]:
    """List task names accepted by load_investment_os."""
    return {"tasks": list(supported_tasks())}


@mcp.tool()
def validate_broker_runtime(
    runtime: dict[str, Any],
    required_capabilities: list[str],
    max_age_seconds: int = 300,
) -> dict[str, Any]:
    """Validate ephemeral broker facts before any account-dependent judgment.

    Pass broker output from an authoritative connected capability, including
    source and observation timestamps. Never substitute chat-pasted numbers,
    estimates, empty collections, or zero for missing broker facts. This tool
    validates only and does not persist the payload or perform a broker write.
    """
    if not isinstance(runtime, dict):
        return {
            "runtime_status": "DATA INCOMPLETE",
            "blocking_issues": ["runtime must be an object"],
            "observation_skew_seconds": None,
        }
    if max_age_seconds < 1 or max_age_seconds > 3600:
        return {
            "runtime_status": "DATA INCOMPLETE",
            "blocking_issues": ["max_age_seconds must be between 1 and 3600"],
            "observation_skew_seconds": None,
        }
    return validate_runtime(
        runtime,
        required_capabilities,
        max_age_seconds=max_age_seconds,
    ).as_dict()


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
