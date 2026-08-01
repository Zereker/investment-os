#!/usr/bin/env python3
"""Compute the month's funding decision from live account inputs — an executable
mirror of the published funding rules.

Why this exists: the thresholds have an executable mirror (check_policy_consistency.py)
and the drawdown state machine has a drill (drawdown_drill.py), but the *funding
computation* had none. Every month it was hand-derived from the docs, which is slow
(the target is 20 minutes) and lets two agents reach two different answers. This
closes that gap: same inputs -> same answer, every time.

Mirrors (any divergence from these files is a BUG in this script, not a new rule):
  01-Constitution/Target-Allocation.md      targets, A_basis/U, guardrails, tiers
  02-Operating-System/Deployment-Framework.md   D / S / B / drawdown deployment
  02-Operating-System/Monthly-Workflow.md   seven-step order and routine-path checks

Hard boundaries this script will not cross:
  - It NEVER places or formats an executable order. Output is the published
    vocabulary only: HOLD / BUY CANDIDATE / REVIEW / DATA INCOMPLETE.
  - It NEVER writes account figures to disk. Values live in argv and stdout,
    never in the repo (public-repo privacy red line).
  - It NEVER invents inputs. Positions and NAV must come from IBKR; a missing
    input yields DATA INCOMPLETE, not a guess.
  - Which drawdown tiers already fired this cycle cannot be derived from price.
    Pass --tiers-executed; omitting it makes the script say so rather than assume.

Usage (figures come from IBKR, in account currency; they are never persisted):
  python3 scripts/monthly_execution.py --nav 100000 --cash 18000 \\
      --spym 50000 --qqqm 26000 --soxx 6000 --contribution 2000

  # already deployed T1 earlier in this drawdown cycle:
  python3 scripts/monthly_execution.py ... --tiers-executed T1

  # skip the network call for the drawdown check (offline / IBKR series preferred):
  python3 scripts/monthly_execution.py ... --dd 0.0
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
HISTORY_API = "https://stockanalysis.com/api/symbol/e/{sym}/history?range=10Y&period=Daily"

# --- Constitution constants. Changing these here changes nothing in the rules;
# --- they must be edited in Target-Allocation.md first (red line 5).
CASH_TARGET = 0.15
CASH_FLOOR = 0.12
QQQM_TARGET = 0.28
SLEEVE_57 = 0.57
A_STAGE = 0.06
A_EXECUTION_CAP = 0.03
TIERS = ((0.15, 0.10, "T1"), (0.25, 0.08, "T2"), (0.35, 0.06, "T3"))
PLAN_END = (2028, 12)  # strategic baseline planned completion month


def months_remaining(today: date) -> int:
    """R: monthly execution slots left through PLAN_END inclusive, minimum 1."""
    n = (PLAN_END[0] - today.year) * 12 + (PLAN_END[1] - today.month) + 1
    return max(n, 1)


def fetch_drawdown(symbol: str = "spym") -> tuple[float, str, str]:
    """Return (DD, as_of, ath_date) from the aggregator daily closes."""
    url = HISTORY_API.format(sym=symbol)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as resp:
        rows = json.loads(resp.read().decode()).get("data")
    if not rows:
        raise RuntimeError(f"no history for {symbol}")
    series = sorted((r["t"], float(r["c"])) for r in rows)
    ath = 0.0
    ath_date = series[0][0]
    for day, close in series:
        if close > ath:
            ath, ath_date = close, day
    last_day, last_close = series[-1]
    return (ath - last_close) / ath, last_day, ath_date


def authorized_cash_floor(dd: float, executed: set[str], reserve: float) -> tuple[float, list[str]]:
    """Lowest floor the drawdown clause authorizes, and EVERY tier consumed to get there.

    A single day may satisfy several tiers (a gap down straight through 25%).
    The Constitution fires them shallow-to-deep, each once per cycle. Deploying to
    the deepest floor subsumes the shallower ones numerically, but all of them are
    consumed and must be recorded as EXECUTED — otherwise a later reconstruction
    would show a shallow tier still available.
    """
    floor = CASH_FLOOR
    consumed = []
    for trigger, tier_floor, name in TIERS:      # TIERS is shallow-to-deep
        if dd >= trigger and name not in executed:
            consumed.append(name)
            floor = min(floor, tier_floor)
    return floor + reserve, consumed


def compute(nav, cash, spym, qqqm, soxx, contribution, dd, executed, today):
    """Everything the monthly workflow needs. Pure function of its inputs."""
    a_actual = soxx / nav
    a_basis = max(a_actual, A_STAGE)
    reserve = max(A_STAGE - a_actual, 0.0)          # U

    spym_target = nav * (SLEEVE_57 - a_basis)
    qqqm_target = nav * QQQM_TARGET
    gap_spym = max(spym_target - spym, 0.0)
    gap_qqqm = max(qqqm_target - qqqm, 0.0)
    g0 = gap_spym + gap_qqqm                        # G_0

    d = min(contribution, g0)                       # D = min(F, G_0)
    # D is allocated to the larger gap first
    d_spym, d_qqqm = allocate(d, gap_spym, gap_qqqm)
    cash_after_d = cash - d                         # C
    g = (gap_spym - d_spym) + (gap_qqqm - d_qqqm)   # G

    r = months_remaining(today)
    s = max(cash_after_d - (CASH_TARGET + reserve) * nav, 0.0)   # S
    b = min(s / r, g) if r else 0.0                              # B
    b_spym, b_qqqm = allocate(b, gap_spym - d_spym, gap_qqqm - d_qqqm)

    floor_w, consumed = authorized_cash_floor(dd, executed, reserve)
    cash_after_db = cash_after_d - b
    # drawdown deployment: only the amount above the temporarily lowered floor,
    # capped by the Core gap left after D and B
    remaining_gap = g - b
    dd_amount = min(max(cash_after_db - floor_w * nav, 0.0), remaining_gap) if consumed else 0.0
    dd_spym, dd_qqqm = allocate(dd_amount, gap_spym - d_spym - b_spym, gap_qqqm - d_qqqm - b_qqqm)

    final_cash = cash_after_db - dd_amount
    return {
        "a_actual": a_actual, "a_basis": a_basis, "reserve": reserve,
        "spym_target": spym_target, "qqqm_target": qqqm_target,
        "gap_spym": gap_spym, "gap_qqqm": gap_qqqm, "g0": g0,
        "d": d, "d_spym": d_spym, "d_qqqm": d_qqqm,
        "cash_after_d": cash_after_d, "g": g, "r": r, "s": s,
        "b": b, "b_spym": b_spym, "b_qqqm": b_qqqm,
        "consumed": consumed, "floor_w": floor_w, "dd_amount": dd_amount,
        "dd_spym": dd_spym, "dd_qqqm": dd_qqqm,
        "final_cash": final_cash, "final_cash_w": final_cash / nav,
        "min_floor_w": CASH_FLOOR + reserve,
    }


def allocate(amount: float, gap_a: float, gap_b: float) -> tuple[float, float]:
    """Send money to the larger gap first, then spill into the other."""
    if amount <= 0:
        return 0.0, 0.0
    first_is_a = gap_a >= gap_b
    big, small = (gap_a, gap_b) if first_is_a else (gap_b, gap_a)
    to_big = min(amount, big)
    to_small = min(amount - to_big, small)
    return (to_big, to_small) if first_is_a else (to_small, to_big)


def money(x: float) -> str:
    return f"{x:,.0f}"


def report(inp, res, dd, dd_as_of, ath_date, executed, tiers_known) -> list[str]:
    """Build the monthly report. Returns the list of blocking issues (empty = clean)."""
    nav = inp["nav"]
    issues = []

    print("=" * 72)
    print("月度执行计算 — 本输出只在聊天/终端呈现，按隐私规则永不落盘")
    print("=" * 72)

    print(f"\n[1] 配置状态（Constitution 定义）")
    print(f"  A_actual = {res['a_actual']:.2%}   A_stage = {A_STAGE:.0%}   "
          f"A_execution_cap = {A_EXECUTION_CAP:.0%}")
    print(f"  A_basis  = {res['a_basis']:.2%}   U = {res['reserve']:.2%}")
    if res["a_actual"] > A_STAGE:
        print(f"  ** SOXX 超 6% 永久硬上限 {res['a_actual']-A_STAGE:+.2%} —— 追加绝对冻结，不自动卖出 **")
    elif res["a_actual"] > A_EXECUTION_CAP:
        print(f"  ** SOXX 高于当前执行上限 {A_EXECUTION_CAP:.0%} —— 冻结新增 **")

    print(f"\n[2] 袖套权重与正缺口")
    print(f"  {'袖套':<8}{'现权重':>9}{'动态目标':>10}{'正缺口':>12}{'缺口(pp)':>11}")
    for name, cur, tgt, gap in (
        ("SPYM", inp["spym"], res["spym_target"], res["gap_spym"]),
        ("QQQM", inp["qqqm"], res["qqqm_target"], res["gap_qqqm"]),
    ):
        print(f"  {name:<8}{cur/nav:>8.2%}{tgt/nav:>10.2%}{money(gap):>12}{gap/nav*100:>10.2f}")
    print(f"  {'SOXX':<8}{res['a_actual']:>8.2%}{'冻结' if res['a_actual']>A_EXECUTION_CAP else f'≤{A_EXECUTION_CAP:.0%}':>10}"
          f"{'不适用':>12}{'—':>11}")
    print(f"  {'Cash':<8}{inp['cash']/nav:>8.2%}{CASH_TARGET+res['reserve']:>10.2%}"
          f"{'—':>12}{'—':>11}")
    print(f"  G_0 = {money(res['g0'])}  ({res['g0']/nav*100:.2f} pp of NAV)")

    print(f"\n[3] 回撤部署档位")
    if dd is None:
        print("  DD 不可得 → 本月不评估分档（不影响 D / B）")
        issues.append("回撤序列不可得：当日不评估分档")
    else:
        print(f"  SPYM DD = {dd:.2%}  (收盘 {dd_as_of}，ATH {ath_date})")
        if not tiers_known:
            print("  ** 未提供 --tiers-executed：无法确认本周期各档是否已执行 **")
            print("     按 State-Reconstruction 第 4 步用三信号交叉 + IBKR 警报重建后重跑")
            issues.append("回撤档位已执行状态未知")
        for trigger, tier_floor, name in TIERS:
            mark = "已执行" if name in executed else ("**达档可用**" if dd >= trigger else "未达档")
            print(f"    {name}  触发 {trigger:.0%}  下限 {tier_floor:.0%}+U   {mark}")
        if res["consumed"]:
            print(f"  → 本次消耗档位 {', '.join(res['consumed'])}，现金下限临时降至 {res['floor_w']:.2%}")
            print(f"     全部消耗档位必须在 Journal 记为本周期 EXECUTED，并更新 IBKR 警报指针")

    print(f"\n[4] 三条资金通道")
    print(f"  Routine DCA   D = min(F={money(inp['contribution'])}, G_0={money(res['g0'])}) = {money(res['d'])}")
    print(f"                  → SPYM {money(res['d_spym'])} ｜ QQQM {money(res['d_qqqm'])}")
    print(f"  Strategic     R = {res['r']} 期至 2028-12")
    print(f"                  S = max(C − (15%+U)×V, 0) = {money(res['s'])}")
    print(f"                  B = min(S/R={money(res['s']/res['r'])}, G={money(res['g'])}) = {money(res['b'])}")
    print(f"                  → SPYM {money(res['b_spym'])} ｜ QQQM {money(res['b_qqqm'])}")
    if res["consumed"]:
        print(f"  Drawdown      {'+'.join(res['consumed'])} 部署 = {money(res['dd_amount'])}")
        print(f"                  → SPYM {money(res['dd_spym'])} ｜ QQQM {money(res['dd_qqqm'])}")
    else:
        print(f"  Drawdown      0（未达档或该档本周期已执行）")

    total = res["d"] + res["b"] + res["dd_amount"]
    print(f"\n[5] 例行路径检查")
    checks = [
        ("只买 SPYM / QQQM", True),
        ("金额完全由已发布公式产生", True),
        (f"交易后现金 {res['final_cash_w']:.2%} ≥ 现行下限 {res['floor_w']:.2%}",
         res["final_cash_w"] >= res["floor_w"] - 1e-9),
        ("不使用融资", res["final_cash"] >= -1e-9),
        ("SOXX 未通过例行路径获得追加", True),
    ]
    for label, ok in checks:
        print(f"  [{'x' if ok else ' '}] {label}")
        if not ok:
            issues.append(label)

    print(f"\n[6] 结论")
    if issues:
        print(f"  DATA INCOMPLETE / HOLD —— 以下项未通过，升级为完整 IC 或停止：")
        for i in issues:
            print(f"    - {i}")
    elif total < 1.0:
        print(f"  HOLD —— 本月无正缺口或无可部署资金。无操作是有效结果。")
    else:
        print(f"  BUY CANDIDATE —— 合计 {money(total)}（{total/nav*100:.2f} pp of NAV）")
        for name, amt in (("SPYM", res["d_spym"] + res["b_spym"] + res["dd_spym"]),
                          ("QQQM", res["d_qqqm"] + res["b_qqqm"] + res["dd_qqqm"])):
            if amt >= 1.0:   # below 1 unit is float residue, not a real candidate
                print(f"    {name}  {money(amt)}")
        print(f"  交易后现金 {res['final_cash_w']:.2%}（下限 {res['floor_w']:.2%}）")
        print(f"\n  本结论不是下单授权。数量、限价与有效期由账户所有者在 IBKR 人工确定并确认。")
    return issues


def self_test() -> None:
    """Assert the arithmetic mirrors the published rules. Run with --self-test."""
    d0 = date(2026, 8, 1)

    # 1. D never exceeds F nor G_0
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 5_000, 0.0, set(), d0)
    assert r["d"] <= 5_000 + 1e-9 and r["d"] <= r["g0"] + 1e-9, "D exceeded min(F, G_0)"

    # 2. money only ever goes to SPYM/QQQM; SOXX is never funded here
    total = r["d"] + r["b"] + r["dd_amount"]
    parts = (r["d_spym"] + r["b_spym"] + r["dd_spym"]) + (r["d_qqqm"] + r["b_qqqm"] + r["dd_qqqm"])
    assert abs(total - parts) < 1e-6, "allocation lost or created money"

    # 3. B never exceeds the remaining Core gap
    assert r["b"] <= r["g"] + 1e-9, "B exceeded G"

    # 4. no drawdown deployment below a tier trigger
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.14, set(), d0)
    assert r["dd_amount"] == 0 and not r["consumed"], "deployed below the T1 trigger"

    # 5. an already-executed tier must not re-authorize (once per cycle)
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.20, {"T1"}, d0)
    assert r["dd_amount"] == 0 and not r["consumed"], "executed tier re-authorized deployment"

    # 6. a gap-down day consumes every tier it passes through, shallow-to-deep
    r = compute(100_000, 20_000, 40_000, 20_000, 6_000, 0, 0.28, set(), d0)
    assert r["consumed"] == ["T1", "T2"], f"wrong tiers consumed: {r['consumed']}"

    # 7. cash never ends below the authorized floor
    for dd, ex in ((0.0, set()), (0.16, set()), (0.28, set()), (0.40, set()), (0.28, {"T1"})):
        r = compute(100_000, 30_000, 30_000, 15_000, 6_000, 3_000, dd, ex, d0)
        assert r["final_cash_w"] >= r["floor_w"] - 1e-9, f"cash pierced the floor at DD {dd}"

    # 8. targets close to 100% at any A_actual, including drift above the cap
    for soxx in (0, 3_000, 6_000, 7_800):
        r = compute(100_000, 15_000, 50_000, 28_000, soxx, 0, 0.0, set(), d0)
        total_w = (CASH_TARGET + r["reserve"]) + QQQM_TARGET + (SLEEVE_57 - r["a_basis"]) + r["a_actual"]
        assert abs(total_w - 1.0) < 1e-9, f"targets do not sum to 100% at SOXX={soxx}"

    # 9. R counts down to the planned completion month and floors at 1
    assert months_remaining(date(2028, 12, 1)) == 1, "R must be 1 in the final month"
    assert months_remaining(date(2029, 6, 1)) == 1, "R must floor at 1 past the plan end"
    assert months_remaining(date(2026, 8, 1)) == 29, "R miscounted"

    print("monthly_execution self-test passed (9 invariants)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nav", type=float, help="IBKR Net Liquidation（入金后、交易前）")
    ap.add_argument("--cash", type=float, help="IBKR Total Cash（含本月已到账 F）")
    ap.add_argument("--spym", type=float, help="SPYM 市值")
    ap.add_argument("--qqqm", type=float, help="QQQM 市值")
    ap.add_argument("--soxx", type=float, default=0.0, help="SOXX 市值")
    ap.add_argument("--contribution", type=float, default=0.0, help="F：本月已到账外部净入金")
    ap.add_argument("--dd", type=float, default=None,
                    help="SPYM 相对历史最高收盘的回撤（小数）。省略则联网自取")
    ap.add_argument("--tiers-executed", default=None,
                    help="本回撤周期内已执行的档位，逗号分隔，如 T1 或 T1,T2；无则填 none")
    ap.add_argument("--today", default=None, help="计算 R 用的日期 YYYY-MM-DD（默认今天）")
    ap.add_argument("--self-test", action="store_true", help="校验算术是否镜像规则")
    args, _ = ap.parse_known_args()
    if args.self_test:
        self_test()
        return 0

    missing = [f for f in ("nav", "cash", "spym", "qqqm") if getattr(args, f) is None]
    if missing:
        ap.error(f"缺少必填输入 {', '.join('--' + m for m in missing)}（或用 --self-test）")
    for name in ("nav", "cash", "spym", "qqqm", "soxx", "contribution"):
        if getattr(args, name) < 0:
            print(f"DATA INCOMPLETE: {name} 不能为负", file=sys.stderr)
            return 2
    if args.nav <= 0:
        print("DATA INCOMPLETE: NAV 必须为正", file=sys.stderr)
        return 2

    today = date.fromisoformat(args.today) if args.today else date.today()

    dd, dd_as_of, ath_date = args.dd, "手工传入", "—"
    if dd is None:
        try:
            dd, dd_as_of, ath_date = fetch_drawdown()
        except Exception as exc:
            print(f"警告：回撤序列拉取失败（{exc}）——本月不评估分档，D / B 不受影响\n",
                  file=sys.stderr)
            dd = None

    tiers_known = args.tiers_executed is not None
    executed = set()
    if tiers_known and args.tiers_executed.strip().lower() not in ("none", ""):
        executed = {t.strip().upper() for t in args.tiers_executed.split(",")}
        bad = executed - {n for _, _, n in TIERS}
        if bad:
            print(f"DATA INCOMPLETE: 未知档位 {bad}", file=sys.stderr)
            return 2
    # unknown tier state must not silently authorize deployment
    effective_dd = dd if (dd is not None and tiers_known) else None

    inp = vars(args) | {"nav": args.nav}
    res = compute(args.nav, args.cash, args.spym, args.qqqm, args.soxx,
                  args.contribution, effective_dd if effective_dd is not None else 0.0,
                  executed, today)
    issues = report(inp, res, dd, dd_as_of, ath_date, executed, tiers_known)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
