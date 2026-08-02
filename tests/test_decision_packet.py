#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from runtime_paths import SCRIPT_DIRS
from decision_packet import DecisionPacket, assert_renderer_preserves

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPT_DIRS["daily"] / "daily_brief.py"


def payload() -> dict:
    return {
        "as_of": "2030-01-15", "nav": 100000.0, "cash": 17000.0,
        "positions": {"SPYM": 48000.0, "QQQM": 29000.0, "SOXX": 6000.0},
        "contribution": 1000.0, "drawdown": 0.12, "tiers_executed": [],
        "lookthrough_current": True,
        "account_inputs": {
            "account_summary": True, "balances": True,
            "positions": True, "open_orders": True,
        },
        "open_orders": [],
    }


def run(data: dict, *, packet_json: bool) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT)]
    if packet_json:
        command.append("--packet-json")
    return subprocess.run(command, input=json.dumps(data), text=True, capture_output=True, cwd=ROOT)


def main() -> None:
    first = run(payload(), packet_json=True)
    assert first.returncode == 0, first.stderr + first.stdout
    packet_data = json.loads(first.stdout)
    assert packet_data["workflow"] == "daily-review"
    assert packet_data["runtime_status"] == "PASS"
    assert packet_data["decision"] == "BUY CANDIDATE"
    assert packet_data["execution_authority"] == "OWNER AUTHORIZATION REQUIRED"
    assert packet_data["eligible_channels"]

    # Identical input produces exactly the same machine packet.
    second = run(payload(), packet_json=True)
    assert json.loads(second.stdout) == packet_data

    # Prose is downstream of the packet and must expose the authoritative values.
    prose = run(payload(), packet_json=False)
    assert prose.returncode == 0
    assert f"Decision Status: **{packet_data['decision']}**" in prose.stdout
    assert f"Execution authority: {packet_data['execution_authority']}" in prose.stdout

    packet = DecisionPacket(
        schema_version=packet_data["schema_version"], workflow=packet_data["workflow"],
        as_of=packet_data["as_of"], runtime_status=packet_data["runtime_status"],
        decision=packet_data["decision"], facts=packet_data["facts"],
        calculations=packet_data["calculations"],
        eligible_channels=tuple(packet_data["eligible_channels"]),
        blocking_issues=tuple(packet_data["blocking_issues"]),
        attention_items=tuple(packet_data["attention_items"]),
        next_conditions=tuple(packet_data["next_conditions"]),
        execution_authority=packet_data["execution_authority"],
    )
    packet.validate()
    try:
        assert_renderer_preserves(packet, {
            "schema_version": packet.schema_version, "workflow": packet.workflow,
            "as_of": packet.as_of, "runtime_status": packet.runtime_status,
            "decision": "HOLD", "execution_authority": packet.execution_authority,
        })
    except ValueError as exc:
        assert "renderer changed authoritative field: decision" in str(exc)
    else:
        raise AssertionError("renderer was allowed to change decision")

    # Missing open-orders authority blocks presentation even when math has positive channels.
    incomplete = payload()
    incomplete["account_inputs"]["open_orders"] = False
    blocked = json.loads(run(incomplete, packet_json=True).stdout)
    assert blocked["runtime_status"] == blocked["decision"] == "DATA INCOMPLETE"
    assert blocked["blocking_issues"] == ["open_orders"]
    assert blocked["execution_authority"] == "NONE"
    assert blocked["eligible_channels"]  # inspectable math, not authorization
    blocked_prose = run(incomplete, packet_json=False).stdout
    assert "停止新的购买候选" in blocked_prose
    assert "BUY CANDIDATE —" not in blocked_prose

    invalid = DecisionPacket(
        schema_version=1, workflow="daily-review", as_of="2030-01-15",
        runtime_status="DATA INCOMPLETE", decision="HOLD", facts={}, calculations={},
        eligible_channels=(), blocking_issues=("missing positions",), attention_items=(),
        next_conditions=(), execution_authority="NONE",
    )
    try:
        invalid.validate()
    except ValueError as exc:
        assert "incomplete runtime" in str(exc)
    else:
        raise AssertionError("invalid runtime/decision combination passed")

    print("Decision packet separation tests passed.")


if __name__ == "__main__":
    main()
