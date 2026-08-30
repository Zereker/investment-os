#!/usr/bin/env python3
"""Validate the broker-side drawdown alert pointer against current cycle state.

This script is a deterministic reliability check, not a broker connector and not
an order/alert mutation tool. It reads normalized runtime JSON from stdin and
prints the expected pointer, actual pointer and a fail-closed status. It never
writes account state to disk.

Required JSON fields:
  ath_close: positive number
  tiers_executed: ordered or unordered list containing current-cycle tier names
  alert_inventory_status: available / unavailable / stale / conflicting

When alert_inventory_status is available, `alerts` must be a list of normalized
active drawdown alerts. An empty list then means an authoritative successful read,
not an unavailable capability.

Each alert object must contain:
  symbol, field, operator, price, enabled

The tier schedule is imported from monthly_execution.py so this validator cannot
silently become a second policy source.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from typing import Any

from monthly_execution import LADDERS, TIERS, TIER_NAMES  # noqa: E402


class InputError(ValueError):
    pass


def number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise InputError(f"{name} must be finite")
    return result


def expected_pointer(ticker: str, ath_close: float,
                     tiers_executed: set[str]) -> dict[str, Any] | None:
    """Next available tier and price for ONE ticker, or None when it is spent."""
    for t, trigger, name, _w in TIERS:
        if t == ticker and name not in tiers_executed:
            return {
                "ticker": ticker,
                "tier": name,
                "trigger": trigger,
                "price": round((1.0 - trigger) * ath_close, 2),
            }
    return None


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    missing = sorted({"cycles", "alert_inventory_status"} - payload.keys())
    if missing:
        raise InputError("missing fields: " + ", ".join(missing))

    raw_cycles = payload["cycles"]
    if not isinstance(raw_cycles, dict):
        raise InputError("cycles must be an object keyed by ticker")
    # Every laddered ticker must be present. A ticker silently absent would be
    # read as "no alert expected", which is exactly the state a missing series
    # must NOT be allowed to imitate.
    absent = sorted(set(LADDERS) - set(raw_cycles))
    if absent:
        raise InputError("cycles missing tickers: " + ", ".join(absent))
    unknown = sorted(set(raw_cycles) - set(LADDERS))
    if unknown:
        raise InputError("cycles has tickers with no ladder: " + ", ".join(unknown))

    cycles = {}
    for ticker, raw in raw_cycles.items():
        if not isinstance(raw, dict):
            raise InputError(f"cycles.{ticker} must be an object")
        for field in ("ath_close", "tiers_executed"):
            if field not in raw:
                raise InputError(f"cycles.{ticker} missing {field}")
        ath = number(raw["ath_close"], f"cycles.{ticker}.ath_close")
        if ath <= 0:
            raise InputError(f"cycles.{ticker}.ath_close must be positive")
        tiers_raw = raw["tiers_executed"]
        if not isinstance(tiers_raw, list) or any(t not in TIER_NAMES for t in tiers_raw):
            raise InputError(f"cycles.{ticker}.tiers_executed contains an unknown tier")
        cycles[ticker] = {"ath_close": ath, "tiers_executed": set(tiers_raw)}

    inventory_status = str(payload["alert_inventory_status"]).lower()
    if inventory_status not in {"available", "unavailable", "stale", "conflicting"}:
        raise InputError("alert_inventory_status is invalid")
    if inventory_status != "available":
        if payload.get("alerts") in ([], {}):
            raise InputError(
                "unavailable alert inventory must not be represented as an empty collection"
            )
        return {
            "cycles": cycles,
            "alert_inventory_status": inventory_status,
            "alerts": None,
        }

    if "alerts" not in payload:
        raise InputError("available alert inventory requires alerts")
    alerts_raw = payload["alerts"]
    if not isinstance(alerts_raw, list):
        raise InputError("alerts must be a list")

    alerts = []
    for index, raw in enumerate(alerts_raw):
        if not isinstance(raw, dict):
            raise InputError(f"alerts[{index}] must be an object")
        required = {"symbol", "field", "operator", "price", "enabled"}
        absent = sorted(required - raw.keys())
        if absent:
            raise InputError(f"alerts[{index}] missing fields: " + ", ".join(absent))
        alerts.append({
            "symbol": str(raw["symbol"]).upper(),
            "field": str(raw["field"]).upper(),
            "operator": str(raw["operator"]).upper(),
            "price": number(raw["price"], f"alerts[{index}].price"),
            "enabled": bool(raw["enabled"]),
            "id": str(raw.get("id", "N/A")),
        })

    return {
        "cycles": cycles,
        "alert_inventory_status": inventory_status,
        "alerts": alerts,
    }


def check(payload: dict[str, Any], tolerance: float = 0.011) -> dict[str, Any]:
    """One pointer per laddered ticker: each unspent ladder needs exactly one
    active alert at its own next tier, and a spent one needs none."""
    state = validate(payload)
    expected = {t: expected_pointer(t, c["ath_close"], c["tiers_executed"])
                for t, c in state["cycles"].items()}
    if state["alert_inventory_status"] != "available":
        return {
            "status": "DATA INCOMPLETE",
            "expected": expected,
            "actual": None,
            "inventory_status": state["alert_inventory_status"],
            "issues": [
                f"alert inventory is {state['alert_inventory_status']}; pointers not verified"
            ],
        }
    active = [a for a in state["alerts"] if a["enabled"]]
    issues: list[str] = []

    for ticker in sorted(LADDERS):
        want = expected[ticker]
        mine = [a for a in active if a["symbol"] == ticker.upper()]
        if want is None:
            if mine:
                issues.append(
                    f"{ticker.upper()} ladder is exhausted but an active alert still exists")
            continue
        if len(mine) != 1:
            issues.append(
                f"{ticker.upper()}: expected exactly one active drawdown alert, found {len(mine)}")
            continue
        alert = mine[0]
        if alert["field"] != "LAST":
            issues.append(f"{ticker.upper()} alert field is not LAST")
        if alert["operator"] not in {"LTE", "<=", "LESS_THAN_OR_EQUAL"}:
            issues.append(f"{ticker.upper()} alert operator is not less-than-or-equal")
        if abs(alert["price"] - want["price"]) > tolerance:
            issues.append(
                f"{ticker.upper()} pointer mismatch: expected {want['tier']} at "
                f"{want['price']:.2f}, actual price {alert['price']:.2f}")

    # An alert on a symbol that carries no ladder is not a drawdown pointer and
    # must be reported rather than ignored: it may be someone else's automation.
    stray = sorted({a["symbol"] for a in active} - {t.upper() for t in LADDERS})
    if stray:
        issues.append("active alerts on symbols with no ladder: " + ", ".join(stray))

    return {
        "status": "PASS" if not issues else "WARN",
        "expected": expected,
        "actual": active,
        "inventory_status": "available",
        "issues": issues,
    }


def render(result: dict[str, Any]) -> str:
    lines = ["# Drawdown Alert Pointer Check", f"Status: **{result['status']}**"]
    for ticker in sorted(result["expected"]):
        want = result["expected"][ticker]
        if want is None:
            lines.append(f"Expected {ticker.upper()}: no active alert; ladder exhausted.")
        else:
            lines.append(
                f"Expected {ticker.upper()}: {want['tier']} at {want['price']:.2f}.")
    if result["actual"] is None:
        lines.append(f"Actual: alert inventory {result['inventory_status']}.")
    elif result["actual"]:
        for alert in result["actual"]:
            lines.append(
                f"Actual: id={alert['id']} {alert['symbol']} {alert['field']} "
                f"{alert['operator']} {alert['price']:.2f}."
            )
    else:
        lines.append("Actual: no active alert.")
    if result["issues"]:
        lines.append("Decision: drawdown deployment state is DATA INCOMPLETE; stop new drawdown candidates.")
        lines.extend(f"- {issue}" for issue in result["issues"])
    else:
        lines.append("Decision: alert pointer invariant satisfied.")
    return "\n".join(lines)


def self_test() -> None:
    def alert(symbol, price, **kw):
        return {"id": f"synthetic-{symbol}", "symbol": symbol, "field": "LAST",
                "operator": "LTE", "price": price, "enabled": True, **kw}

    # every ladder at cycle start: one alert each, at that ticker's own T1
    cycles = {t: {"ath_close": 100.0, "tiers_executed": []} for t in LADDERS}
    alerts = [alert(t.upper(), 90.0) for t in LADDERS]
    base = {"cycles": cycles, "alert_inventory_status": "available", "alerts": alerts}
    if check(base)["status"] != "PASS":
        raise AssertionError("first-tier pointers should pass")

    # each ticker is judged against ITS OWN high: a shared price is wrong
    own_highs = {
        "cycles": {t: {"ath_close": h, "tiers_executed": []}
                   for t, h in zip(sorted(LADDERS), (100.0, 200.0, 400.0))},
        "alert_inventory_status": "available",
        "alerts": [alert(t.upper(), h * 0.9)
                   for t, h in zip(sorted(LADDERS), (100.0, 200.0, 400.0))],
    }
    if check(own_highs)["status"] != "PASS":
        raise AssertionError("per-ticker highs should each drive their own pointer")

    # one ticker's pointer left on a spent tier is caught, and named
    one_stale = {**base, "alerts": [alert(t.upper(), 85.0 if t == "spym" else 90.0)
                                    for t in LADDERS]}
    result = check(one_stale)
    if result["status"] != "WARN" or not any(
            "SPYM pointer mismatch" in i for i in result["issues"]):
        raise AssertionError("a stale pointer on one ticker was not detected")

    # a missing pointer on one ticker must not be masked by the other two
    one_missing = {**base, "alerts": [a for a in alerts if a["symbol"] != "QQQM"]}
    result = check(one_missing)
    if result["status"] != "WARN" or not any(
            "QQQM: expected exactly one" in i for i in result["issues"]):
        raise AssertionError("a missing pointer was not detected")

    after_first = {
        "cycles": {t: {"ath_close": 100.0,
                       "tiers_executed": ["T1"] if t == "spym" else []}
                   for t in LADDERS},
        "alert_inventory_status": "available",
        "alerts": [alert(t.upper(), 85.0 if t == "spym" else 90.0) for t in LADDERS],
    }
    if check(after_first)["status"] != "PASS":
        raise AssertionError("second-tier pointer should pass after the first executes")

    duplicate = {**base, "alerts": alerts + [alert("SPYM", 90.0)]}
    if check(duplicate)["status"] != "WARN":
        raise AssertionError("duplicate alerts were not detected")

    exhausted = {
        "cycles": {t: {"ath_close": 100.0, "tiers_executed": list(TIER_NAMES)}
                   for t in LADDERS},
        "alert_inventory_status": "available",
        "alerts": [],
    }
    if check(exhausted)["status"] != "PASS":
        raise AssertionError("exhausted ladders should require no alert")

    # an alert on a symbol with no ladder is someone else's automation, not a
    # pointer — reported, never silently ignored
    stray = {**base, "alerts": alerts + [alert("AAPL", 100.0)]}
    result = check(stray)
    if result["status"] != "WARN" or not any("AAPL" in i for i in result["issues"]):
        raise AssertionError("a stray alert was not reported")

    # a ticker silently absent from cycles must not read as "no alert expected"
    for bad in ({t: cycles[t] for t in list(LADDERS)[:-1]},
                {**cycles, "aapl": {"ath_close": 100.0, "tiers_executed": []}}):
        try:
            check({**base, "cycles": bad})
        except InputError:
            pass
        else:
            raise AssertionError(f"malformed cycles accepted: {sorted(bad)}")

    unavailable = {"cycles": cycles, "alert_inventory_status": "unavailable", "alerts": None}
    if check(unavailable)["status"] != "DATA INCOMPLETE":
        raise AssertionError("unavailable alert inventory must fail closed")

    disguised = {**unavailable, "alerts": []}
    try:
        check(disguised)
    except InputError:
        pass
    else:
        raise AssertionError("unavailable alert inventory was allowed to masquerade as empty")

    print("alert pointer self-test: PASS")


USAGE_EPILOG = """\
The check reads one JSON object on stdin — there are no input flags. Every
laddered ticker carries its OWN all-time-high close, its own cycle and its own
pointer, so every one of them must appear under "cycles":

  {"cycles": {
     "spym": {"ath_close": 91.56,  "tiers_executed": []},      # [] = cycle reset
     "qqqm": {"ath_close": 303.96, "tiers_executed": []},
     "soxx": {"ath_close": 655.01, "tiers_executed": ["T1"]}},
   "alert_inventory_status": "available",    # available|unavailable|stale|conflicting
   "alerts": [{"symbol": "SPYM", "field": "LAST", "operator": "LTE",
               "price": 82.40, "enabled": true, "id": "..."}]}

A ticker omitted from "cycles" is refused rather than read as "no alert
expected" — that is precisely the state a missing series must not imitate.

An inventory that is not "available" must omit alerts rather than send an empty
list: "the broker did not answer" and "the broker answered, nothing is set" are
different states and only the second is a fact.

  python3 alert_pointer_check.py < pointer.json
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        epilog=USAGE_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    try:
        payload = json.load(sys.stdin)
        print(render(check(payload)))
    except (InputError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print("# Drawdown Alert Pointer Check")
        print("Status: **DATA INCOMPLETE**")
        print(f"Input error: {exc}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
