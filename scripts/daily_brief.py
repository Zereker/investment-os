#!/usr/bin/env python3
"""Render the v6 three-ETF Daily Brief from normalized runtime JSON on stdin.

This is an orchestration boundary, not a broker connector and not a new strategy.
It accepts ephemeral account state, validates the closed Production universe,
reuses monthly_execution.compute for all funding math, and prints a deterministic
brief. It never writes inputs or output to disk and never places an order.

Usage:
  cat /trusted/runtime-state.json | python3 scripts/daily_brief.py
  python3 scripts/daily_brief.py --self-test

Required JSON fields:
  as_of, nav, cash, positions, contribution, drawdown,
  tiers_executed, lookthrough_current, account_inputs, open_orders

`positions` is a mapping of symbol to current market value. SPYM, QQQM and SOXX
are the only Production purchase symbols. Other symbols are reported as
Out-of-Universe and never become purchase candidates.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
from contextlib import redirect_stdout
from datetime import date
from typing import Any

from monthly_execution import compute, TIERS

UNIVERSE = ("SPYM", "QQQM", "SOXX")
REQUIRED_ACCOUNT_INPUTS = (
    "account_summary",
    "balances",
    "positions",
    "open_orders",
)


class InputError(ValueError):
    pass


def number(value: Any, name: str, *, nonnegative: bool = True) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value):
        raise InputError(f"{name} must be finite")
    if nonnegative and value < 0:
        raise InputError(f"{name} must be nonnegative")
    return value


def validate(payload: dict[str, Any]) -> dict[str, Any]:
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
    dd = number(payload["drawdown"], "drawdown")
    if dd > 1:
        raise InputError("drawdown must be between 0 and 1")

    positions_raw = payload["positions"]
    if not isinstance(positions_raw, dict):
        raise InputError("positions must be an object")
    positions = {str(k).upper(): number(v, f"positions.{k}") for k, v in positions_raw.items()}

    account_inputs = payload["account_inputs"]
    if not isinstance(account_inputs, dict):
        raise InputError("account_inputs must be an object")
    input_status = {name: bool(account_inputs.get(name, False)) for name in REQUIRED_ACCOUNT_INPUTS}

    tiers = payload["tiers_executed"]
    if not isinstance(tiers, list) or any(t not in {row[1] for row in TIERS} for t in tiers):
        raise InputError("tiers_executed must be a list containing only T1/T2/T3/T4")

    orders = payload["open_orders"]
    if not isinstance(orders, list):
        raise InputError("open_orders must be a list")

    return {
        **payload,
        "nav": nav,
        "cash": cash,
        "contribution": contribution,
        "drawdown": dd,
        "positions": positions,
        "account_inputs": input_status,
        "tiers_executed": set(tiers),
        "lookthrough_current": bool(payload["lookthrough_current"]),
        "open_orders": orders,
    }


def pct(value: float) -> str:
    return f"{value:.2%}"


def candidate_lines(result: dict[str, Any], data_complete: bool) -> list[str]:
    if not data_complete:
        return ["- DATA INCOMPLETE：停止新的购买候选。"]
    candidates: list[str] = []
    flows = (
        ("SPYM", result["d_spym"] + result["b_spym"] + result["dd_spym"], "Core 例行/回撤通道"),
        ("QQQM", result["d_qqqm"] + result["b_qqqm"] + result["dd_qqqm"], "Core 例行/回撤通道"),
        ("SOXX", result["restore"], "SOXX 回补至目标通道"),
    )
    nav = result["nav"]
    for symbol, amount, channel in flows:
        if amount > 1e-8:
            candidates.append(
                f"- BUY CANDIDATE — {symbol}：{channel}，授权上限约 {pct(amount / nav)} of NAV；仍须人工确认。"
            )
    return candidates or ["- HOLD：没有标的获得新的购买授权。"]


def render(payload: dict[str, Any]) -> str:
    p = validate(payload)
    nav = p["nav"]
    positions = p["positions"]
    spym = positions.get("SPYM", 0.0)
    qqqm = positions.get("QQQM", 0.0)
    soxx = positions.get("SOXX", 0.0)
    other = {k: v for k, v in positions.items() if k not in UNIVERSE}

    data_complete = all(p["account_inputs"].values())
    reconciliation = abs((p["cash"] + sum(positions.values())) - nav) / nav
    if reconciliation > 0.005:
        data_complete = False

    result = compute(
        nav, p["cash"], spym, qqqm, soxx, p["contribution"],
        p["drawdown"], p["tiers_executed"], date.fromisoformat(str(p["as_of"])[:10]),
        p["lookthrough_current"],
    )
    result["nav"] = nav

    input_text = ", ".join(
        f"{name}={'PASS' if ok else 'FAIL'}" for name, ok in p["account_inputs"].items()
    )
    next_tier = next((name for trigger, name, _ in TIERS if p["drawdown"] < trigger), None)
    next_trigger = next((trigger for trigger, _, _ in TIERS if p["drawdown"] < trigger), None)

    decision = "DATA INCOMPLETE" if not data_complete else (
        "BUY CANDIDATE" if any(
            result[key] > 1e-8 for key in ("d", "b", "dd_amount", "restore")
        ) else "HOLD"
    )

    lines = [
        "# Investment OS — Daily Brief",
        f"As of: {p['as_of']}",
        "",
        "## 1. Executive Summary",
        f"- Decision Status: **{decision}**",
        f"- Production universe: SPYM / QQQM / SOXX only.",
        f"- SPYM drawdown: {pct(p['drawdown'])}.",
        f"- Open orders: {len(p['open_orders'])}.",
        "",
        "## 2. Account Health",
        f"- Inputs: {input_text}",
        f"- Reconciliation difference: {pct(reconciliation)} of NAV.",
        f"- Status: {'PASS' if data_complete else 'DATA INCOMPLETE'}",
        "",
        "## 3. Portfolio State",
        f"- Cash: {pct(p['cash'] / nav)}",
        f"- SPYM: {pct(spym / nav)} | positive gap {pct(result['gap_spym'] / nav)}",
        f"- QQQM: {pct(qqqm / nav)} | positive gap {pct(result['gap_qqqm'] / nav)}",
        f"- SOXX: {pct(soxx / nav)} | execution cap 3% | hard cap 6%",
    ]
    if other:
        lines.append("- Out-of-Universe: " + ", ".join(sorted(other)) + "（只披露，不产生新增候选）")
    else:
        lines.append("- Out-of-Universe: None")

    lines.extend([
        "",
        "## 4. What the Rules Mean",
        f"- Monthly contribution channel: {pct(result['d'] / nav)} of NAV authorized.",
        f"- Strategic cash migration channel: {pct(result['b'] / nav)} of NAV authorized.",
        f"- Drawdown channel: {pct(result['dd_amount'] / nav)} of NAV authorized; newly consumed tiers: {', '.join(result['consumed']) or 'None'}.",
        f"- SOXX restore channel: {pct(result['restore'] / nav)} of NAV authorized.",
        "",
        "## 5. What Is Allowed Today",
        *candidate_lines(result, data_complete),
        "",
        "## 6. Why Not the Others",
        f"- SPYM: {'eligible only through its positive Core gap' if result['gap_spym'] > 0 else 'no positive Core gap'}.",
        f"- QQQM: {'eligible only through its positive Core gap' if result['gap_qqqm'] > 0 else 'no positive Core gap'}.",
        f"- SOXX: {'restore candidate exists' if result['restore'] > 0 else 'no authorized restore; raising the execution cap still requires full IC'}.",
        "- Other securities: outside the closed Production universe.",
        "",
        "## 7. Attention Items",
    ])
    attention = []
    if not data_complete:
        attention.append("- Restore missing or conflicting account data before considering any new action.")
    if other:
        attention.append("- Review Out-of-Universe holdings under Legacy/exception rules; do not add.")
    if p["open_orders"]:
        attention.append("- Resolve duplicate, conflicting or stale open orders before new action.")
    lines.extend(attention or ["- None."])

    lines.extend(["", "## 8. Next Observation Conditions"])
    if next_tier is not None and next_trigger is not None:
        lines.append(f"- SPYM reaches {next_tier} at {pct(next_trigger)} drawdown.")
    else:
        lines.append("- Drawdown ladder is fully triggered; no deeper tier exists.")
    if p["contribution"] <= 0:
        lines.append("- Monthly contribution arrives and is confirmed in IBKR.")
    if not p["lookthrough_current"]:
        lines.append("- Current-quarter look-through check becomes valid before any SOXX restore.")
    if not data_complete:
        lines.append("- All four IBKR inputs reconcile successfully.")

    lines.extend([
        "",
        "## 9. Human Boundary",
        "This brief does not place or format an order. Any BUY CANDIDATE requires a fresh IBKR check and manual confirmation.",
    ])
    return "\n".join(lines)


def self_test() -> None:
    synthetic = {
        "as_of": "2030-01-15",
        "nav": 100000.0,
        "cash": 17000.0,
        "positions": {"SPYM": 48000.0, "QQQM": 29000.0, "SOXX": 6000.0},
        "contribution": 1000.0,
        "drawdown": 0.12,
        "tiers_executed": [],
        "lookthrough_current": True,
        "account_inputs": {name: True for name in REQUIRED_ACCOUNT_INPUTS},
        "open_orders": [],
    }
    output = render(synthetic)
    required = (
        "Daily Brief", "SPYM / QQQM / SOXX only", "Why Not the Others",
        "Human Boundary", "BUY CANDIDATE",
    )
    for text in required:
        if text not in output:
            raise AssertionError(f"missing Daily Brief invariant: {text}")

    incomplete = dict(synthetic)
    incomplete["account_inputs"] = {**synthetic["account_inputs"], "positions": False}
    if "Decision Status: **DATA INCOMPLETE**" not in render(incomplete):
        raise AssertionError("missing-data case did not fail closed")

    outside = dict(synthetic)
    outside["positions"] = {**synthetic["positions"], "SYNTHETIC_X": 100.0}
    outside["nav"] = 100100.0
    text = render(outside)
    if "Out-of-Universe: SYNTHETIC_X" not in text or "BUY CANDIDATE — SYNTHETIC_X" in text:
        raise AssertionError("closed universe invariant failed")

    print("daily brief self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    try:
        payload = json.load(sys.stdin)
        print(render(payload))
    except (InputError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print("# Investment OS — Daily Brief")
        print("\nDecision Status: **DATA INCOMPLETE**")
        print(f"\nInput error: {exc}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
