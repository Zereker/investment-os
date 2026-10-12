"""Stateless, dependency-free Investment OS checks. JSON on stdin, JSON on stdout.

This program neither fetches broker data nor authorizes or executes orders.
Only fresh authoritative connector observations may be supplied in production.
"""
import datetime as dt
import json
import math
import sys

TARGETS = {"SPYM": .50, "QQQM": .30, "SOXX": .05}
ACCOUNT = ("account_summary", "balances", "positions", "open_orders")
MONTHLY = ACCOUNT + ("market_inputs",)


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed


def check(payload, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    task = payload.get("task", "account")
    if task not in ("account", "monthly"):
        raise ValueError("task must be account or monthly")
    observations = payload.get("capabilities", {})
    required = MONTHLY if task == "monthly" else ACCOUNT
    issues, data, observed = [], {}, []
    for name in required:
        item = observations.get(name, {})
        if item.get("status") != "available":
            issues.append(f"{name}: {item.get('status', 'unavailable')}")
            continue
        if item.get("source") != "IBKR" or item.get("data") is None:
            issues.append(f"{name}: authoritative IBKR data required")
            continue
        try:
            at = timestamp(item["observed_at"])
            age = (now - at).total_seconds()
            if age < -5 or age > 300:
                raise ValueError("observation outside fresh runtime window")
            observed.append(at)
            data[name] = item["data"]
        except (KeyError, TypeError, ValueError):
            issues.append(f"{name}: missing, invalid or stale observed_at")
    if observed and (max(observed) - min(observed)).total_seconds() > 300:
        issues.append("observations do not form a coherent runtime window")

    summary = data.get("account_summary", {})
    nav = summary.get("net_liquidation")
    currency = summary.get("currency")
    if currency != "USD" or not numeric(nav) or nav <= 0:
        issues.append("positive USD account NAV required")
        nav = None
    rows = data.get("balances", {}).get("balances")
    cash = usd_cash = None
    if isinstance(rows, list):
        base = [r for r in rows if r.get("currency") == "BASE"]
        usd = [r for r in rows if r.get("currency") == "USD"]
        if len(base) == 1 and numeric(base[0].get("cash_balance")):
            cash = base[0]["cash_balance"]
        if len(usd) == 1 and numeric(usd[0].get("cash_balance")):
            settled = usd[0].get("settled_cash")
            if numeric(settled) and settled >= 0:
                usd_cash = min(usd[0]["cash_balance"], settled)
    if cash is None or usd_cash is None:
        issues.append("unique BASE aggregate and USD cash rows required")
    if isinstance(rows, list) and any(numeric(r.get("cash_balance")) and r["cash_balance"] < 0 for r in rows):
        issues.append("negative currency cash balance: borrowing prohibited")

    positions = data.get("positions", {}).get("positions")
    values, holdings, legacy, contracts = [], {}, 0, set()
    if not isinstance(positions, list):
        issues.append("positions envelope required")
        positions = None
    else:
        for p in positions:
            value, quantity = p.get("market_value"), p.get("position")
            cid, symbol = p.get("contract_id"), p.get("contract_description")
            if not numeric(value) or value < 0 or p.get("currency") != "USD" or not numeric(quantity) or quantity <= 0:
                issues.append("invalid, short, zero or non-USD position")
                continue
            if cid is None or cid in contracts:
                issues.append("missing or duplicate position contract")
            contracts.add(cid)
            values.append(value)
            if symbol in TARGETS:
                holdings[symbol] = holdings.get(symbol, 0) + value
            else:
                legacy += value

    reconciliation = None
    if nav is not None and cash is not None and positions is not None and len(values) == len(positions):
        total = cash + sum(values)
        difference = abs(total - nav)
        reconciliation = dict(nav=nav, cash=cash, positions_market_value=sum(values),
                              component_total=total, absolute_difference=difference,
                              relative_difference=difference / nav, tolerance=.005,
                              status="PASS" if difference / nav <= .005 else "DATA INCOMPLETE")
        if difference / nav > .005:
            issues.append("NAV reconciliation exceeds 0.5% tolerance")

    orders = data.get("open_orders", {}).get("orders")
    order_status = "clear" if orders == [] else "conflicting" if isinstance(orders, list) else "unknown"
    if order_status != "clear":
        issues.append(f"open orders: {order_status}")

    report = dict(status="DATA INCOMPLETE" if issues else "PASS", blocking_issues=issues,
                  reconciliation=reconciliation, open_orders_status=order_status,
                  balances_by_currency=rows, base_currency=currency,
                  selected_balance_label="BASE" if cash is not None else None,
                  selection_reason="BASE for reconciliation; USD only for deployment",
                  deployment=None, execution_authorized=False, runtime_data_persisted=False)
    if nav and positions is not None and len(values) == len(positions):
        report["weights"] = {t: holdings.get(t, 0) / nav for t in TARGETS}
        report["legacy"] = {"market_value": legacy, "weight": legacy / nav}
        report["usd_cash_weight"] = usd_cash / nav if usd_cash is not None else None
    if task == "account":
        return report

    # Monthly gates must finish before any funding formula is evaluated.
    schedule = payload.get("schedule", {})
    if schedule.get("source") != "NYSE" or schedule.get("monthly_execution_date") != now.date().isoformat():
        issues.append("not a verified fixed monthly execution date; no catch-up")
    if schedule.get("calculation_already_run") is not False:
        issues.append("monthly calculation lifecycle is unknown or already run")
    market = data.get("market_inputs", {})
    for ticker in ("SPYM", "QQQM"):
        item = market.get(ticker, {})
        dd, tiers = item.get("drawdown"), item.get("tiers_executed")
        try:
            as_of = dt.date.fromisoformat(item["close_as_of"])
            valid_date = 0 <= (now.date() - as_of).days <= 7
        except (KeyError, TypeError, ValueError):
            valid_date = False
        if not numeric(dd) or not 0 <= dd < 1 or not valid_date:
            issues.append(f"{ticker}: verified fresh closing drawdown required")
        if not isinstance(tiers, list) or any(t not in ("T1", "T2", "T3", "T4") for t in tiers) or len(set(tiers)) != len(tiers):
            issues.append(f"{ticker}: verified cycle tier state required")
    report["status"] = "DATA INCOMPLETE" if issues else "PASS"
    if issues:
        return report

    gaps = {t: max(TARGETS[t] * nav - holdings.get(t, 0), 0) for t in TARGETS}
    remaining = gaps.copy()

    def allocate(amount):
        allocation = dict.fromkeys(TARGETS, 0)
        for t in sorted(TARGETS, key=lambda t: (-remaining[t], t)):
            allocation[t] = min(amount, remaining[t])
            remaining[t] -= allocation[t]
            amount -= allocation[t]
        return allocation

    c = usd_cash
    surplus = max(c - .15 * nav, 0)
    g = sum(remaining.values())
    b = min(surplus / 3, g)
    baseline = allocate(b)
    cash_left = c - b
    drawdown = dict.fromkeys(TARGETS, 0)
    candidate_tiers = {"SPYM": [], "QQQM": []}
    for t in sorted(("SPYM", "QQQM"), key=lambda t: -market[t]["drawdown"]):
        for index, trigger in enumerate((.10, .15, .20, .25), 1):
            tier = f"T{index}"
            if market[t]["drawdown"] >= trigger and tier not in market[t]["tiers_executed"]:
                amount = min((.09 if t == "SPYM" else .06) * index / 10 * nav, cash_left, remaining[t])
                if amount > 0:
                    drawdown[t] += amount
                    candidate_tiers[t].append(tier)
                    cash_left -= amount
                    remaining[t] -= amount
    report["deployment"] = dict(V=nav, C=c,
                                 R=3, S=surplus, G=g, B=b, gaps=gaps,
                                 baseline_allocation=baseline,
                                 drawdown_allocation=drawdown, candidate_tiers=candidate_tiers,
                                 final_cash=cash_left, note="Candidates only; tiers consumed only after verified fills. Whole shares and commissions require execution checks.")
    return report


def main():
    try:
        result = check(json.load(sys.stdin))
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        result = dict(status="DATA INCOMPLETE", blocking_issues=[f"invalid input: {exc}"],
                      deployment=None, execution_authorized=False, runtime_data_persisted=False)
    print(json.dumps(result, allow_nan=False))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
