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
    observed = "2030-01-15T20:00:00+00:00"
    available = {"status": "available", "source": "synthetic-adapter", "observed_at": observed}
    names = (
        "account_summary", "balances", "positions", "open_orders",
        "cash_transactions", "market_inputs", "drawdown_history",
        "tiers_executed", "alert_inventory", "lookthrough", "standing_automations",
    )
    return {
        "as_of": "2030-01-15",
        "input_status": {name: dict(available) for name in names},
        "nav": 100000.0,
        "cash": 17000.0,
        "positions": {"SPYM": 48000.0, "QQQM": 29000.0, "SOXX": 6000.0},
        "open_orders": [],
        "contribution": 1000.0,
        "market_inputs": {
            "SPYM": {
                "live_last": {"value": 89.0},
                "last_completed_close": {"value": 88.0, "source_as_of": "2030-01-14"},
                "ath_close": {"value": 100.0, "source_as_of": "2029-12-20"},
            },
            "QQQM": {"live_last": {"value": 50.0}},
            "SOXX": {"live_last": {"value": 40.0}},
        },
        "tiers_executed": [],
        "alerts": [{
            "id": "synthetic", "symbol": "SPYM", "field": "LAST",
            "operator": "LTE", "price": 90.0, "enabled": True,
        }],
        "lookthrough_current": True,
        "standing_automations": [],
    }


def unavailable(data: dict, source: str, field: str) -> None:
    data["input_status"][source] = {"status": "unavailable", "reason": "synthetic connector gap"}
    data[field] = None


def run(data: dict, *, packet_json: bool) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(SCRIPT)]
    if packet_json:
        command.append("--packet-json")
    return subprocess.run(command, input=json.dumps(data), text=True, capture_output=True, cwd=ROOT)


def packet_for(data: dict) -> dict:
    result = run(data, packet_json=True)
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


def main() -> None:
    packet_data = packet_for(payload())
    assert packet_data["schema_version"] == 2
    assert packet_data["workflow"] == "daily-review"
    assert packet_data["runtime_status"] == "PASS"
    assert packet_data["decision"] == "BUY CANDIDATE"
    assert packet_data["execution_authority"] == "OWNER AUTHORIZATION REQUIRED"
    assert packet_data["eligible_channels"]

    # Identical input produces exactly the same machine packet.
    assert packet_for(payload()) == packet_data

    prose = run(payload(), packet_json=False)
    assert prose.returncode == 0
    assert f"Decision Status: **{packet_data['decision']}**" in prose.stdout
    assert f"Execution authority: {packet_data['execution_authority']}" in prose.stdout

    packet = DecisionPacket(
        schema_version=packet_data["schema_version"], workflow=packet_data["workflow"],
        as_of=packet_data["as_of"], runtime_status=packet_data["runtime_status"],
        decision=packet_data["decision"], facts=packet_data["facts"],
        calculations=packet_data["calculations"], source_status=packet_data["source_status"],
        channel_status=packet_data["channel_status"],
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

    # Explicit unavailability is a valid packet outcome, not a CLI/protocol error.
    missing_orders = payload()
    unavailable(missing_orders, "open_orders", "open_orders")
    blocked = packet_for(missing_orders)
    assert blocked["runtime_status"] == blocked["decision"] == "DATA INCOMPLETE"
    assert blocked["blocking_issues"] == ["open_orders is unavailable"]
    assert blocked["execution_authority"] == "NONE"
    assert blocked["eligible_channels"] == []

    missing_cash_activity = payload()
    unavailable(missing_cash_activity, "cash_transactions", "contribution")
    blocked = packet_for(missing_cash_activity)
    assert blocked["calculations"]["routine_dca"] is None
    assert blocked["calculations"]["strategic"] is None
    assert blocked["calculations"]["drawdown_deployment"] is None
    assert blocked["channel_status"]["routine_dca"] == "DATA INCOMPLETE"
    assert not blocked["eligible_channels"]

    missing_alerts = payload()
    unavailable(missing_alerts, "alert_inventory", "alerts")
    blocked = packet_for(missing_alerts)
    assert blocked["source_status"]["alert_inventory"]["status"] == "unavailable"
    assert blocked["facts"]["alert_pointer"] is None
    assert blocked["decision"] == "DATA INCOMPLETE" and not blocked["eligible_channels"]

    # Live/incomplete market price is disclosed, but drawdown uses only the
    # explicitly identified last completed close.
    intraday = payload()
    intraday["market_inputs"]["SPYM"]["live_last"]["value"] = 70.0
    completed = packet_for(intraday)
    assert completed["facts"]["live_last"]["SPYM"] == 70.0
    assert abs(completed["facts"]["drawdown"] - 0.12) < 1e-12

    # An authoritative empty inventory is distinct from an unavailable one:
    # with an expected pointer, empty is a verified mismatch and records why.
    empty_alerts = payload()
    empty_alerts["alerts"] = []
    empty_result = packet_for(empty_alerts)
    assert any("found 0" in issue for issue in empty_result["blocking_issues"])
    assert empty_result["facts"]["alert_pointer"]["inventory_status"] == "available"

    # Missing look-through localizes to SOXX restore and does not block Core.
    localized = payload()
    localized["lookthrough_current"] = False
    localized_result = packet_for(localized)
    assert localized_result["runtime_status"] == "PASS"
    assert localized_result["channel_status"]["soxx_restore"] == "DATA INCOMPLETE"
    assert all(row["name"] != "SOXX" for row in localized_result["eligible_channels"])

    # A broker-side automation can bypass the intended universe even when no
    # new order is issued, so it blocks candidates and is never auto-mutated.
    automated = payload()
    automated["standing_automations"] = [{"type": "DRIP", "symbol": "SPY", "enabled": True}]
    automated_result = packet_for(automated)
    assert automated_result["decision"] == "DATA INCOMPLETE"
    assert any("out-of-universe symbol SPY" in issue for issue in automated_result["blocking_issues"])
    assert automated_result["eligible_channels"] == []

    invalid = DecisionPacket(
        schema_version=2, workflow="daily-review", as_of="2030-01-15",
        runtime_status="DATA INCOMPLETE", decision="DATA INCOMPLETE", facts={}, calculations={},
        source_status={"positions": {"status": "unavailable"}},
        channel_status={"routine_dca": "DATA INCOMPLETE"},
        eligible_channels=({"name": "SPYM", "amount": 1.0},),
        blocking_issues=("positions unavailable",), attention_items=(), next_conditions=(),
        execution_authority="NONE",
    )
    try:
        invalid.validate()
    except ValueError as exc:
        assert "cannot expose eligible channels" in str(exc)
    else:
        raise AssertionError("incomplete packet exposed an eligible channel")

    print("Decision packet separation tests passed.")


if __name__ == "__main__":
    main()
