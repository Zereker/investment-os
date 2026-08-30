#!/usr/bin/env python3
"""Compute the month's funding decision from live account inputs — an executable
mirror of the published funding rules.

Why this exists: hand-deriving the funding computation from the docs is slow
(the target is 20 minutes) and lets two agents reach two different answers.
This closes that gap: same inputs -> same answer, every time.

Mirrors (any divergence from these files is a BUG in this script, not a new rule):
  skills/investment-os/references/00-constitution.md       targets, bands, cash floor, tiers
  skills/investment-os/references/02-monthly.md            deployment framework (D / S / B / drawdown),
                                                                 monthly gate order and routine-path checks

Hard boundaries this script will not cross:
  - It NEVER places or formats an executable order. Output is the published
    vocabulary only: HOLD / BUY CANDIDATE / REVIEW / DATA INCOMPLETE.
  - It NEVER writes account figures to disk. Values live in argv and stdout,
    never in the repo (public-repo privacy red line).
  - It NEVER invents inputs. Positions and NAV must come from IBKR; a missing
    input yields DATA INCOMPLETE, not a guess.
  - It NEVER reaches the network. Prices and account state arrive as arguments.
  - Which drawdown tiers already fired this cycle cannot be derived from price.
    Pass --tiers-executed; omitting it makes the script say so rather than assume.
  - This month's actual external contribution F cannot be derived from positions.
    Pass --contribution (0 for a no-deposit month); omitting it makes the Routine
    DCA path say DATA INCOMPLETE rather than silently deploying on an assumed F=0.

Usage (figures come from IBKR, in account currency; they are never persisted):
  python3 skills/investment-os/scripts/monthly_execution.py --nav 100000 --cash 18000 \\
      --spym 50000 --qqqm 26000 --soxx 6000 --contribution 2000

  # already deployed T1 earlier in this drawdown cycle:
  python3 skills/investment-os/scripts/monthly_execution.py ... --tiers-executed T1

  # DD comes from the IBKR close series the session read; omit it and tiers are
  # simply not evaluated today:
  python3 skills/investment-os/scripts/monthly_execution.py ... --dd 0.0108 --dd-as-of 2026-08-28
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from account_reconciliation import reconcile_nav  # noqa: E402

# --- Constitution constants. Changing these here changes nothing in the rules;
# --- they must be edited in 00-constitution.md first (red line 5).
# Four explicit per-ticker targets summing to 100%. SOXX is an ordinary
# holding whose gap is funded by the same channels as the others.
TARGETS = {"cash": 0.15, "spym": 0.50, "qqqm": 0.30, "soxx": 0.05}
# Bands are disclosure and transition-completion criteria, NOT no-trade zones.
# SOXX has no band; its criterion is a closed gap.
BANDS = {"cash": (0.10, 0.20), "spym": (0.45, 0.55), "qqqm": (0.25, 0.35)}
TICKERS = ("spym", "qqqm", "soxx")
CASH_TARGET = TARGETS["cash"]
# SOXX has no symmetric band: for a 5% position a symmetric band is meaningless,
# and being underweight is already caught by a positive gap. Overweight was not
# caught by anything — SOXX sits out of the band check and an overweight gap is
# zero — so it carries a disclosure-only ceiling. Crossing it reports; it never
# sells, and it never blocks a path.
SOXX_CEILING = 0.075
# Each tier releases a FIXED tranche of NAV, graded 1:2:3:4: the first shot
# stays small while most of the money lands at the deepest, best-priced
# entries. The four tranches sum to the cash target, so the ladder spends the
# cash out entirely.
TIERS = ((0.10, "T1", 0.0150),
         (0.15, "T2", 0.0300),
         (0.20, "T3", 0.0450),
         (0.25, "T4", 0.0600))
ABSOLUTE_FLOOR = 0.0     # cash never goes below this via drawdown deployment
LADDER = sum(t[2] for t in TIERS)   # 15pp: the whole cash position is ammunition
# The strategic baseline migrates surplus cash over a FIXED window: B = min(S/R, G)
# with R constant. Not a countdown to a date: a countdown needs stored state this
# system does not keep, and its final period (R = 1) deploys the entire remainder
# in one month — the lump sum the tranching rules forbid, and worst in the
# drawdown that creates the surplus. Held fixed, the surplus decays geometrically
# and no single month is ever a lump sum.
MIGRATION_MONTHS = 3
# DD is not fetched here. The registry names IBKR the source for the SPYM close
# series, and only the session can reach it; a script that quietly pulled an
# aggregator instead would be sourcing a tier trigger from an unregistered feed.
# The session reads the series, derives DD (market_context.py does this), and
# passes it with its as-of date. No --dd means tiers are not evaluated today —
# the registry localizes that failure and leaves every other path running.
MAX_DD_AGE_DAYS = 7


def dd_series_is_fresh(last_day: str, today: date) -> bool:
    """True when the supplied close is recent enough to define today's tier."""
    try:
        last = date.fromisoformat(str(last_day)[:10])
    except ValueError:
        return False
    return 0 <= (today - last).days <= MAX_DD_AGE_DAYS


def tier_release(dd: float, executed: set[str]) -> tuple[float, list[str]]:
    """Return (released weight, tiers consumed).

    Each newly triggered tier releases its own graded tranche of NAV — a fixed
    amount, not "everything above a floor". A single day may satisfy several
    tiers (a gap down straight through 25%); they fire shallow-to-deep, each
    once per cycle, and every one consumed must be recorded as EXECUTED or a
    later reconstruction would show a shallow tier still available.
    """
    fresh = [(name, tranche) for trigger, name, tranche in TIERS
             if dd >= trigger and name not in executed]
    return sum(tranche for _, tranche in fresh), [name for name, _ in fresh]


def allocate(amount: float, gaps: dict[str, float]) -> dict[str, float]:
    """Send money to the largest gap first, then spill into the next."""
    out = {name: 0.0 for name in gaps}
    if amount <= 0:
        return out
    remaining = amount
    for name, gap in sorted(gaps.items(), key=lambda kv: -kv[1]):
        if remaining <= 0:
            break
        take = min(remaining, max(gap, 0.0))
        out[name] = take
        remaining -= take
    return out


def within_band(name: str, weight: float) -> bool | None:
    """True/False against the published band; None where no band applies."""
    if name not in BANDS:
        return None
    low, high = BANDS[name]
    return low - 1e-12 <= weight <= high + 1e-12


def above_ceiling(name: str, weight: float) -> bool:
    """True when SOXX has drifted past its disclosure-only ceiling."""
    return name == "soxx" and weight > SOXX_CEILING + 1e-12


def portfolio_state(nav, cash, spym, qqqm, soxx, legacy=0.0):
    """Return allocation facts that remain valid before funding inputs exist.

    Daily review uses this subset when a broker capability is unavailable. It
    deliberately contains no funding-channel authorization: contribution,
    drawdown-cycle state and order gates still belong to the full computation.
    """
    values = {"spym": spym, "qqqm": qqqm, "soxx": soxx}
    weights = {name: values[name] / nav for name in TICKERS}
    weights["cash"] = cash / nav
    targets_usd = {name: TARGETS[name] * nav for name in TICKERS}
    # Drift above target yields a zero gap, never a sale: the rules repair
    # overweight by dilution from new money, not by rebalancing out.
    gaps = {name: max(targets_usd[name] - values[name], 0.0) for name in TICKERS}
    return {
        "values": values,
        "legacy": legacy,
        "weights": weights,
        "targets_usd": targets_usd,
        "gaps": gaps,
        "g0": sum(gaps.values()),
        "r": MIGRATION_MONTHS,
        "cash": cash,
    }


def routine_channels(nav, cash, state, contribution):
    """Compute Routine DCA and Strategic Baseline from authoritative F.

    Kept separate so Daily Review can calculate these channels without
    inventing drawdown-cycle inputs that are independently unavailable.
    """
    gaps = state["gaps"]
    d = min(contribution, state["g0"])
    d_alloc = allocate(d, gaps)
    cash_after_d = cash - d
    gaps_after_d = {name: gaps[name] - d_alloc[name] for name in TICKERS}
    g = sum(gaps_after_d.values())
    s = max(cash_after_d - CASH_TARGET * nav, 0.0)
    b = min(s / state["r"], g) if state["r"] else 0.0
    b_alloc = allocate(b, gaps_after_d)
    return {
        "d": d,
        "d_alloc": d_alloc,
        "cash_after_d": cash_after_d,
        "gaps_after_d": gaps_after_d,
        "g": g,
        "s": s,
        "b": b,
        "b_alloc": b_alloc,
    }


def compute(nav, cash, spym, qqqm, soxx, contribution, dd, executed,
            legacy=0.0):
    """Everything the monthly workflow needs. Pure function of its inputs."""
    state = portfolio_state(nav, cash, spym, qqqm, soxx, legacy)
    routine = routine_channels(nav, cash, state, contribution)

    b_alloc = routine["b_alloc"]
    gaps_after_db = {name: routine["gaps_after_d"][name] - b_alloc[name]
                     for name in TICKERS}
    released_w, consumed = tier_release(dd, executed)
    cash_after_db = routine["cash_after_d"] - routine["b"]
    # drawdown deployment: the released tranche(s), capped by cash above the
    # absolute floor and by the gap left after D and B
    dd_amount = min(released_w * nav,
                    max(cash_after_db - ABSOLUTE_FLOOR * nav, 0.0),
                    sum(gaps_after_db.values())) if consumed else 0.0
    dd_alloc = allocate(dd_amount, gaps_after_db)

    final_cash = cash_after_db - dd_amount
    # There is no percentage cash floor to enforce. The routine paths cannot
    # reach one: B <= S = max(cash - 15%V, 0) cannot take cash below the 15%
    # target, and D <= F cannot take it below the pre-contribution level. A
    # 12% line used to sit here and was unreachable under every input — a rule
    # that looks binding but never is, which is worse than no rule. What the
    # policy actually constrains is that cash never goes negative, and only
    # drawdown deployment can approach that; the tranche caps enforce it.
    # This bound is reported so the reader can see where cash could not go.
    start_cash_w = max(cash - contribution, 0.0) / nav
    structural_bound = 0.0 if consumed else min(CASH_TARGET, start_cash_w)
    return {
        "weights": state["weights"],
        "values": state["values"],
        "targets_usd": state["targets_usd"],
        "gaps": state["gaps"], "g0": state["g0"], "legacy": legacy,
        "d": routine["d"], "d_alloc": routine["d_alloc"],
        "cash_after_d": routine["cash_after_d"], "g": routine["g"],
        "r": state["r"], "s": routine["s"],
        "b": routine["b"], "b_alloc": b_alloc,
        "consumed": consumed, "released_w": released_w,
        "dd_amount": dd_amount, "dd_alloc": dd_alloc,
        "final_cash": final_cash, "final_cash_w": final_cash / nav,
        "start_cash_w": start_cash_w,
        "structural_bound_w": structural_bound,
        "cash_non_negative": final_cash >= -1e-9,
    }


def money(x: float) -> str:
    return f"{x:,.0f}"


def report(inp, res, dd, dd_as_of, ath_date, executed, tiers_known,
           contribution_known=True) -> list[str]:
    """Build the monthly report. Returns the list of blocking issues (empty = clean)."""
    nav = inp["nav"]
    issues = []

    print("=" * 72)
    print("月度执行计算 — 本输出只在聊天/终端呈现，按隐私规则永不落盘")
    print("=" * 72)

    print(f"\n[1] 权重、目标与正缺口（Constitution 定义）")
    print(f"  {'标的':<8}{'现权重':>9}{'目标':>9}{'带宽':>15}{'正缺口':>12}{'缺口(pp)':>11}")
    for name in TICKERS:
        band = BANDS.get(name)
        ok = within_band(name, res["weights"][name])
        band_txt = "—" if band is None else (
            f"{band[0]:.0%}-{band[1]:.0%} {'内' if ok else '外'}")
        print(f"  {name.upper():<8}{res['weights'][name]:>8.2%}{TARGETS[name]:>9.0%}"
              f"{band_txt:>15}{money(res['gaps'][name]):>12}"
              f"{res['gaps'][name]/nav*100:>10.2f}")
        if ok is False:
            issues_note = f"{name.upper()} 权重 {res['weights'][name]:.2%} 位于带宽外"
            print(f"           ** {issues_note} —— 披露项，不阻断例行路径 **")
        if above_ceiling(name, res["weights"][name]):
            print(f"           ** SOXX 权重 {res['weights'][name]:.2%} 超过 {SOXX_CEILING:.1%} 披露上沿"
                  f" —— 季度审核须记录；不卖出、不阻断，靠新增资金稀释修复 **")
    if res.get("legacy", 0.0) > 0:
        print(f"  {'LEGACY':<8}{res['legacy']/nav:>8.2%}{'—':>9}{'不适用':>15}"
              f"{'不适用':>12}{'—':>11}")
        print(f"           ** Legacy / Out-of-Universe —— 只披露、只持有，"
              f"不进目标缺口、不获得任何通道资金、不自动卖出 **")
    cash_ok = within_band("cash", res["weights"]["cash"])
    cband = BANDS["cash"]
    print(f"  {'CASH':<8}{res['weights']['cash']:>8.2%}{TARGETS['cash']:>9.0%}"
          f"{f'{cband[0]:.0%}-{cband[1]:.0%} ' + ('内' if cash_ok else '外'):>15}"
          f"{'—':>12}{'—':>11}")
    print(f"  G_0 = {money(res['g0'])}  ({res['g0']/nav*100:.2f} pp of NAV)")

    print(f"\n[2] 回撤部署档位")
    if dd is None:
        print("  DD 不可得 → 本月不评估分档（不影响 D / B）")
        issues.append("回撤序列不可得：当日不评估分档")
    else:
        print(f"  SPYM DD = {dd:.2%}  (收盘 {dd_as_of}，ATH收盘 {ath_date})")
        if not tiers_known:
            print("  ** 未提供 --tiers-executed：无法确认本周期各档是否已执行 **")
            print("     按 05-state.md 第 4 步用成交记录重建后重跑")
            issues.append("回撤档位已执行状态未知")
        for trigger, name, tranche in TIERS:
            mark = "已执行" if name in executed else ("**达档可用**" if dd >= trigger else "未达档")
            print(f"    {name}  触发 {trigger:>3.0%}  释放 {tranche:>5.2%} of NAV   {mark}")
        if res["consumed"]:
            print(f"  → 本次消耗档位 {', '.join(res['consumed'])}，共释放 {res['released_w']:.1%} of NAV"
                  f"（绝对下限 {ABSOLUTE_FLOOR:.0%}）")
            print(f"     全部消耗档位必须由 IBKR 成交记录确认，并更新 IBKR 警报指针")

    print(f"\n[3] 三条资金通道（都只买正缺口，三个标的同等对待）")
    if not contribution_known:
        print(f"  Routine DCA   ** 未提供 --contribution：本月已到账外部净入金 F 未知 **")
        print(f"                  按 05-state.md 第 5 步读 IBKR Cash Transactions 后重跑；")
        print(f"                  无入金的月份也须显式传 --contribution 0")
        print(f"                  → D = DATA INCOMPLETE（不静默按 F=0 部署）")
        issues.append("本月实际入金 F 未知：Routine DCA 无法确认（补 --contribution 后重跑）")
    else:
        print(f"  Routine DCA   D = min(F={money(inp['contribution'])}, G_0={money(res['g0'])}) = {money(res['d'])}")
        print(f"                  → " + " ｜ ".join(
            f"{n.upper()} {money(res['d_alloc'][n])}" for n in TICKERS))
    print(f"  Strategic     R = {res['r']}（固定迁移期数，每月按最新数据重算）")
    print(f"                  S = max(C − 15%×V, 0) = {money(res['s'])}")
    print(f"                  B = min(S/R={money(res['s']/res['r'])}, G={money(res['g'])}) = {money(res['b'])}")
    print(f"                  → " + " ｜ ".join(
        f"{n.upper()} {money(res['b_alloc'][n])}" for n in TICKERS))
    if res["consumed"]:
        print(f"  Drawdown      {'+'.join(res['consumed'])} 部署 = {money(res['dd_amount'])}")
        print(f"                  → " + " ｜ ".join(
            f"{n.upper()} {money(res['dd_alloc'][n])}" for n in TICKERS))
    else:
        print(f"  Drawdown      0（未达档或该档本周期已执行）")

    total = res["d"] + res["b"] + res["dd_amount"]
    print(f"\n[4] 例行路径检查")
    cash_label = (
        f"交易后现金 {res['final_cash_w']:.2%}"
        f"（本月结构下界 {res['structural_bound_w']:.2%}"
        + ("：档位已触发，下界即绝对下限 0%" if res["consumed"]
           else f"，取 15% 目标与月初入金前水位 {res['start_cash_w']:.2%} 的较低者）")
        + ("" if res["consumed"] else "")
    )
    checks = [
        ("只买 Production 标的的正缺口", True),
        ("金额完全由已发布公式产生", True),
        ("不使用融资：交易后现金不为负", res["cash_non_negative"]),
        ("没有重复或冲突订单", inp.get("open_orders_status") == "clear"),
    ]
    for label, ok in checks:
        print(f"  [{'x' if ok else ' '}] {label}")
        if not ok:
            issues.append(label)
    print(f"  ·   {cash_label}")

    print(f"\n[5] 结论")
    if issues:
        print(f"  DATA INCOMPLETE / HOLD —— 以下项未通过，升级为完整 IC 或停止：")
        for i in issues:
            print(f"    - {i}")
    elif total < 1.0:
        print(f"  HOLD —— 本月无正缺口或无可部署资金。无操作是有效结果。")
    else:
        print(f"  BUY CANDIDATE —— 合计 {money(total)}（{total/nav*100:.2f} pp of NAV）")
        for name in TICKERS:
            amt = res["d_alloc"][name] + res["b_alloc"][name] + res["dd_alloc"][name]
            if amt >= 1.0:   # below 1 unit is float residue, not a real candidate
                print(f"    {name.upper()}  {money(amt)}")
        print(f"  交易后现金 {res['final_cash_w']:.2%}（本月结构下界 {res['structural_bound_w']:.2%}）")
        print(f"\n  本结论不是下单授权。数量、限价与有效期由账户所有者在 IBKR 人工确定并确认。")
    return issues


def self_test() -> None:
    """Assert the arithmetic mirrors the published rules. Run with --self-test."""
    # 1. the four targets are explicit and close to exactly 100%
    assert abs(sum(TARGETS.values()) - 1.0) < 1e-12, "targets do not sum to 100%"
    for name, (low, high) in BANDS.items():
        assert low < TARGETS[name] < high, f"{name} band does not bracket its target"
    assert "soxx" not in BANDS, "SOXX must not carry a band"

    # 2. D never exceeds F nor G_0
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 5_000, 0.0, set())
    assert r["d"] <= 5_000 + 1e-9 and r["d"] <= r["g0"] + 1e-9, "D exceeded min(F, G_0)"

    # 3. every channel conserves money across the three tickers
    total = r["d"] + r["b"] + r["dd_amount"]
    parts = sum(r["d_alloc"][n] + r["b_alloc"][n] + r["dd_alloc"][n] for n in TICKERS)
    assert abs(total - parts) < 1e-6, "allocation lost or created money"

    # 4. B never exceeds the remaining gap
    assert r["b"] <= r["g"] + 1e-9, "B exceeded G"

    # 5. no drawdown deployment below a tier trigger
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.09, set())
    assert r["dd_amount"] == 0 and not r["consumed"], "deployed below the T1 trigger"

    # 6. an already-executed tier must not re-authorize (once per cycle).
    # At DD 12% only T1 qualifies, and it already fired -> nothing releases.
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.12, {"T1"})
    assert r["dd_amount"] == 0 and not r["consumed"], "executed tier re-authorized deployment"
    # but deeper tiers stay available: at DD 20%, T2 and T3 still release
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.20, {"T1"})
    assert r["consumed"] == ["T2", "T3"], f"deeper tiers blocked: {r['consumed']}"

    # 7. a gap-down day consumes every tier it passes through, shallow-to-deep
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.28, set())
    assert r["consumed"] == ["T1", "T2", "T3", "T4"], f"wrong tiers consumed: {r['consumed']}"

    # 7b. graded tranching: the tiers take cash from the 15% target exactly to 0
    assert abs(LADDER + ABSOLUTE_FLOOR - CASH_TARGET) < 1e-12, \
        "the tranches must take cash from the cash target exactly to the absolute floor"
    assert all(b[2] > a[2] for a, b in zip(TIERS, TIERS[1:])), \
        "tranches must grow strictly with depth"

    # 7c. the ladder ends at 25%. Past T4 the ammunition is spent by design,
    # so a deeper fall authorizes nothing — this is the decision, not an oversight.
    deep = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.45, set())
    assert deep["consumed"] == ["T1", "T2", "T3", "T4"], \
        f"a 45% fall must consume the whole ladder and no more: {deep['consumed']}"
    spent = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.45,
                    {"T1", "T2", "T3", "T4"})
    assert spent["dd_amount"] == 0 and not spent["consumed"], \
        "a spent ladder must authorize nothing however deep the fall"

    # 8. the two structural cash bounds. There is no percentage floor gate: the
    # formulas make one unreachable, so the properties it pretended to enforce
    # are asserted directly instead — a check that can fail, not a tautology.
    # 8a. no routine path takes cash below the 15% target or below the level it
    # started at before this month's contribution, whichever is lower.
    for cash_w in (0.05, 0.12, 0.15, 0.20, 0.41, 0.60):
        for f in (0.0, 1_500.0, 15_000.0):
            cash = cash_w * 100_000
            r = compute(100_000 + f, cash + f, 30_000, 15_000, 6_000, f, 0.0, set())
            assert r["final_cash_w"] >= r["structural_bound_w"] - 1e-9, \
                f"routine path pierced the structural bound at cash {cash_w}, F {f}"
    # 8b. cash never goes negative, at any depth, with any tiers already spent
    for dd, ex in ((0.0, set()), (0.11, set()), (0.28, set()), (0.40, set()), (0.28, {"T1"})):
        r = compute(100_000, 30_000, 30_000, 15_000, 6_000, 3_000, dd, ex)
        assert r["cash_non_negative"], f"cash went negative at DD {dd}"

    # 9. the baseline deploys a fixed fraction of the surplus, never all of it
    assert MIGRATION_MONTHS >= 2, "R = 1 collapses B into min(S, G): a lump sum"
    surplus = compute(100_000, 25_000, 45_000, 25_000, 5_000, 0, 0.0, set())
    assert surplus["s"] > 0, "fixture must carry a strategic surplus"
    assert abs(surplus["b"] - surplus["s"] / MIGRATION_MONTHS) < 1e-9, \
        "B must be S/R where the gap does not bind"
    assert surplus["b"] < surplus["s"], \
        f"baseline deployed as a lump sum: {surplus['b']} of {surplus['s']}"

    # 10. SOXX is an ordinary holding: its gap is funded by the same channels.
    r = compute(100_000, 20_000, 50_000, 30_000, 2_000, 5_000, 0.0, set())
    assert abs(r["gaps"]["soxx"] - 3_000) < 1e-6, f"SOXX gap miscomputed: {r['gaps']}"
    assert abs(r["d_alloc"]["soxx"] - 3_000) < 1e-6, \
        f"routine DCA must fund the SOXX gap like any other: {r['d_alloc']}"

    # 11. drift above target yields no gap and no sale — repaired by dilution
    r = compute(100_000, 20_000, 60_000, 30_000, 5_000, 5_000, 0.0, set())
    assert r["gaps"]["spym"] == 0.0, "overweight SPYM must not produce a gap"
    assert r["d"] == 0.0 and r["g0"] == 0.0, "nothing to buy when every ticker is at or above target"
    assert all(v >= 0.0 for v in r["gaps"].values()), "a gap must never go negative"

    # 11b. a Legacy holding reconciles but never receives funding and never
    # creates a target or a gap — otherwise any account holding one is stuck.
    from account_reconciliation import reconcile_nav as _rec
    # the Legacy leg must be large enough that dropping it breaches the 0.5%
    # tolerance, or the fixture proves nothing
    assert _rec(100_000, 20_000, (50_000, 28_000, 1_000, 1_000)).passed, \
        "Legacy must be able to close the reconciliation equation"
    assert not _rec(100_000, 20_000, (50_000, 28_000, 1_000)).passed, \
        "fixture must actually depend on the Legacy leg"
    plain = compute(100_000, 20_000, 50_000, 28_000, 1_000, 5_000, 0.0, set())
    withleg = compute(100_000, 20_000, 50_000, 28_000, 1_000, 5_000, 0.0, set(),
                      legacy=1_000)
    for key in ("d", "b", "dd_amount", "g0"):
        assert abs(plain[key] - withleg[key]) < 1e-9, f"Legacy displaced {key}"
    assert set(withleg["gaps"]) == set(TICKERS), "Legacy must not appear as a gap"

    # 12. a stale supplied close must not define today's tier
    assert dd_series_is_fresh("2026-07-30", date(2026, 8, 1)), "2-day-old close wrongly stale"
    assert dd_series_is_fresh("2026-07-25", date(2026, 8, 1)), "boundary 7-day close wrongly stale"
    assert not dd_series_is_fresh("2026-07-24", date(2026, 8, 1)), "8-day-old close wrongly fresh"
    assert not dd_series_is_fresh("garbage", date(2026, 8, 1)), "unparseable date wrongly fresh"
    assert not dd_series_is_fresh("2026-09-01", date(2026, 8, 1)), "future-dated close wrongly fresh"

    # 13. deployment-framework §2: after a deployment, cash rebuilds only from
    # external contributions and the Routine DCA must not pause for it. A month
    # that STARTS below the normal floor because tranches fired earlier in the
    # cycle is a rebuild state, not a violation — the floor gate must pass it.
    r = compute(100_000, 11_000, 55_000, 28_500, 4_900, 0, 0.17, {"T1", "T2"})
    assert r["final_cash_w"] < CASH_TARGET, "rebuild fixture must sit below the cash target"
    assert r["cash_non_negative"], "post-deployment rebuild month drove cash negative"
    # and a contribution flowing through D returns cash to its pre-F level —
    # the DCA runs, and that is still not a breach
    r = compute(100_000, 11_500, 55_000, 28_000, 4_900, 2_000, 0.18, {"T1", "T2"})
    assert r["d"] > 0, "rebuild fixture must exercise the DCA path"
    assert r["final_cash"] >= (11_500 - 2_000) - 1e-9, \
        "DCA spent more than the contribution: it must never dig into existing cash"

    # 14. band classification matches the published edges
    assert within_band("cash", 0.15) and within_band("cash", 0.10) and within_band("cash", 0.20)
    assert not within_band("cash", 0.0999) and not within_band("cash", 0.2001)
    assert within_band("soxx", 0.05) is None, "SOXX must report no band"

    # 15. SOXX overweight is visible. Without the ceiling nothing reports it:
    # it is outside the band check and an overweight position has a zero gap.
    assert SOXX_CEILING > TARGETS["soxx"], "the ceiling must sit above the target"
    assert not above_ceiling("soxx", TARGETS["soxx"]), "at target is not above the ceiling"
    assert not above_ceiling("soxx", SOXX_CEILING), "the ceiling edge is inside"
    assert above_ceiling("soxx", SOXX_CEILING + 1e-6), "just past the ceiling must report"
    assert not above_ceiling("spym", 0.99), "the ceiling applies to SOXX alone"
    drift = compute(100_000, 20_000, 45_000, 27_000, 8_000, 0, 0.0, set())
    assert drift["gaps"]["soxx"] == 0.0, "overweight SOXX still yields no gap"
    assert above_ceiling("soxx", drift["weights"]["soxx"]), \
        "an 8% SOXX position must trip the ceiling that the gap cannot"

    print("monthly_execution self-test passed (15 invariants)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nav", type=float, help="IBKR Net Liquidation（入金后、交易前）")
    ap.add_argument("--cash", type=float, help="IBKR Total Cash（含本月已到账 F）")
    ap.add_argument("--spym", type=float, help="SPYM 市值")
    ap.add_argument("--qqqm", type=float, help="QQQM 市值")
    ap.add_argument("--soxx", type=float, default=0.0, help="SOXX 市值")
    ap.add_argument("--legacy", type=float, default=0.0,
                    help="Legacy / Out-of-Universe 持仓市值合计。进入对账，但不参与目标、缺口或任何资金通道")
    ap.add_argument("--contribution", type=float, default=None,
                    help="F：本月已到账外部净入金；无入金也须显式传 0（省略即 DATA INCOMPLETE，不静默按 F=0）")
    ap.add_argument("--dd", type=float, default=None,
                    help="SPYM 相对历史最高收盘的回撤（小数），来自 IBKR 收盘序列。省略则本月不评估分档")
    ap.add_argument("--dd-as-of", default=None,
                    help="该回撤对应的最后一个已完成日线收盘日期 YYYY-MM-DD")
    ap.add_argument("--ath", type=float, default=None,
                    help="该回撤所依据的历史最高收盘。只作披露，使输出可反查 DD 的基准")
    ap.add_argument("--tiers-executed", default=None,
                    help="本回撤周期内已执行的档位，逗号分隔，如 T1 或 T1,T2；无则填 none")
    ap.add_argument("--open-orders-status", choices=("clear", "conflicting", "unknown"), default="unknown",
                    help="权威订单核查结果；只有 clear 允许月度候选，省略即 unknown 并失败关闭")
    ap.add_argument("--today", default=None,
                    help="判定回撤收盘新鲜度用的日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--self-test", action="store_true", help="校验算术是否镜像规则")
    # parse_args, not parse_known_args: an unrecognized flag must fail loudly
    # rather than be silently swallowed by the caller.
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0

    missing = [f for f in ("nav", "cash", "spym", "qqqm") if getattr(args, f) is None]
    if missing:
        ap.error(f"缺少必填输入 {', '.join('--' + m for m in missing)}（或用 --self-test）")
    for name in ("nav", "cash", "spym", "qqqm", "soxx", "legacy"):
        if getattr(args, name) < 0:
            print(f"DATA INCOMPLETE: {name} 不能为负", file=sys.stderr)
            return 2
    # F is fail-closed: omitting it must not silently deploy the DCA path on F=0.
    contribution_known = args.contribution is not None
    if contribution_known and args.contribution < 0:
        print("DATA INCOMPLETE: contribution 不能为负", file=sys.stderr)
        return 2
    if args.nav <= 0:
        print("DATA INCOMPLETE: NAV 必须为正", file=sys.stderr)
        return 2
    if args.dd is not None and not (0.0 <= args.dd < 1.0):
        print(
            "DATA INCOMPLETE: --dd 必须使用小数且范围为 [0, 1)；例如 1.68% 应传 0.0168",
            file=sys.stderr,
        )
        return 2
    # Legacy holdings are positions: leaving them out of the equation makes any
    # account that holds one fail reconciliation permanently. They reconcile,
    # and they do nothing else — no target, no gap, no channel (00-constitution
    # part 2 section 3: disclose separately, never fold into a production ticker).
    reconciliation = reconcile_nav(
        args.nav, args.cash, (args.spym, args.qqqm, args.soxx, args.legacy))
    if not reconciliation.passed:
        print(f"DATA INCOMPLETE: {reconciliation.issue}", file=sys.stderr)
        return 2
    if args.open_orders_status != "clear":
        print(
            f"DATA INCOMPLETE: open orders status is {args.open_orders_status}; "
            "must be clear before monthly candidates",
            file=sys.stderr,
        )
        return 2

    today = date.fromisoformat(args.today) if args.today else date.today()

    dd, dd_as_of, ath_date = args.dd, args.dd_as_of or "未标注", args.ath or "未提供"
    if dd is None:
        print("提示：未提供 --dd —— 本月不评估回撤分档，D / B 不受影响\n", file=sys.stderr)
    elif args.dd_as_of is None:
        print("警告：提供了 --dd 但没有 --dd-as-of，无法确认收盘新鲜度"
              "——本月不评估分档，D / B 不受影响\n", file=sys.stderr)
        dd = None
    elif not dd_series_is_fresh(args.dd_as_of, today):
        print(f"警告：回撤对应收盘 {args.dd_as_of} 超过 {MAX_DD_AGE_DAYS} 天或日期无效"
              "——按注册表局部化规则，本月不评估分档，D / B 不受影响\n", file=sys.stderr)
        dd = None

    tiers_known = args.tiers_executed is not None
    executed = set()
    if tiers_known and args.tiers_executed.strip().lower() not in ("none", ""):
        executed = {t.strip().upper() for t in args.tiers_executed.split(",")}
        bad = executed - {name for _, name, _t in TIERS}
        if bad:
            print(f"DATA INCOMPLETE: 未知档位 {bad}", file=sys.stderr)
            return 2
    # unknown tier state must not silently authorize deployment
    effective_dd = dd if (dd is not None and tiers_known) else None

    inp = vars(args) | {"nav": args.nav}
    res = compute(args.nav, args.cash, args.spym, args.qqqm, args.soxx,
                  args.contribution if contribution_known else 0.0,
                  effective_dd if effective_dd is not None else 0.0,
                  executed, args.legacy)
    issues = report(inp, res, dd, dd_as_of, ath_date, executed, tiers_known,
                    contribution_known)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
