"""Stateless, dependency-free Investment OS checks. JSON on stdin, JSON on stdout.

This program neither fetches broker data nor authorizes or executes orders.
Only fresh authoritative connector observations may be supplied in production.
"""
import datetime as dt
import copy
import json
import math
import sys

TARGETS = {"SPYM": .50, "QQQM": .30, "SOXX": .05}
ACCOUNT = ("account_summary", "balances", "positions", "open_orders", "contract_details")
MONTHLY = ACCOUNT + ("cash_transactions",)


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def timestamp(value):
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed


def funding_preparation(rows):
    """Disclosure only: source-currency balances never become deployable USD."""
    result = dict(source_currency="CNH", destination_currency="USD",
                  status="DATA INCOMPLETE", cash_balance=None, settled_cash=None,
                  settled_balance_limit=None, amount_to_convert=None,
                  expected_usd_proceeds=None, execution_authorized=False)
    if not isinstance(rows, list):
        return result
    found = [row for row in rows if isinstance(row, dict) and row.get("currency") == "CNH"]
    if not found:
        result["status"] = "NOT_APPLICABLE"
        return result
    if len(found) != 1:
        return result
    cash, settled = found[0].get("cash_balance"), found[0].get("settled_cash")
    if not numeric(cash) or not numeric(settled) or cash < 0 or settled < 0:
        return result
    limit = min(cash, settled)
    result.update(cash_balance=cash, settled_cash=settled, settled_balance_limit=limit,
                  status="AWAIT_OWNER_REVIEW" if limit > 0 else "WAIT")
    return result


def confirmed_fx_contribution(payload, data, now, issues):
    confirmation = payload.get("funding_confirmation", {})
    if confirmation.get("source_currency") != "CNH" or confirmation.get("confirmed_new_funding") is not True:
        issues.append("explicit CNH new-funding source confirmation required")
    if confirmation.get("allocation_period") != now.strftime("%Y-%m"):
        issues.append("funding allocation period must match monthly review period")
    selected = confirmation.get("trade_ids")
    try:
        ledger = funding_ledger(payload.get("funding_ledger"))
        used = [trade for entry in ledger["entries"] if entry["status"] != "released"
                for trade in entry["trade_ids"]]
    except ValueError as exc:
        issues.append(str(exc))
        used = []
    if not isinstance(selected, list) or not selected or any(not isinstance(x, str) or not x for x in selected):
        issues.append("specific FX fill identifiers required")
        return None
    if len(set(selected)) != len(selected) or set(selected).intersection(used):
        issues.append("FX fills duplicate or already counted")
    evidence = data.get("fx_funding", {})
    trades = evidence.get("trades", [])
    fees = evidence.get("usd_fees_total")
    if not numeric(fees) or fees < 0 or evidence.get("fee_currency_verified") is not True:
        issues.append("verified USD-denominated FX fees required; zero must be explicit")
        return None
    amount = 0
    for trade_id in selected:
        matches = [x for x in trades if x.get("trade_id") == trade_id]
        if len(matches) != 1:
            issues.append("selected FX fill missing or repeated in broker evidence")
            continue
        t = matches[0]
        try:
            at = timestamp(t["trade_time"])
            valid_time = at <= now
        except (KeyError, TypeError, ValueError):
            valid_time = False
        if t.get("sec_type") != "CASH" or t.get("symbol") != "USD" or t.get("currency") != "CNH" or t.get("side") != "BUY" or not numeric(t.get("size")) or t["size"] <= 0 or not valid_time:
            issues.append("selected fill is not a verified completed CNH-to-USD conversion")
            continue
        amount += t["size"]
    if evidence.get("usd_settlement_verified") is not True:
        issues.append("converted USD settlement must be verified from broker evidence")
    if fees > amount:
        issues.append("FX USD fees exceed proceeds")
    return max(amount - fees, 0)


def check(payload, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    task = payload.get("task", "account")
    if task == "funding_ledger":
        return update_funding_ledger(payload)
    if task not in ("account", "monthly", "drawdown"):
        raise ValueError("task must be account, monthly or drawdown")
    observations = payload.get("capabilities", {})
    required = MONTHLY if task == "monthly" else ACCOUNT
    confirmed_path = task == "monthly" and "funding_confirmation" in payload
    if confirmed_path:
        required = ACCOUNT + ("fx_funding",)
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
    details = data.get("contract_details", {}).get("contracts", [])
    values, holdings, legacy, contracts = [], {}, 0, set()
    mapping_complete = True
    if not isinstance(positions, list):
        issues.append("positions envelope required")
        positions = None
    else:
        for p in positions:
            value, quantity = p.get("market_value"), p.get("position")
            cid = p.get("contract_id")
            matches = [c for c in details if c.get("contract_id") == cid]
            symbol = None
            if len(matches) != 1 or not isinstance(matches[0].get("symbol"), str) or not matches[0]["symbol"] or matches[0].get("sec_type") != "STK" or matches[0].get("currency") != p.get("currency"):
                issues.append("unique verified USD stock contract mapping required")
                mapping_complete = False
            else:
                symbol = matches[0]["symbol"]
            if not numeric(value) or value < 0 or p.get("currency") != "USD" or not numeric(quantity) or quantity <= 0:
                issues.append("invalid, short, zero or non-USD position")
                continue
            if cid is None or cid in contracts:
                issues.append("missing or duplicate position contract")
                mapping_complete = False
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
                  deployment=None, funding_preparation=funding_preparation(rows),
                  execution_authorized=False, runtime_data_persisted=False)
    if nav and positions is not None and len(values) == len(positions) and mapping_complete:
        report["weights"] = {t: holdings.get(t, 0) / nav for t in TARGETS}
        report["legacy"] = {"market_value": legacy, "weight": legacy / nav}
        report["usd_cash_weight"] = usd_cash / nav if usd_cash is not None else None
    if task == "account":
        return report
    if task == "drawdown":
        return check_drawdown(payload, now, report, nav, usd_cash, holdings)

    # Monthly gates must finish before any funding formula is evaluated.
    contribution = confirmed_fx_contribution(payload, data, now, issues) if confirmed_path else data.get("cash_transactions", {}).get("external_contribution_usd")
    report["funding_evidence_mode"] = "user_source_confirmation_plus_ibkr_fx" if confirmed_path else "ibkr_cash_transactions"
    if not numeric(contribution) or contribution < 0:
        issues.append("authoritative external net contribution F unavailable or invalid")
    schedule = payload.get("schedule", {})
    if schedule.get("source") != "NYSE" or schedule.get("monthly_execution_date") != now.date().isoformat():
        issues.append("not a verified fixed monthly execution date; no catch-up")
    if schedule.get("calculation_already_run") is not False:
        issues.append("monthly calculation lifecycle is unknown or already run")
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

    g0 = sum(gaps.values())
    dmax = min(contribution, g0)
    d = min(dmax, usd_cash)
    routine = allocate(d)
    c = usd_cash - d
    surplus = max(c - .15 * nav, 0)
    g = sum(remaining.values())
    b = min(surplus / 3, g)
    baseline = allocate(b)
    cash_left = c - b
    report["deployment"] = dict(F=contribution, V=nav, C0=usd_cash, G0=g0, Dmax=dmax, D=d, C=c,
                                 R=3, S=surplus, G=g, B=b, gaps=gaps,
                                 routine_allocation=routine, baseline_allocation=baseline,
                                 final_cash=cash_left, note="Candidates only; tiers consumed only after verified fills. Whole shares and commissions require execution checks.")
    return report


def funding_ledger(value):
    """Validate a private journal; the host must verify history and durable storage."""
    if not isinstance(value, dict) or value.get("schema_version") != 1 or not isinstance(value.get("ledger_id"), str) or not value["ledger_id"] or type(value.get("revision")) is not int or value["revision"] < 0 or value.get("history_scope") != "verified_full_history" or not isinstance(value.get("entries"), list):
        raise ValueError("verified complete private funding ledger required")
    ids, active, recorded_fills = set(), set(), set()
    for entry in value["entries"]:
        trades = entry.get("trade_ids")
        rid = entry.get("reservation_id")
        if not isinstance(rid, str) or not rid or rid in ids or entry.get("status") not in ("reserved", "consumed", "partial", "released") or not isinstance(trades, list) or not trades or any(not isinstance(t, str) or not t for t in trades) or len(trades) != len(set(trades)) or not isinstance(entry.get("allocation_period"), str):
            raise ValueError("invalid private funding ledger entry")
        ids.add(rid)
        period = entry["allocation_period"]
        try:
            if len(period) != 7:
                raise ValueError("period")
            dt.date.fromisoformat(period + "-01")
        except ValueError:
            raise ValueError("invalid funding allocation period") from None
        if entry["status"] in ("consumed", "partial", "released"):
            amount, fills = entry.get("dca_usd"), entry.get("broker_fill_ids")
            if not numeric(amount) or amount < 0 or not isinstance(fills, list) or any(not isinstance(f, str) or not f for f in fills) or len(fills) != len(set(fills)):
                raise ValueError("invalid historical funding receipt")
            if (entry["status"] == "released" and (amount != 0 or fills)) or (entry["status"] != "released" and (amount <= 0 or not fills)):
                raise ValueError("historical receipt state conflicts with fills")
            if recorded_fills.intersection(fills):
                raise ValueError("duplicate historical broker fills")
            recorded_fills.update(fills)
        if entry["status"] != "released":
            if active.intersection(trades):
                raise ValueError("duplicate active funding ledger trades")
            active.update(trades)
    return value


def update_funding_ledger(payload):
    """Pure journal transition. No disk IO, storage confirmation or order authority."""
    ledger = copy.deepcopy(funding_ledger(payload.get("funding_ledger")))
    if type(payload.get("expected_revision")) is not int or payload["expected_revision"] != ledger["revision"]:
        raise ValueError("funding ledger revision mismatch")
    change = payload.get("change", {})
    rid = change.get("reservation_id")
    if change.get("action") == "reserve":
        if any(e["reservation_id"] == rid for e in ledger["entries"]):
            raise ValueError("reservation already exists")
        ledger["entries"].append(dict(reservation_id=rid, trade_ids=change.get("trade_ids"),
            allocation_period=change.get("allocation_period"), status="reserved"))
    elif change.get("action") == "settle":
        matches = [e for e in ledger["entries"] if e["reservation_id"] == rid]
        if len(matches) != 1 or matches[0]["status"] != "reserved":
            raise ValueError("one unresolved reservation required")
        receipt = change.get("receipt", {})
        state, amount, fills = receipt.get("status"), receipt.get("dca_usd"), receipt.get("broker_fill_ids")
        if receipt.get("broker_readback_verified") is not True or receipt.get("broker_orders_clear") is not True or state not in ("consumed", "partial", "released") or not numeric(amount) or amount < 0 or not isinstance(fills, list) or any(not isinstance(f, str) or not f for f in fills) or len(fills) != len(set(fills)):
            raise ValueError("verified broker funding receipt required")
        if (state == "released" and (amount != 0 or fills)) or (state != "released" and (amount <= 0 or not fills)):
            raise ValueError("receipt state conflicts with fills")
        if any(set(fills).intersection(e.get("broker_fill_ids", [])) for e in ledger["entries"]):
            raise ValueError("broker fill already recorded")
        matches[0].update(status=state, dca_usd=amount, broker_fill_ids=fills)
    else:
        raise ValueError("funding ledger action must be reserve or settle")
    ledger["revision"] += 1
    funding_ledger(ledger)
    return dict(status="PASS", funding_ledger=ledger, execution_authorized=False,
                runtime_data_persisted=False, persistence_required=True)


def check_drawdown(payload, now, report, nav, usd_cash, holdings):
    """Independent ladders: account failures are global, market failures local."""
    if report["blocking_issues"]:
        return report
    observation = payload.get("capabilities", {}).get("market_inputs", {})
    common = []
    if observation.get("status") != "available" or observation.get("source") != "IBKR":
        common.append("authoritative IBKR market_inputs unavailable")
    try:
        age = (now - timestamp(observation["observed_at"])).total_seconds()
        if not -5 <= age <= 300:
            raise ValueError("stale")
    except (KeyError, TypeError, ValueError):
        common.append("fresh market observation required")
    market = observation.get("data") or {}
    if not isinstance(market, dict):
        market = {}
    paths, eligible = {}, {}
    for ticker in ("SPYM", "QQQM"):
        issues = common.copy()
        item = market.get(ticker, {})
        if not isinstance(item, dict):
            item = {}
        dd, tiers = item.get("drawdown"), item.get("tiers_executed")
        try:
            valid_date = 0 <= (now.date() - dt.date.fromisoformat(item["close_as_of"])).days <= 7
        except (KeyError, TypeError, ValueError):
            valid_date = False
        if not numeric(dd) or not 0 <= dd < 1 or not valid_date:
            issues.append("verified fresh closing drawdown required")
        if not isinstance(tiers, list) or any(t not in ("T1", "T2", "T3", "T4") for t in tiers) or len(set(tiers)) != len(tiers):
            issues.append("verified cycle tier state required")
        paths[ticker] = dict(status="DATA INCOMPLETE" if issues else "PASS", blocking_issues=issues)
        if not issues:
            eligible[ticker] = item
    cash_left = usd_cash
    allocation = {t: None if t in paths and paths[t]["status"] != "PASS" else 0 for t in TARGETS}
    candidates = {t: [] if t in eligible else None for t in paths}
    gaps = {t: max(TARGETS[t] * nav - holdings.get(t, 0), 0) for t in TARGETS}
    for t in sorted(eligible, key=lambda t: (-eligible[t]["drawdown"], t)):
        for index, trigger in enumerate((.10, .15, .20, .25), 1):
            tier = f"T{index}"
            if eligible[t]["drawdown"] >= trigger and tier not in eligible[t]["tiers_executed"]:
                amount = min((.09 if t == "SPYM" else .06) * index / 10 * nav, cash_left, gaps[t] - allocation[t])
                if amount > 0:
                    allocation[t] += amount
                    candidates[t].append(tier)
                    cash_left -= amount
    report["paths"] = paths
    report["blocking_issues"] = [f"{t}: {issue}" for t, path in paths.items() for issue in path["blocking_issues"]]
    report["status"] = "DATA INCOMPLETE" if report["blocking_issues"] else "PASS"
    if eligible:
        report["deployment"] = dict(V=nav, C0=usd_cash, gaps=gaps,
            drawdown_allocation=allocation, candidate_tiers=candidates, final_cash=cash_left,
            note="Only PASS paths are candidates. Refresh account after monthly fills; never add standalone snapshots. Whole shares, fees, authorization and verified fills remain required.")
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
