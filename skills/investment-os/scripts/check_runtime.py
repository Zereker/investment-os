"""Stateless, dependency-free Investment OS checks. JSON on stdin, JSON on stdout.

This program neither fetches broker data nor authorizes or executes orders.
Only fresh authoritative connector observations may be supplied in production.
"""
import datetime as dt
import copy
import json
import math
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ALLOWED_ETFS = frozenset(("SPYM", "QQQM"))
TARGETS = {"SPYM": .55, "QQQM": .30}
ACCOUNT = ("account_summary", "balances", "positions", "open_orders", "contract_details")
MONTHLY = ACCOUNT + ("cash_transactions",)
DRAWDOWN_TRIGGERS = (.10, .15, .20, .25)
DRAWDOWN_BUDGETS = {"SPYM": .09, "QQQM": .06}
DRAWDOWN_TIERS = tuple(f"T{index}" for index in range(1, len(DRAWDOWN_TRIGGERS) + 1))
FX_FUNDING = "user_source_confirmation_plus_ibkr_fx"
CASH_FUNDING = "ibkr_cash_transactions"


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp requires an ISO 8601 string")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed


def working_order_status(orders):
    """A valid working order is a constraint, not a missing account fact."""
    if not isinstance(orders, list):
        return "unknown"
    if not orders:
        return "clear"
    seen = set()
    working = {"NEW", "SUBMITTED", "PARTIALLY_FILLED", "PRESUBMITTED",
               "PRE_SUBMITTED", "PENDING_SUBMIT", "PENDING_CANCEL"}
    for order in orders:
        if not isinstance(order, dict):
            return "unknown"
        description = order.get("primary_description")
        if not isinstance(description, str) or not description.strip():
            return "unknown"
        oid = order.get("order_id")
        if type(oid) is not int or oid <= 0 or oid in seen:
            return "unknown"
        seen.add(oid)
        status = order.get("order_status")
        if order.get("side") not in ("BUY", "SELL") or not isinstance(status, str) or status not in working:
            return "unknown"
        try:
            raw = [order[k] for k in ("total_shares_qty", "cum_shares_qty", "remaining_shares_qty")]
            if any(isinstance(x, bool) for x in raw):
                return "unknown"
            total, filled, remaining = map(float, raw)
            if not all(math.isfinite(x) for x in (total, filled, remaining)):
                return "unknown"
            if total <= 0 or filled < 0 or remaining <= 0 or not math.isclose(total, filled + remaining, rel_tol=0, abs_tol=1e-8):
                return "unknown"
            if order.get("order_type") == "LIMIT":
                price = order["limit_price"]
                if isinstance(price, bool) or not math.isfinite(float(price)) or float(price) <= 0:
                    return "unknown"
            elif order.get("order_type") != "MARKET":
                return "unknown"
        except (KeyError, TypeError, ValueError, OverflowError):
            return "unknown"
    return "pending"


def balance_disclosure(rows):
    """Keep valid fields even when a broker row contains an invalid value."""
    if not isinstance(rows, list):
        return None, []
    output, issues = [], []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            output.append(None)
            issues.append(f"balances[{index}]: object required")
            continue
        normalized = {}
        for field, value in row.items():
            if isinstance(value, (dict, list)) or (isinstance(value, float) and not math.isfinite(value)):
                issues.append(f"balances[{index}].{field}: invalid scalar")
                value = None
            normalized[field] = value
        output.append(normalized)
    return output, issues


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


def confirmed_fx_contribution(payload, data, now, ledger, issues):
    confirmation = payload.get("funding_confirmation", {})
    if confirmation.get("source_currency") != "CNH" or confirmation.get("confirmed_new_funding") is not True:
        issues.append("explicit CNH new-funding source confirmation required")
    if confirmation.get("allocation_period") != now.strftime("%Y-%m"):
        issues.append("funding allocation period must match monthly review period")
    selected = confirmation.get("trade_ids")
    used = {trade for entry in ledger["entries"] if entry["status"] != "released"
            for trade in entry["trade_ids"]} if ledger else set()
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
    if set(TARGETS) != ALLOWED_ETFS:
        raise ValueError("Production universe must remain exactly SPYM and QQQM")
    task = payload.get("task", "account")
    if task == "trade_scope":
        return check_trade_scope(payload, now)
    if task == "funding_ledger":
        return update_funding_ledger(payload, now)
    if task not in ("daily", "account", "monthly", "drawdown"):
        raise ValueError("task must be daily, account, monthly, drawdown, trade_scope or funding_ledger")
    observations = payload.get("capabilities", {})
    if not isinstance(observations, dict):
        raise ValueError("capabilities must be an object")
    required = MONTHLY if task == "monthly" else ACCOUNT
    confirmed_path = task == "monthly" and "funding_confirmation" in payload
    if confirmed_path:
        required = ACCOUNT + ("fx_funding",)
    issues, data, observed, source_times = [], {}, [], {}
    for name in required:
        item = observations.get(name, {})
        if not isinstance(item, dict):
            issues.append(f"{name}: invalid capability envelope")
            continue
        source_time = item.get("source_as_of")
        if isinstance(source_time, str):
            source_times[name] = source_time
        status = item.get("status", "unavailable")
        if status != "available":
            label = status if status in ("unavailable", "stale", "conflicting", "not_requested", "not_applicable") else "invalid status"
            issues.append(f"{name}: {label}")
            continue
        if item.get("source") != "IBKR" or not isinstance(item.get("data"), dict):
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
    if not isinstance(currency, str):
        currency = None
    if currency != "USD" or not numeric(nav) or nav <= 0:
        issues.append("positive USD account NAV required")
        nav = None
    rows, disclosure_issues = balance_disclosure(data.get("balances", {}).get("balances"))
    cash = usd_cash = None
    if isinstance(rows, list):
        valid_rows = [r for r in rows if isinstance(r, dict)]
        if len(valid_rows) != len(rows) or any(
            not isinstance(r.get("currency"), str) or not r["currency"].strip() or not numeric(r.get("cash_balance"))
            for r in valid_rows
        ):
            issues.append("each balance row requires a currency and finite cash balance")
        base = [r for r in valid_rows if r.get("currency") == "BASE"]
        usd = [r for r in valid_rows if r.get("currency") == "USD"]
        if len(base) == 1 and numeric(base[0].get("cash_balance")):
            cash = base[0]["cash_balance"]
        if len(usd) == 1 and numeric(usd[0].get("cash_balance")):
            settled = usd[0].get("settled_cash")
            if numeric(settled) and settled >= 0:
                usd_cash = min(usd[0]["cash_balance"], settled)
        if any(numeric(r.get("cash_balance")) and r["cash_balance"] < 0 for r in valid_rows):
            issues.append("negative currency cash balance: borrowing prohibited")
    if cash is None or usd_cash is None:
        issues.append("unique BASE aggregate and USD cash rows required")

    positions = data.get("positions", {}).get("positions")
    details = data.get("contract_details", {}).get("contracts", [])
    values, holdings, legacy, contracts = [], {}, 0, set()
    mapping_complete = True
    if not isinstance(details, list) or any(not isinstance(c, dict) for c in details):
        issues.append("invalid canonical contract list")
        details = []
        mapping_complete = False
    if not isinstance(positions, list):
        issues.append("positions envelope required")
        positions = None
    else:
        for p in positions:
            if not isinstance(p, dict):
                issues.append("invalid position row")
                continue
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
            if type(cid) is not int or cid in contracts:
                issues.append("missing or duplicate position contract")
                mapping_complete = False
            else:
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
    order_status = working_order_status(orders)
    if order_status == "unknown" or (order_status == "pending" and task != "daily"):
        issues.append(f"open orders: {order_status}")

    report = dict(status="DATA INCOMPLETE" if issues else "PASS", blocking_issues=issues,
                  reconciliation=reconciliation, open_orders_status=order_status,
                  balances_by_currency=rows, base_currency=currency,
                  disclosure_issues=disclosure_issues,
                  selected_balance_label="BASE" if cash is not None else None,
                  selection_reason="BASE for reconciliation; USD only for deployment",
                  deployment=None, funding_preparation=funding_preparation(rows),
                  execution_authorized=False, runtime_data_persisted=False)
    if task == "daily":
        report.update(read_only=True, execution_check_required=True,
                      observed_at=max(observed).isoformat() if observed else None,
                      validated_at=now.isoformat(),
                      source_as_of={name: source_times.get(name) for name in required},
                      has_open_orders=None if order_status == "unknown" else order_status == "pending",
                      order_constraints=["working orders require review before deployment"] if order_status == "pending" else [])
    coherent = task != "daily" or (reconciliation is not None and reconciliation["status"] == "PASS")
    if nav and positions is not None and len(values) == len(positions) and mapping_complete and coherent:
        report["weights"] = {t: holdings.get(t, 0) / nav for t in TARGETS}
        report["legacy"] = {"market_value": legacy, "weight": legacy / nav}
        report["usd_cash_weight"] = usd_cash / nav if usd_cash is not None else None
    if task in ("daily", "account"):
        return report
    if task == "drawdown":
        return check_drawdown(payload, now, report, nav, usd_cash, holdings)

    # Monthly gates must finish before any funding formula is evaluated.
    try:
        market_now = now.astimezone(ZoneInfo("America/New_York"))
    except ZoneInfoNotFoundError:
        issues.append("America/New_York timezone data required for monthly checks")
        report["status"] = "DATA INCOMPLETE"
        return report
    period = market_now.strftime("%Y-%m")
    report.update(allocation_period=period, monthly_plan_reservable=False,
                  funding_evidence_mode=FX_FUNDING if confirmed_path else CASH_FUNDING)
    ledger = None
    if confirmed_path or "funding_ledger" in payload:
        try:
            ledger = funding_ledger(payload.get("funding_ledger"))
        except ValueError as exc:
            issues.append(str(exc))
    if ledger and monthly_plan_exists(ledger, period):
        issues.append("a funding plan already exists for this New York month")
    contribution = confirmed_fx_contribution(payload, data, market_now, ledger, issues) if confirmed_path else data.get("cash_transactions", {}).get("external_contribution_usd")
    if not numeric(contribution) or contribution < 0:
        issues.append("authoritative external net contribution F unavailable or invalid")
    schedule = payload.get("schedule", {})
    if schedule.get("source") != "NYSE" or schedule.get("monthly_execution_date") != market_now.date().isoformat():
        issues.append("not a verified fixed monthly execution date; no catch-up")
    if schedule.get("calculation_already_run") is not False:
        issues.append("monthly calculation lifecycle is unknown or already run")
    report["status"] = "DATA INCOMPLETE" if issues else "PASS"
    if issues:
        return report
    report["monthly_plan_reservable"] = ledger is not None and ledger["schema_version"] == 2

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


def check_trade_scope(payload, now):
    """Read-only instrument gate; never account clearance or order authority."""
    result = dict(status="DATA INCOMPLETE", blocking_issues=[],
                  normalized_instrument=None, scope_only=True,
                  execution_authorized=False, runtime_data_persisted=False)
    operation = payload.get("operation", {})
    expected = {k: operation.get(k) for k in ("contract_id", "symbol", "sec_type", "currency", "side")}
    if any(expected[k] is None for k in expected):
        result["blocking_issues"].append("exact instrument identity and side required")
        return result
    if expected["symbol"] not in ALLOWED_ETFS or expected["sec_type"] != "STK" or expected["currency"] != "USD" or expected["side"] not in ("BUY", "SELL"):
        result.update(status="REJECT", blocking_issues=["only USD SPYM/QQQM ETF shares may be acted on"])
        return result
    if type(expected["contract_id"]) is not int or expected["contract_id"] <= 0:
        result["blocking_issues"].append("positive canonical contract ID required")
        return result
    evidence = payload.get("capabilities", {}).get("contract_details", {})
    if evidence.get("status") != "available" or evidence.get("source") != "IBKR":
        result["blocking_issues"].append("authoritative IBKR contract evidence required")
        return result
    try:
        age = (now - timestamp(evidence["observed_at"])).total_seconds()
        if not -5 <= age <= 300:
            raise ValueError("stale contract evidence")
    except (KeyError, TypeError, ValueError):
        result["blocking_issues"].append("fresh contract observation required")
        return result
    contracts = evidence.get("data", {}).get("contracts")
    if not isinstance(contracts, list) or any(not isinstance(c, dict) for c in contracts):
        result["blocking_issues"].append("canonical contract list required")
        return result
    matches = [c for c in contracts if c.get("contract_id") == expected["contract_id"]]
    if len(matches) != 1:
        result["blocking_issues"].append("one matching canonical contract required")
        return result
    if any(matches[0].get(k) != expected[k] for k in ("symbol", "sec_type", "currency")):
        result.update(status="REJECT", blocking_issues=["operation conflicts with canonical broker instrument"])
        return result
    result.update(status="PASS", normalized_instrument=expected)
    return result


def valid_period(value):
    if not isinstance(value, str) or len(value) != 7:
        return False
    try:
        dt.date.fromisoformat(value + "-01")
    except ValueError:
        return False
    return True


def unique_strings(values):
    return (isinstance(values, list) and all(isinstance(value, str) and value.strip() for value in values)
            and len(values) == len(set(values)))


def monthly_plan_exists(ledger, period):
    if period in ledger.get("historical_months", []):
        return True
    return any(entry["allocation_period"] == period and
               (ledger["schema_version"] == 2 or entry["status"] != "released")
               for entry in ledger["entries"])


def valid_funding_receipt(plan, receipt):
    dca, fills = receipt.get("dca_usd"), receipt.get("broker_fill_ids")
    baseline = receipt.get("baseline_usd") if "funding_evidence_mode" in plan else 0
    if not all(numeric(amount) and amount >= 0 for amount in (dca, baseline)) or not unique_strings(fills):
        return False
    if "funding_evidence_mode" in plan:
        if dca > plan["planned_dca_usd"] + 1e-8 or baseline > plan["planned_baseline_usd"] + 1e-8:
            return False
    if receipt.get("status") == "released":
        return dca == baseline == 0 and not fills
    return (dca > 0 or baseline > 0) and bool(fills)


def valid_allocation(allocation, total):
    return (isinstance(allocation, dict) and set(allocation) == ALLOWED_ETFS
            and all(numeric(amount) and amount >= 0 for amount in allocation.values())
            and math.isclose(sum(allocation.values()), total, rel_tol=0, abs_tol=1e-8))


def funding_ledger(value):
    """Validate a private journal; the host must verify history and durable storage."""
    if not isinstance(value, dict):
        raise ValueError("verified complete private funding ledger required")
    version, revision, ledger_id = value.get("schema_version"), value.get("revision"), value.get("ledger_id")
    if (type(version) is not int or version not in (1, 2) or type(revision) is not int or revision < 0
            or not isinstance(ledger_id, str) or not ledger_id.strip()
            or value.get("history_scope") != "verified_full_history" or not isinstance(value.get("entries"), list)):
        raise ValueError("invalid private funding ledger header or unverified history")
    history = []
    if version == 2:
        history = value.get("historical_months")
        if not unique_strings(history) or not all(valid_period(period) for period in history):
            raise ValueError("verified historical monthly periods required")
    ids, active, recorded_fills = set(), set(), set()
    periods, plan_periods = set(), set()
    for entry in value["entries"]:
        if not isinstance(entry, dict):
            raise ValueError("invalid private funding ledger entry")
        trades = entry.get("trade_ids")
        rid = entry.get("reservation_id")
        if (not isinstance(rid, str) or not rid.strip() or rid in ids
                or entry.get("status") not in ("reserved", "consumed", "partial", "released")
                or not unique_strings(trades)):
            raise ValueError("invalid private funding ledger entry")
        ids.add(rid)
        period = entry.get("allocation_period")
        if not valid_period(period):
            raise ValueError("invalid funding allocation period")
        if "funding_evidence_mode" in entry:
            mode = entry["funding_evidence_mode"]
            planned = (entry.get("planned_dca_usd"), entry.get("planned_baseline_usd"))
            if (version != 2 or mode not in (FX_FUNDING, CASH_FUNDING) or bool(trades) != (mode == FX_FUNDING)
                    or not all(numeric(amount) and amount >= 0 for amount in planned)):
                raise ValueError("invalid monthly funding plan")
            if not (valid_allocation(entry.get("routine_allocation"), planned[0]) and
                    valid_allocation(entry.get("baseline_allocation"), planned[1])):
                raise ValueError("invalid monthly funding plan")
            if period in periods or period in history:
                raise ValueError("duplicate monthly funding plan")
            plan_periods.add(period)
        elif not trades:
            raise ValueError("legacy funding entry requires FX trade IDs")
        elif period in plan_periods:
            raise ValueError("duplicate monthly funding plan")
        periods.add(period)
        if entry["status"] in ("consumed", "partial", "released"):
            if not valid_funding_receipt(entry, entry):
                raise ValueError("invalid historical funding receipt")
            fills = entry["broker_fill_ids"]
            if recorded_fills.intersection(fills):
                raise ValueError("duplicate historical broker fills")
            recorded_fills.update(fills)
        if entry["status"] != "released":
            if active.intersection(trades):
                raise ValueError("duplicate active funding ledger trades")
            active.update(trades)
    return value


def update_funding_ledger(payload, now):
    """Pure journal transition. No disk IO, storage confirmation or order authority."""
    ledger = copy.deepcopy(funding_ledger(payload.get("funding_ledger")))
    if type(payload.get("expected_revision")) is not int or payload["expected_revision"] != ledger["revision"]:
        raise ValueError("funding ledger revision mismatch")
    change = payload.get("change", {})
    rid = change.get("reservation_id")
    action = change.get("action")
    if action == "upgrade_monthly_history":
        if ledger["schema_version"] != 1 or change.get("monthly_history_verified") is not True:
            raise ValueError("verified monthly history required to upgrade the legacy ledger")
        ledger.update(schema_version=2, historical_months=change.get("historical_months"))
    elif action in ("reserve", "reserve_monthly"):
        if any(e["reservation_id"] == rid for e in ledger["entries"]):
            raise ValueError("reservation already exists")
        if action == "reserve_monthly":
            review = change.get("monthly_review")
            if ledger["schema_version"] != 2 or not isinstance(review, dict) or review.get("task") != "monthly":
                raise ValueError("monthly reservation requires schema 2 and fresh monthly review input")
            result = check({**review, "funding_ledger": ledger}, now)
            if not result.get("monthly_plan_reservable"):
                raise ValueError("monthly reservation blocked: " + "; ".join(result["blocking_issues"]))
            mode = result["funding_evidence_mode"]
            deployment = result["deployment"]
            trades = review["funding_confirmation"]["trade_ids"] if mode == FX_FUNDING else []
            ledger["entries"].append(dict(reservation_id=rid, trade_ids=copy.deepcopy(trades),
                allocation_period=result["allocation_period"], status="reserved", funding_evidence_mode=mode,
                planned_dca_usd=deployment["D"], planned_baseline_usd=deployment["B"],
                routine_allocation=deployment["routine_allocation"],
                baseline_allocation=deployment["baseline_allocation"]))
        else:
            if ledger["schema_version"] != 1:
                raise ValueError("schema 2 requires reserve_monthly")
            period = change.get("allocation_period")
            occupied = any(entry["allocation_period"] == period for entry in ledger["entries"])
            ledger["entries"].append(dict(reservation_id=rid, trade_ids=change.get("trade_ids"),
                allocation_period=period, status="reserved"))
            funding_ledger(ledger)
            if occupied:
                raise ValueError("a funding plan already exists for this New York month")
    elif action == "settle":
        matches = [e for e in ledger["entries"] if e["reservation_id"] == rid]
        if len(matches) != 1 or matches[0]["status"] != "reserved":
            raise ValueError("one unresolved reservation required")
        receipt = change.get("receipt", {})
        state = receipt.get("status")
        if (receipt.get("broker_readback_verified") is not True or receipt.get("broker_orders_clear") is not True
                or state not in ("consumed", "partial", "released")):
            raise ValueError("verified broker funding receipt required")
        if not valid_funding_receipt(matches[0], receipt):
            raise ValueError("receipt state or amounts conflict with fills or the reserved plan")
        fills = receipt["broker_fill_ids"]
        if any(set(fills).intersection(e.get("broker_fill_ids", [])) for e in ledger["entries"]):
            raise ValueError("broker fill already recorded")
        matches[0].update(status=state, dca_usd=receipt["dca_usd"], broker_fill_ids=copy.deepcopy(fills))
        if "funding_evidence_mode" in matches[0]:
            matches[0]["baseline_usd"] = receipt["baseline_usd"]
    else:
        raise ValueError("funding ledger action must be upgrade_monthly_history, reserve_monthly, reserve or settle")
    ledger["revision"] += 1
    funding_ledger(ledger)
    return dict(status="PASS", funding_ledger=ledger, execution_authorized=False,
                runtime_data_persisted=False, persistence_required=True)


def valid_tier_receipts(item):
    """Verify the shape and cycle of host-verified, private fill associations."""
    receipts = item.get("tier_receipts")
    if not isinstance(receipts, dict) or set(receipts) != set(item["tiers_executed"]):
        return False
    try:
        peak = dt.date.fromisoformat(item["cycle_peak_date"])
        close = dt.date.fromisoformat(item["close_as_of"])
    except (KeyError, TypeError, ValueError):
        return False
    if peak > close:
        return False
    used = set()
    for receipt in receipts.values():
        if not isinstance(receipt, dict):
            return False
        if receipt.get("cycle_peak_date") != item["cycle_peak_date"]:
            return False
        cap, amount = receipt.get("allocation_usd"), receipt.get("filled_usd")
        fills = receipt.get("broker_fill_ids")
        if not numeric(cap) or not numeric(amount) or not 0 < amount <= cap + 1e-8:
            return False
        if not unique_strings(fills) or not fills or used.intersection(fills):
            return False
        used.update(fills)
    return True


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
        if not unique_strings(tiers) or any(t not in DRAWDOWN_TIERS for t in tiers):
            issues.append("verified cycle tier state required")
        elif "tier_receipts" in item and not valid_tier_receipts(item):
            issues.append("tier receipts must verify distinct fills in the current cycle")
        paths[ticker] = dict(status="DATA INCOMPLETE" if issues else "PASS", blocking_issues=issues)
        if not issues:
            eligible[ticker] = item
            paths[ticker].update(close_as_of=item["close_as_of"], drawdown=dd)
            if "tier_receipts" in item:
                paths[ticker]["cycle_peak_date"] = item["cycle_peak_date"]

    if len(eligible) == len(TARGETS):
        spym_fills = {fill for receipt in eligible["SPYM"].get("tier_receipts", {}).values()
                      for fill in receipt["broker_fill_ids"]}
        qqqm_fills = {fill for receipt in eligible["QQQM"].get("tier_receipts", {}).values()
                      for fill in receipt["broker_fill_ids"]}
        if spym_fills.intersection(qqqm_fills):
            for ticker in tuple(eligible):
                paths[ticker].update(status="DATA INCOMPLETE", blocking_issues=["broker fill shared by both ladders"])
            eligible.clear()
    cash_left = usd_cash
    allocation = {t: None if t in paths and paths[t]["status"] != "PASS" else 0 for t in TARGETS}
    candidates = {t: [] if t in eligible else None for t in paths}
    per_tier = {t: [] if t in eligible else None for t in paths}
    gaps = {t: max(TARGETS[t] * nav - holdings.get(t, 0), 0) for t in TARGETS}
    for t in sorted(eligible, key=lambda t: (-eligible[t]["drawdown"], t)):
        item = eligible[t]
        dd = item["drawdown"]
        for index, (tier, trigger) in enumerate(zip(DRAWDOWN_TIERS, DRAWDOWN_TRIGGERS), 1):
            budget = DRAWDOWN_BUDGETS[t] * index / 10 * nav
            amount = 0
            if tier in item["tiers_executed"]:
                state = "executed"
            elif dd > DRAWDOWN_TRIGGERS[-1]:
                state = "above_maximum"
            elif dd < trigger:
                state = "below_trigger"
            else:
                amount = min(budget, cash_left, max(gaps[t] - allocation[t], 0))
                state = "candidate" if amount > 0 else "no_capacity"
                if amount > 0:
                    allocation[t] += amount
                    candidates[t].append(tier)
                    cash_left -= amount
            receipt = item.get("tier_receipts", {}).get(tier)
            if receipt is not None:
                receipt = {key: receipt[key] for key in ("cycle_peak_date", "allocation_usd", "filled_usd", "broker_fill_ids")}
            per_tier[t].append(dict(tier=tier, trigger=trigger, budget_usd=budget,
                                    allocation_usd=amount, state=state, receipt=receipt))
    report["paths"] = paths
    report["blocking_issues"] = [f"{t}: {issue}" for t, path in paths.items() for issue in path["blocking_issues"]]
    report["status"] = "DATA INCOMPLETE" if report["blocking_issues"] else "PASS"
    if eligible:
        report["deployment"] = dict(V=nav, C0=usd_cash, gaps=gaps,
            drawdown_allocation=allocation, candidate_tiers=candidates, tier_allocations=per_tier,
            final_cash=cash_left,
            note="Only PASS paths are candidates. Refresh account after monthly fills; never add standalone snapshots. Whole shares, fees, authorization and verified fills remain required.")
    return report


def main():
    try:
        result = check(json.load(sys.stdin))
        output = json.dumps(result, allow_nan=False)
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        result = dict(status="DATA INCOMPLETE", blocking_issues=[f"invalid input: {exc}"],
                      deployment=None, execution_authorized=False, runtime_data_persisted=False)
        output = json.dumps(result, allow_nan=False)
    print(output)
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
