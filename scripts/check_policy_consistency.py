#!/usr/bin/env python3
"""Fail CI when Production policy formulas, state or guardrails diverge (v4.0)."""

from math import isfinite, nan, inf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = (0.06,)  # v4.0: 6% is the permanent hard cap; 10/12.5/15% stages are void
EXECUTION_CAPS = (0.03, 0.045, 0.06)
CURRENT_STAGE = 0.06
CURRENT_EXECUTION_CAP = 0.03
DRAWDOWN_TIERS = ((0.15, 0.10), (0.25, 0.08), (0.35, 0.06))  # (dd trigger, cash floor)
NORMAL_CASH_FLOOR = 0.12


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path}: missing required text: {needle}")


def forbid(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        if needle in text:
            raise AssertionError(f"{path}: forbidden stale text: {needle}")


def close_to_member(value: float, allowed: tuple[float, ...]) -> bool:
    return any(abs(value - item) <= 1e-12 for item in allowed)


def allocation(actual: float, stage: float, execution_cap: float) -> dict[str, float]:
    values = (actual, stage, execution_cap)
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) for value in values):
        raise ValueError("weights must be finite numbers")
    if not 0 <= actual <= 0.15:
        # actual may drift above the 6% cap (freeze, no auto-sell); 15% is a sanity bound
        raise ValueError("A_actual outside [0, 15%]")
    if not close_to_member(stage, STAGES):
        raise ValueError("illegal A_stage")
    if not close_to_member(execution_cap, EXECUTION_CAPS):
        raise ValueError("illegal A_execution_cap")
    if execution_cap > stage + 1e-12:
        raise ValueError("execution cap exceeds stage")

    basis = max(actual, stage)
    reserve = max(stage - actual, 0.0)
    targets = {
        "cash_base": 0.15,
        "stage_reserve": reserve,
        "qqqm": 0.28,
        "spym": 0.57 - basis,
        "soxx": actual,
    }
    if not all(0.0 <= value <= 1.0 for value in targets.values()):
        raise ValueError(f"target outside [0, 100%]: {targets}")
    if abs(sum(targets.values()) - 1.0) > 1e-12:
        raise ValueError(f"allocation does not sum to 100%: {targets}")
    return targets


def next_execution_cap(current: float, proposed: float) -> bool:
    if not (close_to_member(current, EXECUTION_CAPS) and close_to_member(proposed, EXECUTION_CAPS)):
        return False
    old = min(range(len(EXECUTION_CAPS)), key=lambda i: abs(EXECUTION_CAPS[i] - current))
    new = min(range(len(EXECUTION_CAPS)), key=lambda i: abs(EXECUTION_CAPS[i] - proposed))
    return new == old + 1


def allocation_tests() -> None:
    valid = [
        (0.00, 0.06, 0.03), (0.03, 0.06, 0.03), (0.045, 0.06, 0.045),
        (0.06, 0.06, 0.06), (0.078, 0.06, 0.03),  # drift above cap: freeze, math still closes
    ]
    for args in valid:
        allocation(*args)

    invalid = [
        (-0.01, 0.06, 0.03), (0.16, 0.06, 0.06), (nan, 0.06, 0.03),
        (inf, 0.06, 0.03), (0.03, 0.10, 0.03), (0.03, 0.15, 0.06),
        (0.03, 0.06, 0.04), (0.03, 0.06, 0.10), (True, 0.06, 0.03),
    ]
    for args in invalid:
        try:
            allocation(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"illegal allocation accepted: {args}")

    if not next_execution_cap(0.03, 0.045):
        raise AssertionError("next checkpoint rejected")
    if not next_execution_cap(0.045, 0.06):
        raise AssertionError("next checkpoint rejected")
    for proposed in (0.03, 0.06, 0.10, 0.15, nan):
        if next_execution_cap(0.03, proposed):
            raise AssertionError(f"illegal checkpoint transition accepted: 3% -> {proposed}")


def drawdown_cash_floor(dd: float, executed: set[float] | None = None) -> float:
    """Return the currently authorized cash floor for a drawdown level."""
    if not isinstance(dd, (int, float)) or isinstance(dd, bool) or not isfinite(dd):
        raise ValueError("drawdown must be a finite number")
    if not 0 <= dd <= 1:
        raise ValueError("drawdown outside [0, 100%]")
    executed = executed or set()
    floor = NORMAL_CASH_FLOOR
    for trigger, tier_floor in DRAWDOWN_TIERS:
        if dd >= trigger and trigger not in executed:
            floor = min(floor, tier_floor)
    return floor


def drawdown_tests() -> None:
    if drawdown_cash_floor(0.0) != NORMAL_CASH_FLOOR:
        raise AssertionError("no-drawdown floor must be the normal 12% floor")
    if drawdown_cash_floor(0.149999) != NORMAL_CASH_FLOOR:
        raise AssertionError("below-tier drawdown must not unlock deployment")
    expected = {0.15: 0.10, 0.2499: 0.10, 0.25: 0.08, 0.3499: 0.08, 0.35: 0.06, 1.0: 0.06}
    for dd, floor in expected.items():
        if abs(drawdown_cash_floor(dd) - floor) > 1e-12:
            raise AssertionError(f"wrong cash floor at drawdown {dd}")
    # once-per-cycle: an executed tier no longer lowers the floor
    if drawdown_cash_floor(0.20, executed={0.15}) != NORMAL_CASH_FLOOR:
        raise AssertionError("executed tier must not re-authorize deployment")
    if abs(drawdown_cash_floor(0.30, executed={0.15}) - 0.08) > 1e-12:
        raise AssertionError("deeper tier must stay available after shallower executed")
    for invalid in (-0.01, 1.01, nan, inf, True):
        try:
            drawdown_cash_floor(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"illegal drawdown accepted: {invalid}")
    # tiers must be strictly monotone
    triggers = [t for t, _ in DRAWDOWN_TIERS]
    floors = [f for _, f in DRAWDOWN_TIERS]
    if triggers != sorted(triggers) or floors != sorted(floors, reverse=True):
        raise AssertionError("drawdown tiers must deepen monotonically")


import re


PRIVACY_PATTERNS = (
    (re.compile(r"\$\s?\d"), "dollar amount ($N)"),
    (re.compile(r"\d[\d,]*(?:\.\d+)?\s*美元"), "CNY-written dollar amount (N美元)"),
    (re.compile(r"\d\s*万美元"), "dollar amount (N万美元)"),
    (re.compile(r"\d+(?:\.\d+)?\s*股(?![票市权价东])"), "share count (N股)"),
    (re.compile(r"(?i)\bnav\b\s*[:=≈]\s*\$?\d"), "NAV figure"),
)


def privacy_gate() -> None:
    """Public-repo red line: no account-derivable figures in any tracked Markdown."""
    violations = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), 1):
            for pattern, label in PRIVACY_PATTERNS:
                if pattern.search(line):
                    violations.append(f"{path.relative_to(ROOT)}:{lineno}: {label}: {line.strip()[:80]}")
    if violations:
        raise AssertionError("privacy gate failed:\n" + "\n".join(violations))


def benchmark_interest_tests() -> None:
    principal = 20_000.0
    accrued = 0.0
    rate = 0.036
    first = max(principal - 10_000.0, 0.0) * rate / 360.0
    accrued += first
    second = max(principal - 10_000.0, 0.0) * rate / 360.0
    if abs(first - second) > 1e-12:
        raise AssertionError("unposted accrual compounded")
    nav_before_posting = principal + accrued
    posting = accrued
    principal += posting
    accrued -= posting
    if abs((principal + accrued) - nav_before_posting) > 1e-12:
        raise AssertionError("posting conversion changed benchmark NAV")


def valuation_tier(percentile: float) -> str:
    if not isinstance(percentile, (int, float)) or isinstance(percentile, bool) or not isfinite(percentile):
        raise ValueError("valuation percentile must be finite")
    if not 0 <= percentile <= 100:
        raise ValueError("valuation percentile outside [0, 100]")
    if percentile < 20:
        return "CHEAP"
    if percentile < 70:
        return "FAIR"
    if percentile < 90:
        return "EXPENSIVE"
    return "VERY EXPENSIVE"


def valuation_action(tier: str) -> tuple[bool, bool, bool]:
    """v4.0 mapping: (D allowed, B allowed, T allowed).

    D is never valuation-gated; B pauses only at VERY EXPENSIVE; T requires CHEAP.
    """
    actions = {
        "CHEAP": (True, True, True),
        "FAIR": (True, True, False),
        "EXPENSIVE": (True, True, False),
        "VERY EXPENSIVE": (True, False, False),
        "N/A": (True, True, False),
    }
    if tier not in actions:
        raise ValueError("unknown valuation tier")
    return actions[tier]


def valuation_policy_tests() -> None:
    expected = {
        0: "CHEAP", 19.999: "CHEAP", 20: "FAIR", 69.999: "FAIR",
        70: "EXPENSIVE", 89.999: "EXPENSIVE", 90: "VERY EXPENSIVE",
        100: "VERY EXPENSIVE",
    }
    for percentile, tier in expected.items():
        if valuation_tier(percentile) != tier:
            raise AssertionError(f"wrong valuation tier at {percentile}")
    for invalid in (-0.01, 100.01, nan, inf, True):
        try:
            valuation_tier(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"illegal valuation percentile accepted: {invalid}")
    for tier in ("CHEAP", "FAIR", "EXPENSIVE", "VERY EXPENSIVE", "N/A"):
        d, b, t = valuation_action(tier)
        if not d:
            raise AssertionError(f"{tier}: D must never be valuation-gated in v4.0")
        if t and tier != "CHEAP":
            raise AssertionError(f"{tier}: T requires CHEAP")
    if valuation_action("VERY EXPENSIVE")[1]:
        raise AssertionError("VERY EXPENSIVE must pause B")
    if not valuation_action("N/A")[1]:
        raise AssertionError("N/A must not block B (BUG-007 regression)")


def main() -> None:
    dictionary = "08-Data/DATA_DICTIONARY.md"
    require(
        dictionary,
        r"SPYM \(57\%-A_{basis}\)",
        r"\(D_{max}=\min(F,G_0)\)",
        r"\(S=\max(C-(15\%+U)\times V,0)\)",
        r"P_{B,m,0}+A_{B,m,0}=15\%\times V_{B,m,0}",
        r"E_{B,d}=\max(P^*_{B,d}-10000,0)",
        r"A_{B,d}=A^*_{B,d}+i_{B,d}",
        "应计利息计入基准NAV，但在正式入账前不得进入计息本金",
        "drawdown_from_ath",
        "drawdown_tier_state",
        "不被估值等级或估值数据缺失削减",
    )
    forbid(
        dictionary,
        r"SPYM \(57\%-A\)",
        r"\(S=\max(C-15\%\times V,0)\)",
        r"C_{B,d}=15\%\times V_{B,d}",
        r"C_{B,m,d}=C^-_{B,m,d}+i_{B,m,d}",
        "合法集合为6%、10%、12.5%、15%",
    )

    active_files = [
        "README.md", "PRODUCTION.md",
        "00-IPS/Investment-Policy-Statement.md",
        "01-Constitution/Target-Allocation.md",
        "02-Operating-System/Daily-Review.md",
        "02-Operating-System/Decision-Checklist.md",
        "02-Operating-System/Monthly-Workflow.md",
        "02-Operating-System/Weekly-Review.md",
        "02-Operating-System/Quarterly-Workflow.md",
        "02-Operating-System/Deployment-Framework.md",
        "02-Operating-System/ETF-Valuation-Framework.md",
        "03-Transition/Transition-Dashboard.md",
        "03-Transition/Transition-Plan.md",
        "04-Alpha/Alpha-Framework.md",
        "04-Alpha/Position-Registry.md",
        "08-Data/README.md",
        "08-Data/DATA_REGISTRY.md",
        "08-Data/DATA_QUALITY.md",
        "08-Data/DATA_DICTIONARY.md",
        "08-Data/LOOKTHROUGH_CHECK.md",
    ]
    # v3.x machinery must not resurface in active rules
    for path in active_files:
        forbid(
            path,
            "Approved / Frozen",
            "Add Candidate Packet的",
            "validate_lookthrough_packet",
            "10%、12.5%与15%",
            "3%→4.5%→6%→10%",
            "Frozen — DATA GATE",
            "长期硬上限与最终治理阶段15%",
        )
        if path != "README.md":  # README keeps a labeled historical footnote
            forbid(path, "Bundle v1.4", "Bundle v1.5")

    require(
        "04-Alpha/Position-Registry.md",
        "3%→4.5%→6%",
        r"当前\(A_{execution\_cap}=3\%\)",
        "永久硬上限",
        "同一次IC不得既推进执行档又执行交易",
        "LOOKTHROUGH_CHECK.md",
        "不自动卖出",
    )
    require(
        "01-Constitution/Target-Allocation.md",
        "永久硬上限为总组合 **6%**",
        "10% / 12.5% / 15% 治理阶段自 v4.0 起作废",
        "回撤部署（Drawdown Deployment）",
        "`10%+U`", "`8%+U`", "`6%+U`",
        "每一档在同一轮回撤周期内最多执行一次",
        "不受估值等级与估值数据可得性约束",
        "只用外部新增资金逐月重建",
        "18% 半导体",
        "SPYM / QQQM 例行路径不受此项单独阻断",
    )
    require(
        "00-IPS/Investment-Policy-Statement.md",
        "SB-1 满仓政策组合",
        "SB-2 单一基金",
        "0.45–0.75",
        "不按 alpha 命名或考核",
    )
    require(
        "04-Alpha/Research/SOXX.md",
        "Incomplete — INDEX METHODOLOGY EVIDENCE",
        "NYSE Semiconductor Index",
    )
    forbid(
        "04-Alpha/Research/SOXX.md",
        "indexes.nasdaq.com",
        "前三大权重上限分别为12%、10%、8%",
    )
    require("README.md", "# Investment OS v4.0")
    require("PRODUCTION.md", "# Investment OS v4.0 — Production Contract")
    require("07-Releases/v4.0.md", "不授权任何订单", "10% / 12.5% / 15% 历史治理阶段作废")
    require("CLAUDE.md", "永远不下单", "fetch_etf_data.py", "DATA INCOMPLETE",
            "公开安全写法", "State-Reconstruction.md", "永不落盘")
    require(
        "02-Operating-System/State-Reconstruction.md",
        "不存储任何账户数据",
        "现金水位自证",
        "恰好一个",
        "0.85×ATH收盘",
        "隐私边界",
    )
    require(
        "scripts/fetch_etf_data.py",
        "holdings-daily-us-en-spym.xlsx",
        "stockanalysis.com",
        "never authorizes trades",
        "GUARD_SEMI_IC = 15.0",
    )
    require(
        "08-Data/LOOKTHROUGH_CHECK.md",
        "fetch_etf_data.py",
    )
    require(
        "02-Operating-System/ETF-Valuation-Framework.md",
        "本框架只覆盖 `SPYM / QQQM / SOXX`",
        "`p < 20`",
        "`20 ≤ p < 70`",
        "`70 ≤ p < 90`",
        "`p ≥ 90`",
        "估值贵本身不能触发卖出",
        "至少需要连续 5 年、60 个互不重复的月末观察值",
        "Trailing P/E 时不得判定为便宜",
        "`CHEAP` 是战术加速 `T` 的必要条件",
        "`VERY EXPENSIVE` 暂停对应标的的战略基线 `B`",
    )
    require(
        "02-Operating-System/Deployment-Framework.md",
        "回撤部署（Drawdown Deployment）",
        "`DD ≥ 15%`", "`DD ≥ 25%`", "`DD ≥ 35%`",
        "估值等级与估值数据可得性不是检查项",
        "每档在同一回撤周期内最多执行一次",
    )
    require(
        "08-Data/LOOKTHROUGH_CHECK.md",
        "15 分钟",
        "只增不改",
        "不自动改变 Registry",
        "PASS / WARN / FREEZE-TILT / DATA INCOMPLETE",
    )
    for path in (
        "README.md",
        "PRODUCTION.md",
        "02-Operating-System/Daily-Review.md",
        "02-Operating-System/Monthly-Workflow.md",
        "02-Operating-System/Deployment-Framework.md",
        "02-Operating-System/Weekly-Review.md",
        "03-Transition/Transition-Dashboard.md",
    ):
        forbid(path, "Valuation Score", "Opportunity Score")
    # historical audit anchors stay in history files
    for path in ("BUGLOG.md", "Decision-Log.md", "README.md"):
        require(path, "Bundle v1.4")
    require(
        "README.md",
        "仓库不维护重复的中央证券数据库",
        "普通数据变化不更新项目",
    )
    require(
        "PRODUCTION.md",
        "仓库不维护行情、ETF成分、issuer或GICS中央数据库",
        "普通巡检不写仓库",
    )
    require(
        "Decision-Log.md",
        "运行时多源数据与决策留证",
        "删除仓库中的中央issuer/GICS全量表",
        "v4.0 证据驱动的结构修正与简化",
    )
    require(
        "Research/2026-07-31-v4-Evidence-and-Proposal.md",
        "18.2%", "24.2%", "31.7%",
        "半导体 15% 护栏在 SOXX=0 时即被 Core 自身突破",
    )
    require(
        ".github/workflows/policy-consistency.yml",
        "python3 scripts/check_policy_consistency.py",
    )
    forbid(
        ".github/workflows/policy-consistency.yml",
        "validate_lookthrough_packet",
        "test_lookthrough_adversarial",
        "check_lookthrough_history",
    )
    for stale in (
        "scripts/validate_lookthrough_packet.py",
        "scripts/parse_lookthrough_sources.py",
        "scripts/test_lookthrough_adversarial.py",
        "scripts/check_lookthrough_history.py",
        "08-Data/LOOKTHROUGH_PACKET.md",
        "08-Data/LOOKTHROUGH_PACKET_TEMPLATE.json",
    ):
        if (ROOT / stale).exists():
            raise AssertionError(f"retired v3.x lookthrough machinery resurfaced: {stale}")
    forbid("03-Transition/Transition-Plan.md", r"现金、\(A\)、目标缺口")

    privacy_gate()

    if CURRENT_EXECUTION_CAP > CURRENT_STAGE:
        raise AssertionError("current execution cap exceeds current stage")
    allocation_tests()
    drawdown_tests()
    benchmark_interest_tests()
    valuation_policy_tests()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
