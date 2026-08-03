#!/usr/bin/env python3
"""Build a fail-closed Daily Brief from normalized, capability-aware JSON.

Unavailable data is represented by an explicit source status and a null value.
That is a valid runtime outcome and therefore still produces a DecisionPacket.
Only malformed input protocol exits with an input error. This module never writes inputs or output to disk,
never persists account data, and never places or formats an order.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "reconstructing-portfolio-state" / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "running-monthly-review" / "scripts"))
sys.path.insert(0, str(PLUGIN_ROOT / "skills" / "validating-drawdown-state" / "scripts"))
from account_reconciliation import reconcile_nav  # noqa: E402
from alert_pointer_check import check as check_alert_pointer  # noqa: E402
from decision_packet import DecisionPacket, assert_renderer_preserves  # noqa: E402
from monthly_execution import TIERS, compute, portfolio_state  # noqa: E402

UNIVERSE = ("SPYM", "QQQM", "SOXX")
VALID_SOURCE_STATES = {"available", "unavailable", "stale", "conflicting"}
SOURCE_VALUE_FIELDS = {
    "account_summary": "nav",
    "balances": "cash",
    "positions": "positions",
    "open_orders": "open_orders",
    "cash_transactions": "contribution",
    "market_inputs": "market_inputs",
    "drawdown_history": "market_inputs",
    "tiers_executed": "tiers_executed",
    "alert_inventory": "alerts",
    "lookthrough": "lookthrough_current",
    "standing_automations": "standing_automations",
}
GLOBAL_REQUIRED = (
    "account_summary", "balances", "positions", "open_orders",
    "cash_transactions", "market_inputs", "drawdown_history",
    "tiers_executed", "alert_inventory",
)


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


def _timestamp(value: Any, name: str) -> str:
    if not isinstance(value, str):
        raise InputError(f"{name} must be an ISO-8601 timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputError(f"{name} must be an ISO-8601 timezone-aware timestamp") from exc
    if parsed.tzinfo is None:
        raise InputError(f"{name} must include a timezone")
    return value


def _source_status(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = payload.get("input_status")
    if not isinstance(raw, dict):
        raise InputError("input_status must be an object")
    normalized: dict[str, dict[str, Any]] = {}
    for name, value_field in SOURCE_VALUE_FIELDS.items():
        entry = raw.get(name)
        if not isinstance(entry, dict):
            normalized[name] = {
                "status": "unavailable", "source": None,
                "observed_at": None, "reason": "status not declared",
            }
            continue
        state = str(entry.get("status", "")).lower()
        if state not in VALID_SOURCE_STATES:
            raise InputError(f"input_status.{name}.status is invalid")
        source = entry.get("source")
        observed_at = entry.get("observed_at")
        if state == "available":
            if not isinstance(source, str) or not source.strip():
                raise InputError(f"input_status.{name}.source is required when available")
            observed_at = _timestamp(observed_at, f"input_status.{name}.observed_at")
        elif payload.get(value_field) is not None and name != "drawdown_history":
            raise InputError(
                f"{name} is {state}; {value_field} must be null, not an empty or zero value"
            )
        normalized[name] = {
            "status": state,
            "source": source if state == "available" else None,
            "observed_at": observed_at if state == "available" else None,
            "source_as_of": entry.get("source_as_of"),
            "reason": entry.get("reason"),
        }
    return normalized


def _available(statuses: dict[str, dict[str, Any]], name: str) -> bool:
    return statuses[name]["status"] == "available"


def _price_node(raw: Any, name: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise InputError(f"{name} must be an object")
    value = number(raw.get("value"), f"{name}.value")
    return {"value": value, "source_as_of": raw.get("source_as_of")}


def validate_input(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise InputError("input must be an object")
    if not isinstance(payload.get("as_of"), str):
        raise InputError("as_of is required")
    try:
        date.fromisoformat(payload["as_of"][:10])
    except ValueError as exc:
        raise InputError("as_of must begin with an ISO date") from exc

    statuses = _source_status(payload)
    result: dict[str, Any] = {"as_of": payload["as_of"], "source_status": statuses}

    result["nav"] = number(payload.get("nav"), "nav") if _available(statuses, "account_summary") else None
    if result["nav"] is not None and result["nav"] <= 0:
        raise InputError("nav must be positive")
    result["cash"] = number(payload.get("cash"), "cash", nonnegative=False) if _available(statuses, "balances") else None

    if _available(statuses, "positions"):
        if not isinstance(payload.get("positions"), dict):
            raise InputError("positions must be an object")
        result["positions"] = {
            str(symbol).upper(): number(value, f"positions.{symbol}")
            for symbol, value in payload["positions"].items()
        }
    else:
        result["positions"] = None

    if _available(statuses, "open_orders"):
        if not isinstance(payload.get("open_orders"), list):
            raise InputError("open_orders must be a list")
        result["open_orders"] = payload["open_orders"]
    else:
        result["open_orders"] = None

    result["contribution"] = (
        number(payload.get("contribution"), "contribution")
        if _available(statuses, "cash_transactions") else None
    )

    valid_tiers = {row[1] for row in TIERS}
    if _available(statuses, "tiers_executed"):
        tiers = payload.get("tiers_executed")
        if not isinstance(tiers, list) or any(tier not in valid_tiers for tier in tiers):
            raise InputError("tiers_executed must contain only T1/T2/T3/T4")
        result["tiers_executed"] = set(tiers)
    else:
        result["tiers_executed"] = None

    result["market_inputs"] = None
    result["drawdown"] = None
    if _available(statuses, "market_inputs"):
        market = payload.get("market_inputs")
        if not isinstance(market, dict):
            raise InputError("market_inputs must be an object")
        normalized_market: dict[str, Any] = {}
        for symbol in UNIVERSE:
            row = market.get(symbol)
            if not isinstance(row, dict):
                raise InputError(f"market_inputs.{symbol} must be an object")
            normalized_market[symbol] = {"live_last": _price_node(row.get("live_last"), f"market_inputs.{symbol}.live_last")}
        if _available(statuses, "drawdown_history"):
            spym = market["SPYM"]
            completed = _price_node(spym.get("last_completed_close"), "market_inputs.SPYM.last_completed_close")
            ath = _price_node(spym.get("ath_close"), "market_inputs.SPYM.ath_close")
            if ath["value"] <= 0:
                raise InputError("market_inputs.SPYM.ath_close.value must be positive")
            normalized_market["SPYM"].update({"last_completed_close": completed, "ath_close": ath})
            result["drawdown"] = max((ath["value"] - completed["value"]) / ath["value"], 0.0)
        result["market_inputs"] = normalized_market

    if _available(statuses, "alert_inventory"):
        if not isinstance(payload.get("alerts"), list):
            raise InputError("alerts must be a list")
        result["alerts"] = payload["alerts"]
    else:
        result["alerts"] = None

    if _available(statuses, "lookthrough"):
        if not isinstance(payload.get("lookthrough_current"), bool):
            raise InputError("lookthrough_current must be boolean")
        result["lookthrough_current"] = payload["lookthrough_current"]
    else:
        result["lookthrough_current"] = None

    if _available(statuses, "standing_automations"):
        if not isinstance(payload.get("standing_automations"), list):
            raise InputError("standing_automations must be a list")
        result["standing_automations"] = payload["standing_automations"]
    else:
        result["standing_automations"] = None
    return result


def build_packet(payload: dict[str, Any]) -> DecisionPacket:
    p = validate_input(payload)
    statuses = p["source_status"]
    blockers = [f"{name} is {statuses[name]['status']}" for name in GLOBAL_REQUIRED if not _available(statuses, name)]
    attention: list[str] = []
    next_conditions: list[str] = []

    nav, cash, positions = p["nav"], p["cash"], p["positions"]
    core_ready = nav is not None and cash is not None and positions is not None
    state = None
    reconciliation = None
    other: tuple[str, ...] = ()
    if core_ready:
        spym, qqqm, soxx = (positions.get(symbol, 0.0) for symbol in UNIVERSE)
        state = portfolio_state(
            nav, cash, spym, qqqm, soxx, date.fromisoformat(p["as_of"][:10]),
            p["lookthrough_current"] is True,
        )
        reconciliation_result = reconcile_nav(nav, cash, positions.values())
        reconciliation = reconciliation_result.relative_difference
        if not reconciliation_result.passed:
            blockers.append(reconciliation_result.issue or "account reconciliation failed")
        other = tuple(sorted(symbol for symbol in positions if symbol not in UNIVERSE))
        if other:
            attention.append("Review Out-of-Universe holdings under Legacy/exception rules; do not add.")

    if p["open_orders"]:
        attention.append("Resolve duplicate, conflicting or stale open orders before new action.")

    standing = p["standing_automations"]
    if standing is None:
        attention.append("Standing broker automations were not verified; inspect them manually before execution.")
    else:
        for index, automation in enumerate(standing):
            if not isinstance(automation, dict):
                raise InputError(f"standing_automations[{index}] must be an object")
            symbol = str(automation.get("symbol", "")).upper()
            if automation.get("enabled") is True and symbol not in UNIVERSE:
                blockers.append(f"enabled standing automation targets out-of-universe symbol {symbol or 'UNKNOWN'}")
                attention.append("Disable or explicitly govern the out-of-universe broker automation; no automatic mutation was attempted.")

    alert_result = None
    market = p["market_inputs"]
    if market is not None and p["tiers_executed"] is not None and _available(statuses, "alert_inventory"):
        ath = market.get("SPYM", {}).get("ath_close", {}).get("value")
        if ath is not None:
            alert_result = check_alert_pointer({
                "ath_close": ath,
                "tiers_executed": sorted(p["tiers_executed"]),
                "alert_inventory_status": "available",
                "alerts": p["alerts"],
            })
            if alert_result["status"] != "PASS":
                blockers.extend(f"alert pointer: {issue}" for issue in alert_result["issues"])

    full_math_ready = core_ready and p["contribution"] is not None and p["drawdown"] is not None and p["tiers_executed"] is not None
    result = None
    if full_math_ready:
        spym, qqqm, soxx = (positions.get(symbol, 0.0) for symbol in UNIVERSE)
        result = compute(
            nav, cash, spym, qqqm, soxx, p["contribution"], p["drawdown"],
            p["tiers_executed"], date.fromisoformat(p["as_of"][:10]),
            p["lookthrough_current"] is True,
        )
        if not result["floor_ok"]:
            blockers.append("candidate channels would breach the effective cash floor")

    channel_status = {
        "routine_dca": "PASS" if core_ready and p["contribution"] is not None else "DATA INCOMPLETE",
        "strategic": "PASS" if core_ready and p["contribution"] is not None else "DATA INCOMPLETE",
        "drawdown_deployment": "PASS" if full_math_ready and alert_result and alert_result["status"] == "PASS" else "DATA INCOMPLETE",
        "soxx_restore": (
            "PASS" if core_ready and p["lookthrough_current"] is True
            else "DATA INCOMPLETE" if core_ready else "DATA INCOMPLETE"
        ),
    }

    # Missing look-through is localized to SOXX restore (PR #61); all other
    # globally required gaps remain fail-closed for the complete daily packet.
    if p["lookthrough_current"] is not True:
        next_conditions.append("Current-quarter look-through check becomes valid before SOXX restore.")
    if p["contribution"] is None:
        next_conditions.append("Cash-transaction activity becomes available; do not substitute zero contribution.")
    if alert_result is None or alert_result["status"] != "PASS":
        next_conditions.append("Authoritative alert inventory matches the expected drawdown pointer.")
    if blockers:
        next_conditions.append("All task-required broker inputs and controls reconcile successfully.")

    calculations = {
        "gap_spym": state["gap_spym"] if state else None,
        "gap_qqqm": state["gap_qqqm"] if state else None,
        "routine_dca": result["d"] if result else None,
        "strategic": result["b"] if result else None,
        "drawdown_deployment": result["dd_amount"] if result else None,
        "soxx_restore": result["restore"] if result and channel_status["soxx_restore"] == "PASS" else None,
        "consumed_tiers": tuple(result["consumed"]) if result else (),
    }
    eligible: tuple[dict[str, Any], ...] = ()
    if not blockers and result:
        specs = (
            ("SPYM", "Core routine/drawdown", result["d_spym"] + result["b_spym"] + result["dd_spym"]),
            ("QQQM", "Core routine/drawdown", result["d_qqqm"] + result["b_qqqm"] + result["dd_qqqm"]),
            ("SOXX", "restore", result["restore"] if channel_status["soxx_restore"] == "PASS" else 0.0),
        )
        eligible = tuple(
            {"name": symbol, "channel": channel, "amount": amount, "nav_weight": amount / nav}
            for symbol, channel, amount in specs if amount > 1e-8
        )

    runtime_status = "DATA INCOMPLETE" if blockers else "PASS"
    decision = "DATA INCOMPLETE" if blockers else ("BUY CANDIDATE" if eligible else "HOLD")
    packet = DecisionPacket(
        schema_version=2,
        workflow="daily-review",
        as_of=p["as_of"],
        runtime_status=runtime_status,
        decision=decision,
        facts={
            "universe": UNIVERSE,
            "nav": nav,
            "cash": cash,
            "positions": positions,
            "out_of_universe": other,
            "open_order_count": len(p["open_orders"]) if p["open_orders"] is not None else None,
            "live_last": {symbol: market[symbol]["live_last"]["value"] for symbol in UNIVERSE} if market else None,
            "spym_last_completed_close": market.get("SPYM", {}).get("last_completed_close") if market else None,
            "drawdown": p["drawdown"],
            "alert_pointer": alert_result,
            "reconciliation_weight": reconciliation,
        },
        calculations=calculations,
        source_status=statuses,
        channel_status=channel_status,
        eligible_channels=eligible,
        blocking_issues=tuple(dict.fromkeys(blockers)),
        attention_items=tuple(dict.fromkeys(attention)),
        next_conditions=tuple(dict.fromkeys(next_conditions)),
        execution_authority="NONE" if decision in {"HOLD", "DATA INCOMPLETE"} else "OWNER AUTHORIZATION REQUIRED",
    )
    packet.validate()
    return packet


def _pct(value: Any) -> str:
    return "N/A" if value is None else f"{value:.2%}"


def _weight(amount: Any, nav: Any) -> str:
    return "N/A" if amount is None or nav in (None, 0) else _pct(amount / nav)


def render_packet(packet: DecisionPacket) -> str:
    packet.validate()
    facts, calc = packet.facts, packet.calculations
    nav, positions = facts["nav"], facts["positions"] or {}
    lines = [
        "# Investment OS — Daily Brief", f"As of: {packet.as_of}", "",
        "## 1. Executive Summary", f"- Decision Status: **{packet.decision}**",
        "- Production universe: SPYM / QQQM / SOXX only.",
        f"- SPYM completed-close drawdown: {_pct(facts['drawdown'])}.",
        f"- Open orders: {facts['open_order_count'] if facts['open_order_count'] is not None else 'N/A'}.", "",
        "## 2. Account Health",
    ]
    lines.extend(f"- {name}: {entry['status']} ({entry.get('source') or 'no authoritative source'})" for name, entry in packet.source_status.items())
    lines.extend([
        f"- Reconciliation difference: {_pct(facts['reconciliation_weight'])} of NAV.",
        f"- Status: {packet.runtime_status}", "", "## 3. Portfolio State",
        f"- Cash: {_weight(facts['cash'], nav)}",
        f"- SPYM: {_weight(positions.get('SPYM'), nav)} | positive gap {_weight(calc['gap_spym'], nav)}",
        f"- QQQM: {_weight(positions.get('QQQM'), nav)} | positive gap {_weight(calc['gap_qqqm'], nav)}",
        f"- SOXX: {_weight(positions.get('SOXX'), nav)} | execution cap 3% | hard cap 6%",
        "- Out-of-Universe: " + (", ".join(facts["out_of_universe"]) + "（只披露，不产生新增候选）" if facts["out_of_universe"] else "None"),
        "", "## 4. Channel Status",
    ])
    lines.extend(f"- {name}: {status}; amount {_weight(calc.get(name), nav)} of NAV." for name, status in packet.channel_status.items())
    lines.extend(["", "## 5. What Is Allowed Today"])
    if packet.decision == "DATA INCOMPLETE":
        lines.append("- DATA INCOMPLETE：停止新的购买候选。")
    elif packet.eligible_channels:
        lines.extend(
            f"- BUY CANDIDATE — {item['name']}：{item['channel']}，授权上限约 {_pct(item['nav_weight'])} of NAV；仍须所有者确认。"
            for item in packet.eligible_channels
        )
    else:
        lines.append("- HOLD：没有标的获得新的购买授权。")
    lines.extend([
        "", "## 6. Why Not the Others",
        "- Other securities remain outside the closed Production universe.",
        "", "## 7. Attention Items",
    ])
    lines.extend([f"- {item}" for item in packet.attention_items] or ["- None."])
    lines.extend(f"- Blocking: {item}" for item in packet.blocking_issues)
    lines.extend(["", "## 8. Next Observation Conditions"])
    lines.extend([f"- {item}" for item in packet.next_conditions] or ["- None."])
    lines.extend(["", "## 9. Execution Boundary", f"Execution authority: {packet.execution_authority}. This renderer cannot place or format an order."])
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
    observed = "2030-01-15T20:00:00+00:00"
    available = {"status": "available", "source": "synthetic-adapter", "observed_at": observed}
    statuses = {name: dict(available) for name in SOURCE_VALUE_FIELDS}
    return {
        "as_of": "2030-01-15", "input_status": statuses,
        "nav": 100000.0, "cash": 17000.0,
        "positions": {"SPYM": 48000.0, "QQQM": 29000.0, "SOXX": 6000.0},
        "open_orders": [], "contribution": 1000.0,
        "market_inputs": {
            "SPYM": {"live_last": {"value": 89.0}, "last_completed_close": {"value": 88.0, "source_as_of": "2030-01-14"}, "ath_close": {"value": 100.0, "source_as_of": "2029-12-20"}},
            "QQQM": {"live_last": {"value": 50.0}},
            "SOXX": {"live_last": {"value": 40.0}},
        },
        "tiers_executed": [],
        "alerts": [{"id": "synthetic", "symbol": "SPYM", "field": "LAST", "operator": "LTE", "price": 90.0, "enabled": True}],
        "lookthrough_current": True, "standing_automations": [],
    }


def self_test() -> None:
    packet = build_packet(synthetic_payload())
    assert packet.decision == "BUY CANDIDATE"
    assert packet.facts["drawdown"] == 0.12
    incomplete = synthetic_payload()
    incomplete["input_status"]["cash_transactions"] = {"status": "unavailable", "reason": "connector gap"}
    incomplete["contribution"] = None
    blocked = build_packet(incomplete)
    assert blocked.decision == "DATA INCOMPLETE" and not blocked.eligible_channels
    assert blocked.calculations["routine_dca"] is None
    outside = synthetic_payload()
    outside["standing_automations"] = [{"type": "DRIP", "symbol": "SPY", "enabled": True}]
    assert build_packet(outside).decision == "DATA INCOMPLETE"
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
        print(f"\nInput protocol error: {exc}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
