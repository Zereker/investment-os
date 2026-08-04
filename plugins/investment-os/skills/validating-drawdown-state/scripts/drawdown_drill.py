#!/usr/bin/env python3
"""Replay the Constitution's drawdown-deployment tier machine over real SPYM
history, so the mechanism is proven BEFORE a real crash depends on it.

Why this exists: the 15% structural cash position costs ~0.45-0.75pp/year, and
its entire justification is the drawdown-deployment clause
(skills/using-investment-os/references/00-constitution.md). That clause had never been executed —
its first live run would have been during a crash, which is the worst possible
time to discover a state-machine bug.

What it checks (per the Constitution's drawdown clause + the deployment framework in
skills/using-investment-os/references/01-operating-manual.md):
  - DD is measured against the running historical maximum CLOSE.
  - Tiers: DD >= 10/15/20/25% lower the cash floor to
    13.5/10.5/6/0% (+U) — GRADED tranches of 1.5/3/4.5/6pp from the 15%
    target, 15pp total. Deeper drawdown buys more; no bottom is called.
  - v4.6: the ladder ENDS at 25% and spends the cash out entirely. Past 25%
    the ammunition is gone by design and nothing further unlocks, however
    deep the drawdown goes.
  - Each tier fires at most once per drawdown cycle.
  - A new all-time-high CLOSE resets the cycle: all tiers become AVAILABLE.
  - One day may satisfy several tiers (gap down); they fire shallow-to-deep,
    still subject to once-per-cycle.

Scope limit — read this before trusting the result: the drill validates the
PRICE -> TIER logic only. It does NOT validate the "which tiers were already
executed" half of state reconstruction (skills/using-investment-os/references/01-operating-manual.md), which depends on
IBKR alerts, journal entries and cash-level self-proof. That half stays unproven
until a live cycle exercises it.

Data source: stockanalysis.com daily closes — a registered aggregator, Yellow
per skills/using-investment-os/references/08-data-registry.md. Adequate for a drill; the production trigger must
read IBKR or the official State Street series. This tool reports facts only; it
never changes the Registry and never authorizes trades.

Usage:
  python3 skills/validating-drawdown-state/scripts/drawdown_drill.py                    # 10Y SPYM replay + invariant checks
  python3 skills/validating-drawdown-state/scripts/drawdown_drill.py --symbol spy       # cross-check against the index proxy
  python3 skills/validating-drawdown-state/scripts/drawdown_drill.py --range 5Y
  python3 skills/validating-drawdown-state/scripts/drawdown_drill.py --markdown         # block for a Research note
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HISTORY_API = "https://stockanalysis.com/api/symbol/e/{sym}/history?range={rng}&period=Daily"

# Constitution drawdown-deployment clause: (DD trigger, temporary cash floor).
# U (the SOXX stage reserve) rides on top of every floor and is not modeled here.
TIERS = ((0.10, "T1", 0.0150),
         (0.15, "T2", 0.0300),
         (0.20, "T3", 0.0450),
         (0.25, "T4", 0.0600))
ABSOLUTE_FLOOR = 0.0     # cash never goes below this (+U)
LADDER = sum(t[2] for t in TIERS)   # 15pp: the whole cash position is ammunition
NORMAL_CASH_FLOOR = 0.12


def fetch_closes(symbol: str, rng: str) -> list[tuple[str, float]]:
    """Return [(date, close)] ascending. Raises on any failure — never guesses."""
    url = HISTORY_API.format(sym=symbol.lower(), rng=rng)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    rows = payload.get("data")
    if not rows:
        raise RuntimeError(f"no history returned for {symbol} @ {rng}")
    series = sorted((r["t"], float(r["c"])) for r in rows)
    if len(series) < 2:
        raise RuntimeError(f"history too short for {symbol}: {len(series)} rows")
    return series


def replay(series: list[tuple[str, float]]) -> tuple[list[dict], list[dict]]:
    """Run the tier machine. Returns (trigger events, cycle records)."""
    events: list[dict] = []
    cycles: list[dict] = []

    ath = series[0][1]
    cycle_start = series[0][0]
    cycle_peak = ath
    executed: set[str] = set()
    max_dd_in_cycle = 0.0

    for day, close in series:
        if close > ath:
            # new all-time-high close: close out the cycle and reset every tier
            if executed or max_dd_in_cycle > 0:
                cycles.append({
                    "start": cycle_start, "end": day, "peak": cycle_peak,
                    "max_dd": max_dd_in_cycle, "fired": sorted(executed),
                })
            ath = close
            cycle_start = day
            cycle_peak = close
            executed = set()
            max_dd_in_cycle = 0.0
            continue

        dd = (ath - close) / ath
        max_dd_in_cycle = max(max_dd_in_cycle, dd)

        # shallow-to-deep, once per cycle
        for trigger, name, tranche in TIERS:
            if dd >= trigger and name not in executed:
                executed.add(name)
                events.append({
                    "date": day, "tier": name, "dd": dd, "close": close,
                    "ath": ath, "cycle_start": cycle_start, "tranche": tranche,
                })

    cycles.append({
        "start": cycle_start, "end": series[-1][0], "peak": cycle_peak,
        "max_dd": max_dd_in_cycle, "fired": sorted(executed), "open": True,
    })
    return events, cycles


def current_release(dd: float, executed: set[str]) -> float:
    """Weight of NAV the clause releases right now, given tiers already fired."""
    return sum(tranche for trigger, name, tranche in TIERS
               if dd >= trigger and name not in executed)


def check_invariants(series, events, cycles) -> list[str]:
    """Assert the clause's guarantees. Returns a list of failures (empty = pass)."""
    failures = []

    # 1. once per tier per cycle
    seen: dict[str, set[str]] = {}
    for e in events:
        fired = seen.setdefault(e["cycle_start"], set())
        if e["tier"] in fired:
            failures.append(f"tier {e['tier']} fired twice in cycle starting {e['cycle_start']}")
        fired.add(e["tier"])

    # 2. every trigger genuinely met its threshold
    thresholds = {name: t for t, name, _ in TIERS}
    for e in events:
        if e["dd"] < thresholds[e["tier"]] - 1e-12:
            failures.append(f"{e['tier']} fired at DD {e['dd']:.4f}, below its {thresholds[e['tier']]:.0%} trigger")

    # 3. shallow-to-deep ordering within a cycle
    order = {name: i for i, (_, name, _t) in enumerate(TIERS)}
    per_cycle: dict[str, list[str]] = {}
    for e in events:
        per_cycle.setdefault(e["cycle_start"], []).append(e["tier"])
    for cycle, fired in per_cycle.items():
        if [order[t] for t in fired] != sorted(order[t] for t in fired):
            failures.append(f"cycle {cycle}: tiers fired out of order: {fired}")

    # 4. a deeper tier never fires without the shallower one having fired this cycle
    for cycle, fired in per_cycle.items():
        idxs = sorted(order[t] for t in fired)
        if idxs and idxs != list(range(idxs[0], idxs[0] + len(idxs))):
            failures.append(f"cycle {cycle}: tier sequence has gaps: {fired}")
        if idxs and idxs[0] != 0:
            failures.append(f"cycle {cycle}: fired {fired} without T1")

    # 5. cycle reset — a closed cycle must be followed by a fresh tier set
    for c in cycles:
        if not c.get("open") and c["fired"] and c["max_dd"] < TIERS[0][0]:
            failures.append(f"cycle {c['start']}: tiers fired but max DD was only {c['max_dd']:.2%}")

    # 6. determinism — replaying the same series must give the same events
    again, _ = replay(series)
    if again != events:
        failures.append("replay is not deterministic")

    # 7. release helper is consistent with the ladder
    if current_release(0.0, set()) != 0.0:
        failures.append("no drawdown must release nothing")
    if abs(current_release(0.099, set())) > 1e-12:
        failures.append("below T1 must release nothing")
    if abs(current_release(0.10, set()) - TIERS[0][2]) > 1e-12:
        failures.append("T1 alone must release exactly its own tranche")
    if abs(current_release(0.28, set()) - LADDER) > 1e-12:
        failures.append("a gap down to 28% must release the whole ladder")
    # graded, not equal: every tier must be strictly larger than the one above it
    if any(b[2] <= a[2] for a, b in zip(TIERS, TIERS[1:])):
        failures.append("tranches must grow strictly with depth")
    # v4.6: past the deepest tier nothing further unlocks — the ladder ends at 25%
    if abs(current_release(0.50, set()) - LADDER) > 1e-12:
        failures.append("a 50% drawdown must release no more than the whole ladder")
    if abs(current_release(0.50, {"T1", "T2", "T3", "T4"})) > 1e-12:
        failures.append("a spent ladder must release nothing however deep the fall")
    if abs(current_release(0.28, {"T1", "T2"}) - (TIERS[2][2] + TIERS[3][2])) > 1e-12:
        failures.append("already-executed tiers must not release again")
    # the tranches must take cash from the 15% target exactly to the floor
    if abs(LADDER + ABSOLUTE_FLOOR - 0.15) > 1e-12:
        failures.append("ladder does not span 15% -> the absolute floor")

    return failures


def report(symbol, rng, series, events, cycles, failures, markdown: bool) -> None:
    first, last = series[0][0], series[-1][0]
    closed = [c for c in cycles if not c.get("open")]
    deep = [c for c in closed if c["fired"]]

    if markdown:
        print(f"# Drawdown Deployment Drill — {symbol.upper()} {first} → {last}\n")
        print(f"- 数据源：stockanalysis.com 日收盘（Yellow，聚合源；生产触发须用 IBKR / 官方序列）")
        print(f"- 交易日数：{len(series)}｜完成的回撤周期：{len(closed)}｜其中触发过档位的：{len(deep)}\n")
        print("| 触发日 | 档位 | DD | 周期起点(ATH日) | 现金下限临时降至 |")
        print("|---|---|---:|---|---:|")
        for e in events:
            print(f"| {e['date']} | {e['tier']} | {e['dd']:.1%} | {e['cycle_start']} | {e['tranche']:.1%} of NAV |")
        print(f"\n不变量检查：{'全部通过' if not failures else '**失败 ' + str(len(failures)) + ' 项**'}")
        for f in failures:
            print(f"- {f}")
        return

    print(f"Drawdown deployment drill — {symbol.upper()}  {first} → {last}  ({len(series)} trading days)")
    print(f"source: stockanalysis.com daily closes (Yellow; production must use IBKR/official)\n")

    if not events:
        print("no tier ever triggered in this window")
    else:
        print(f"{'date':12} {'tier':5} {'DD':>7} {'close':>10} {'ATH':>10}  {'cycle start':12} {'释放':>8}")
        for e in events:
            print(f"{e['date']:12} {e['tier']:5} {e['dd']:>6.1%} {e['close']:>10.2f} {e['ath']:>10.2f}  "
                  f"{e['cycle_start']:12} {e['tranche']:>7.1%}")

    print(f"\ncycles: {len(closed)} completed, {len(deep)} of them deep enough to fire a tier")
    for c in deep:
        print(f"  {c['start']} → {c['end']}  max DD {c['max_dd']:>5.1%}  fired {','.join(c['fired'])}")
    open_cycle = [c for c in cycles if c.get("open")][0]
    print(f"  {open_cycle['start']} → (open)  max DD {open_cycle['max_dd']:>5.1%}  "
          f"fired {','.join(open_cycle['fired']) or 'none'}")

    print()
    if failures:
        print(f"INVARIANT FAILURES ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
    else:
        print("all invariants hold: once-per-cycle, threshold respected, shallow-to-deep,")
        print("no gaps, ATH reset, deterministic replay, release helper consistent")
    print("\nscope: validates price->tier logic only. The 'which tiers already executed'")
    print("reconstruction (IBKR alerts + journal + cash-level self-proof) stays unproven")
    print("until a live cycle exercises it. See skills/using-investment-os/references/01-operating-manual.md (state reconstruction).")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbol", default="spym", help="ticker to replay (default: spym)")
    ap.add_argument("--range", dest="rng", default="10Y", help="history range: 5Y, 10Y (default: 10Y)")
    ap.add_argument("--markdown", action="store_true", help="emit a Research-note block")
    args = ap.parse_args()

    try:
        series = fetch_closes(args.symbol, args.rng)
    except Exception as exc:
        print(f"DATA INCOMPLETE: could not fetch {args.symbol.upper()} history: {exc}", file=sys.stderr)
        return 2

    events, cycles = replay(series)
    failures = check_invariants(series, events, cycles)
    report(args.symbol, args.rng, series, events, cycles, failures, args.markdown)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
