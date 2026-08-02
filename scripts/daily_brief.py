#!/usr/bin/env python3
"""Build and render the three-ETF Daily Brief from normalized runtime JSON.

The deterministic engine returns a DecisionPacket. Presentation consumes that packet
and never recomputes policy state. This script never writes inputs or output to disk
and never places an order.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date
from typing import Any

from account_reconciliation import reconcile_nav
from decision_packet import DecisionPacket, assert_renderer_preserves
from monthly_execution import TIERS, compute

UNIVERSE = ("SPYM", "QQQM", "SOXX")
REQUIRED_ACCOUNT_INPUTS = ("account_summary", "balances", "positions", "open_orders")


class InputError(ValueError):
    pass


def number(value: Any, name: str, *, nonnegative: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise InputError(f"{name} must be finite")
    if nonnegative and result < 0:
        raise InputError(f"{name} must be nonnegative")
    return result


def validate_input(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "as_of", "nav", "cash", "positions", "contribution", "drawdown",
        "tiers_executed", "lookthrough_current", "account_inputs", "open_orders",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise InputError("missing fields: " + ", ".join(missing))
    nav = number(payload["nav"], "nav")
    if nav <= 0:
        raise InputError("nav must be positive")
    cash = number(payload["cash"], "cash", nonnegative=False)
    contribution = number(payload["contribution"], "contribution")
    drawdown = number(payload["drawdown"], "drawdown")
    if not 0 <= drawdown < 1:
        raise InputError("drawdown must be in [0, 1)")
    if not isinstance(payload["positions"], dict):
        raise InputError("positions must be an object")
    positions = {
        str(symbol).upper(): number(value, f"positions.{symbol}")
        for symbol, value in payload["positions"].items()
    }
    if not isinstance(payload["account_inputs"], dict):
        raise InputError("account_inputs must be an object")
    account_inputs = {
        name: bool(payload["account_inputs"].get(name, False))
        for name in REQUIRED_ACCOUNT_INPUTS
    }
    valid_tiers = {row[1] for row in TIERS}
    tiers = payload["tiers_executed"]
    if not isinstance(tiers, list) or any(tier not in valid_tiers for tier in tiers):
        raise InputError("tiers_executed must contain only T1/T2/T3/T4")
    if not isinstance(payload["open_orders"], list):
        raise InputError("open_orders must be a list")
    return {
        **payload,
        "nav": nav,
        "cash": cash,
        "contribution": contribution,
        "drawdown": drawdown,
        "positions": positions,
        "account_inputs": account_inputs,
        "tiers_executed": set(tiers),
        "lookthrough_current": bool(payload["lookthrough_current"]),
    }


def build_packet(payload: dict[str, Any]) -> DecisionPacket:
    p = validate_input(payload)
    nav = p["nav"]
    positions = p["positions"]
    spym, qqqm, soxx = (positions.get(symbol, 0.0) for symbol in UNIVERSE)
    other = tuple(sorted(symbol for symbol in positions if symbol not in UNIVERSE))
    reconciliation_result = reconcile_nav(nav, p["cash"], positions.values())
    reconciliation = reconciliation_result.relative_difference

    blockers = [name for name, ok in p["account_inputs"].items() if not ok]
    if not reconciliation_result.passed:
        blockers.append(reconciliation_result.issue or "account reconciliation failed")

    result = compute(
        nav, p["cash"], spym, qqqm, soxx, p["contribution"],
        p["drawdown"], p["tiers_executed"],
        date.fromisoformat(str(p["as_of"])[:10]), p["lookthrough_current"],
    )
    channel_specs = (
        ("SPYM", "Core routine/drawdown", result["d_spym"] + result["b_spym"] + result["dd_spym"]),
        ("QQQM", "Core routine/drawdown", result["d_qqqm"] + result["b_qqqm"] + result["dd_qqqm"]),
        ("SOXX", "restore", result["restore"]),
    )
    eligible = tuple(
        {"name": symbol, "channel": channel, "amount": amount, "nav_weight": amount / nav}
        for symbol, channel, amount in channel_specs if amount > 1e-8
    )
    runtime_status = "DATA INCOMPLETE" if blockers else "PASS"
    decision = "DATA INCOMPLETE" if blockers else ("BUY CANDIDATE" if eligible else "HOLD")

    attention: list[str] = []
    if other:
        attention.append("Review Out-of-Universe holdings under Legacy/exception rules; do not add.")
    if p["open_orders"]:
        attention.append("Resolve duplicate, conflicting or stale open orders before new action.")

    next_conditions: list[str] = []
    next_tier = next(((name, trigger) for trigger, name, _ in TIERS if p["drawdown"] < trigger), None)
    if next_tier:
        next_conditions.append(f"SPYM reaches {next_tier[0]} at {next_tier[1]:.2%} drawdown.")
    else:
        next_conditions.append("Drawdown ladder is fully triggered; no deeper tier exists.")
    if p["contribution"] <= 0:
        next_conditions.append("Monthly contribution arrives and is confirmed in IBKR.")
    if not p["lookthrough_current"]:
        next_conditions.append("Current-quarter look-through check becomes valid before SOXX restore.")
    if blockers:
        next_conditions.append("All task-required broker inputs reconcile successfully.")

    packet = DecisionPacket(
        schema_version=1,
        workflow="daily-review",
        as_of=str(p["as_of"]),
        runtime_status=runtime_status,
        decision=decision,
        facts={
            "universe": UNIVERSE,
            "nav": nav,
            "cash": p["cash"],
            "positions": positions,
            "out_of_universe": other,
            "open_order_count": len(p["open_orders"]),
            "drawdown": p["drawdown"],
            "account_inputs": p["account_inputs"],
            "reconciliation_weight": reconciliation,
        },
        calculations={
            "gap_spym": result["gap_spym"], "gap_qqqm": result["gap_qqqm"],
            "routine_dca": result["d"], "strategic": result["b"],
            "drawdown_deployment": result["dd_amount"], "soxx_restore": result["restore"],
            "consumed_tiers": tuple(result["consumed"]),
        },
        eligible_channels=eligible,
        blocking_issues=tuple(blockers),
        attention_items=tuple(attention),
        next_conditions=tuple(next_conditions),
        execution_authority="NONE" if decision in {"HOLD", "DATA INCOMPLETE"} else "OWNER AUTHORIZATION REQUIRED",
    )
    packet.validate()
    return packet


def pct(value: float) -> str:
    return f"{value:.2%}"


def render_packet(packet: DecisionPacket) -> str:
    packet.validate()
    facts, calc = packet.facts, packet.calculations
    nav = facts["nav"]
    positions = facts["positions"]
    lines = [
        "# Investment OS — Daily Brief", f"As of: {packet.as_of}", "",
        "## 1. Executive Summary", f"- Decision Status: **{packet.decision}**",
        "- Production universe: SPYM / QQQM / SOXX only.",
        f"- SPYM drawdown: {pct(facts['drawdown'])}.",
        f"- Open orders: {facts['open_order_count']}.", "",
        "## 2. Account Health",
        "- Inputs: " + ", ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in facts["account_inputs"].items()),
        f"- Reconciliation difference: {pct(facts['reconciliation_weight'])} of NAV.",
        f"- Status: {packet.runtime_status}", "", "## 3. Portfolio State",
        f"- Cash: {pct(facts['cash'] / nav)}",
        f"- SPYM: {pct(positions.get('SPYM', 0) / nav)} | positive gap {pct(calc['gap_spym'] / nav)}",
        f"- QQQM: {pct(positions.get('QQQM', 0) / nav)} | positive gap {pct(calc['gap_qqqm'] / nav)}",
        f"- SOXX: {pct(positions.get('SOXX', 0) / nav)} | execution cap 3% | hard cap 6%",
        "- Out-of-Universe: " + (", ".join(facts["out_of_universe"]) + "（只披露，不产生新增候选）" if facts["out_of_universe"] else "None"),
        "", "## 4. What the Rules Mean",
        f"- Monthly contribution channel: {pct(calc['routine_dca'] / nav)} of NAV authorized.",
        f"- Strategic cash migration channel: {pct(calc['strategic'] / nav)} of NAV authorized.",
        f"- Drawdown channel: {pct(calc['drawdown_deployment'] / nav)} of NAV authorized; newly consumed tiers: {', '.join(calc['consumed_tiers']) or 'None'}.",
        f"- SOXX restore channel: {pct(calc['soxx_restore'] / nav)} of NAV authorized.",
        "", "## 5. What Is Allowed Today",
    ]
    if packet.decision == "DATA INCOMPLETE":
        lines.append("- DATA INCOMPLETE：停止新的购买候选。")
    elif packet.eligible_channels:
        lines.extend(
            f"- BUY CANDIDATE — {item['name']}：{item['channel']}，授权上限约 {pct(item['nav_weight'])} of NAV；仍须所有者确认。"
            for item in packet.eligible_channels
        )
    else:
        lines.append("- HOLD：没有标的获得新的购买授权。")
    lines.extend(["", "## 6. Why Not the Others",
                  "- Other securities: outside the closed Production universe.",
                  "", "## 7. Attention Items"])
    lines.extend((f"- {item}" for item in packet.attention_items) or ["- None."])
    if packet.blocking_issues:
        lines.extend(f"- Blocking: {item}" for item in packet.blocking_issues)
    lines.extend(["", "## 8. Next Observation Conditions"])
    lines.extend(f"- {item}" for item in packet.next_conditions)
    lines.extend(["", "## 9. Execution Boundary",
                  f"Execution authority: {packet.execution_authority}. This renderer cannot place or format an order."])
    metadata = {
        "schema_version": packet.schema_version, "workflow": packet.workflow,
        "as_of": packet.as_of, "runtime_status": packet.runtime_status,
        "decision": packet.decision, "execution_authority": packet.execution_authority,
    }
    assert_renderer_preserves(packet, metadata)
    return "\n".join(lines)


def render(payload: dict[str, Any]) -> str:
    return render_packet(build_packet(payload))


def synthetic_payload() -> dict[str, Any]:
    return {
        "as_of": "2030-01-15", "nav": 100000.0, "cash": 17000.0,
        "positions": {"SPYM": 48000.0, "QQQM": 29000.0, "SOXX": 6000.0},
        "contribution": 1000.0, "drawdown": 0.12, "tiers_executed": [],
        "lookthrough_current": True,
        "account_inputs": {name: True for name in REQUIRED_ACCOUNT_INPUTS},
        "open_orders": [],
    }


def self_test() -> None:
    packet = build_packet(synthetic_payload())
    assert packet.decision == "BUY CANDIDATE"
    output = render_packet(packet)
    for text in ("Daily Brief", "SPYM / QQQM / SOXX only", "Why Not the Others", "Execution Boundary"):
        assert text in output
    incomplete = synthetic_payload()
    incomplete["account_inputs"] = {**incomplete["account_inputs"], "positions": False}
    assert build_packet(incomplete).decision == "DATA INCOMPLETE"
    outside = synthetic_payload()
    outside["positions"] = {**outside["positions"], "SYNTHETIC_X": 100.0}
    outside["nav"] = 100100.0
    text = render(outside)
    assert "Out-of-Universe: SYNTHETIC_X" in text and "BUY CANDIDATE — SYNTHETIC_X" not in text
    print("daily brief self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--packet-json", action="store_true", help="emit DecisionPacket JSON instead of prose")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    try:
        packet = build_packet(json.load(sys.stdin))
        print(json.dumps(packet.as_dict(), ensure_ascii=False, sort_keys=True) if args.packet_json else render_packet(packet))
    except (InputError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print("# Investment OS — Daily Brief\n\nDecision Status: **DATA INCOMPLETE**")
        print(f"\nInput error: {exc}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
