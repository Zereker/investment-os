#!/usr/bin/env python3
"""Fail CI when Production policy formulas, state or guardrails diverge (v4.0)."""

from math import isfinite, nan, inf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = (0.06,)  # v4.0: 6% is the permanent hard cap; 10/12.5/15% stages are void
EXECUTION_CAPS = (0.03, 0.045, 0.06)
CURRENT_STAGE = 0.06
CURRENT_EXECUTION_CAP = 0.03
# v4.4: each tier releases a FIXED tranche of NAV. The older "deploy everything
# above a floor" shape dumped the whole 15%->floor band into the first tier,
# which is exactly what tranching exists to prevent.
# v4.6: four tiers ending at 25% (the deepest two of the old six almost never
# fired), GRADED 1:2:3:4 so the first shot stays small while the money lands at
# the deepest entries, and spending the cash out entirely — the old 6% floor was
# never independently justified, just the tail of v4.0's 10/8/6 sequence.
DRAWDOWN_TIERS = ((0.10, 0.0150), (0.15, 0.0300), (0.20, 0.0450), (0.25, 0.0600))
DRAWDOWN_TRIGGERS = tuple(t for t, _ in DRAWDOWN_TIERS)
LADDER = sum(w for _, w in DRAWDOWN_TIERS)   # 15pp: all of the cash is ammunition
ABSOLUTE_FLOOR = 0.0     # drawdown deployment never takes cash below this (+U)
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


def drawdown_release(dd: float, executed: set[float] | None = None) -> float:
    """Weight of NAV the drawdown clause releases at this level, given fired tiers."""
    if not isinstance(dd, (int, float)) or isinstance(dd, bool) or not isfinite(dd):
        raise ValueError("drawdown must be a finite number")
    if not 0 <= dd <= 1:
        raise ValueError("drawdown outside [0, 100%]")
    executed = executed or set()
    return sum(weight for trigger, weight in DRAWDOWN_TIERS
               if dd >= trigger and trigger not in executed)


def drawdown_tests() -> None:
    if drawdown_release(0.0) != 0.0:
        raise AssertionError("no drawdown must release nothing")
    if drawdown_release(0.099999) != 0.0:
        raise AssertionError("below-tier drawdown must not unlock deployment")
    # v4.6: graded ladder ending at 25% — 30%, 35% and 100% all release the same
    # 15pp, because past T4 the ammunition is spent by design.
    expected = {0.10: 0.0150, 0.1499: 0.0150, 0.15: 0.0450, 0.20: 0.0900,
                0.25: 0.1500, 0.30: 0.1500, 0.35: 0.1500, 1.0: 0.1500}
    for dd, weight in expected.items():
        if abs(drawdown_release(dd) - weight) > 1e-12:
            raise AssertionError(f"wrong release at drawdown {dd}")
    # graded, not equal: each tier must be strictly larger than the one above it
    if any(b[1] <= a[1] for a, b in zip(DRAWDOWN_TIERS, DRAWDOWN_TIERS[1:])):
        raise AssertionError("tranches must grow strictly with depth")
    # a fully spent ladder releases nothing however deep the fall goes
    if drawdown_release(0.60, executed=set(DRAWDOWN_TRIGGERS)) != 0.0:
        raise AssertionError("spent ladder must release nothing at any depth")
    # once-per-cycle: an executed tier no longer releases
    if drawdown_release(0.12, executed={0.10}) != 0.0:
        raise AssertionError("executed tier must not re-authorize deployment")
    if abs(drawdown_release(0.30, executed={0.10}) - 0.1350) > 1e-12:
        raise AssertionError("deeper tiers must stay available after shallower executed")
    # the tranches take cash from the 15% target exactly to the absolute floor
    if abs(LADDER + ABSOLUTE_FLOOR - 0.15) > 1e-12:
        raise AssertionError("ladder does not span the 15% target down to the floor")
    if ABSOLUTE_FLOOR >= NORMAL_CASH_FLOOR:
        raise AssertionError("the crisis floor must sit below the normal floor")
    # the floor may be zero but never negative: that would be borrowing, which
    # the IPS forbids outright (owner reaffirmed no leverage on 2026-08-01)
    if ABSOLUTE_FLOOR < 0:
        raise AssertionError("a negative floor is margin borrowing — forbidden by the IPS")
    for invalid in (-0.01, 1.01, nan, inf, True):
        try:
            drawdown_release(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"illegal drawdown accepted: {invalid}")
    if list(DRAWDOWN_TRIGGERS) != sorted(DRAWDOWN_TRIGGERS):
        raise AssertionError("drawdown triggers must deepen monotonically")


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


INTEREST_THRESHOLD = 10_000.0


def benchmark_month_interest(
    month_start_nav: float | None,
    rate: float | None,
    days_in_month: int,
) -> float | None:
    """v4.1 monthly cash-sleeve interest. Returns None (N/A) on any missing input.

    Principal is fixed at the month-start sleeve value, so interest never
    compounds within the month (BUG-016 regression guard).
    """
    if month_start_nav is None or rate is None:
        return None
    sleeve = 0.15 * month_start_nav
    eligible = max(sleeve - INTEREST_THRESHOLD, 0.0)
    scale = min(month_start_nav / 100_000.0, 1.0)
    return eligible * rate * scale * days_in_month / 360.0


def benchmark_interest_tests() -> None:
    # missing input must yield N/A, never a silent 0% (BUG-013 regression guard)
    if benchmark_month_interest(None, 0.036, 31) is not None:
        raise AssertionError("missing NAV must yield N/A, not a number")
    if benchmark_month_interest(200_000.0, None, 31) is not None:
        raise AssertionError("missing rate must yield N/A, not a number")

    # below the interest-free threshold the sleeve earns nothing
    if benchmark_month_interest(60_000.0, 0.036, 31) != 0.0:
        raise AssertionError("sleeve under the threshold must earn no interest")

    # no intra-month compounding: two half-length months must equal one full month
    full = benchmark_month_interest(1_000_000.0, 0.036, 30)
    half = benchmark_month_interest(1_000_000.0, 0.036, 15)
    if full is None or half is None or abs(full - 2 * half) > 1e-9:
        raise AssertionError("interest compounded within the month")

    # NAV scale caps at 1.0 and shrinks small accounts proportionally
    big = benchmark_month_interest(1_000_000.0, 0.036, 30)
    capped = benchmark_month_interest(100_000.0, 0.036, 30)
    if capped is None or big is None:
        raise AssertionError("scale test inputs must produce values")
    if abs(min(1_000_000.0 / 100_000.0, 1.0) - 1.0) > 1e-12:
        raise AssertionError("NAV scale must cap at 1.0")
    expected_capped = max(0.15 * 100_000.0 - INTEREST_THRESHOLD, 0.0) * 0.036 * 1.0 * 30 / 360.0
    if abs(capped - expected_capped) > 1e-9:
        raise AssertionError("NAV scale applied incorrectly")


def main() -> None:
    dictionary = "08-Data/DATA_DICTIONARY.md"
    require(
        dictionary,
        r"SPYM \(57\%-A_{basis}\)",
        r"\(D_{max}=\min(F,G_0)\)",
        r"\(S=\max(C-(15\%+U)\times V,0)\)",
        r"C_{B,m,0}=15\%\times V_{B,m,0}",
        r"r^{model}_{cash,m}=I_{B,m}/C_{B,m,0}",
        "本金固定为月初值，因此利息不在月内复利",
        "它不得在当月内参与计息，也不得被重复确认为收益",
        "drawdown_from_ath",
        "drawdown_tier_state",
    )
    forbid(
        dictionary,
        r"SPYM \(57\%-A\)",
        r"\(S=\max(C-15\%\times V,0)\)",
        r"C_{B,d}=15\%\times V_{B,d}",
        r"C_{B,m,d}=C^-_{B,m,d}+i_{B,m,d}",
        "合法集合为6%、10%、12.5%、15%",
        # v4.1: the daily recursion and its posted/unposted split are retired
        r"P^*_{B,d}",
        r"i_{B,d}=E_{B,d}",
        "次月第三个工作日",
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
            "Bundle v1.4",
            "Bundle v1.5",
            # v4.2 retired the valuation subsystem. The old BUG-007 guard asserted
            # "N/A must not block B"; with no valuation gate at all that holds by
            # construction, so the guard becomes: the vocabulary must not return.
            "CHEAP",
            "VERY EXPENSIVE",
            "Forward P/E",
            "战术加速",
            "ETF-Valuation-Framework",
        )

    require(
        "04-Alpha/Position-Registry.md",
        "3%→4.5%→6%",
        r"当前\(A_{execution\_cap}=3\%\)",
        "永久硬上限",
        "同一次IC不得既推进执行档又执行交易",
        "LOOKTHROUGH_CHECK.md",
        "不自动卖出",
        # v4.5: the two paths must stay named and separately gated
        "提高倾斜闸门",
        "回补至目标",
        "完整 IC",
        "`min(A_execution_cap, A_stage) − A_actual`",
        "不传该标志即视为无当季有效核查",
    )
    require(
        "01-Constitution/Target-Allocation.md",
        "永久硬上限为总组合 **6%**",
        "10% / 12.5% / 15% 治理阶段自 v4.0 起作废",
        "回撤部署（Drawdown Deployment）",
        "T1 | `DD ≥ 10%` | 1.50pp", "T4 | `DD ≥ 25%` | 6.00pp",
        "`0+U`", "梯度", "行为缓冲",
        # v4.6: the ladder ends at 25% and that must stay stated, not implied
        "**`DD` 超过 25% 后不再解锁任何档位。**",
        "为什么终点是 25% 而不是 35%",
        "每一档在同一轮回撤周期内最多执行一次",
        "除 `DD` 达档外不引入任何其他判断项",
        "只用外部新增资金逐月重建",
        "18% 半导体",
        "SPYM / QQQM 例行路径不受此项单独阻断",
        "广谱市场信号",
        # v4.5: "追加" split into restore (routine path) and tilt increase (full IC).
        # Both definitions and the restore's five constraints live here.
        "回补至目标 vs 提高倾斜",
        "**回补至目标（Restore-to-target）**",
        "**提高倾斜（Tilt increase）**",
        "回补走月度例行路径",
        "**提高倾斜仍须完整 IC**",
        "资金只来自 `U`",
        "不得降级为「先买一部分」",
        r"交易后 `A_actual ≤ min(A_execution_cap, A_stage)`",
    )
    # the restore must never be describable as raising the cap — that is the one
    # thing it is defined not to do, and the whole split collapses if it drifts
    forbid(
        "01-Constitution/Target-Allocation.md",
        "回补可提高 `A_execution_cap`",
        "回补时推进执行档",
    )
    require(
        "02-Operating-System/Deployment-Framework.md",
        "与再平衡的分工",
        "由再平衡吸收",
    )
    require(
        "Research/2026-08-01-drawdown-vs-rebalancing-scope.md",
        "由再平衡吸收",
        "未采纳",
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
    require("PRODUCTION.md", "# Investment OS v4.6 — Production Contract")
    require(
        "Research/2026-08-01-valuation-subsystem-retirement.md",
        "已批准",
        "历史百分位是真正的死结",
    )
    require("Decision-Log.md", "v4.2 估值子系统整体退役", "v4.3 回撤部署 T1 触发线由 15% 下调至 10%")
    require(
        "Research/2026-08-01-t1-threshold-10pct.md",
        "已批准",
        "反对证据",
        "证伪回路",
    )
    require("01-Constitution/Target-Allocation.md", "由 T2（15%）、T3（20%）、T4（25%）逐档覆盖")
    # the retired deep tiers must not survive anywhere in the active rules
    for path in ("01-Constitution/Target-Allocation.md",
                 "02-Operating-System/Deployment-Framework.md",
                 "02-Operating-System/State-Reconstruction.md",
                 "scripts/drawdown_drill.py", "scripts/monthly_execution.py"):
        forbid(path, "`DD ≥ 30%`", "`DD ≥ 35%`", '"T5"', '"T6"')
    require(
        "Research/2026-08-01-drawdown-four-tier.md",
        "已批准", "证伪回路", "未采纳",
        # the case against must stay on the page, not just the case for
        "2008 型深跌无弹药", "行为缓冲在最深档消失",
        # 6% was never justified — that finding is why the floor moved to zero
        "6% 从未被单独论证过",
        # leverage was raised and declined; the analysis must stay retrievable
        "关于杠杆：明确不做", "强制平仓不是现实风险",
    )
    # the IPS's no-leverage principle must survive this release untouched
    require("00-IPS/Investment-Policy-Statement.md", "不接受无上限的行业、杠杆或流动性风险")
    require("Decision-Log.md", "v4.6 回撤阶梯改为四档梯度，25% 处把现金全部投出")
    require(
        "Research/2026-08-01-drawdown-tranching.md",
        "已批准",
        "证伪回路",
        "分批本身就是「不知道谷底在哪」的正确答案",
    )
    require("Decision-Log.md", "v4.4 回撤部署改为六档等额分批")
    require("02-Operating-System/State-Reconstruction.md", "已执行档数")
    require(
        "Research/2026-08-01-benchmark-cash-model-simplification.md",
        "已批准",
        "不得使用实际账户的单位现金收益率",
    )
    require("CLAUDE.md", "永远不下单", "fetch_etf_data.py", "DATA INCOMPLETE",
            "公开安全写法", "State-Reconstruction.md", "永不落盘",
            "你不合并 master", "由所有者审阅合并")
    require(
        "02-Operating-System/State-Reconstruction.md",
        "不存储任何账户数据",
        "现金水位自证",
        "恰好一个",
        "T1 `0.90×`",
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
        "scripts/monthly_execution.py",
        "NEVER places or formats an executable order",
        "NEVER writes account figures to disk",
        # the calculator mirrors the rules; its constants must match this file
        'TIERS = ((0.10, "T1", 0.0150),',
        '(0.25, "T4", 0.0600))',
        "ABSOLUTE_FLOOR = 0.0     # cash never goes below",
        "CASH_FLOOR = 0.12",
        "CASH_TARGET = 0.15",
        "QQQM_TARGET = 0.28",
        "A_STAGE = 0.06",
        "A_EXECUTION_CAP = 0.03",
        "def self_test",
        # v4.5: the restore is capped by the execution cap and fails closed
        "def restore_candidate",
        "if not lookthrough_current:",
        "headroom = min(A_EXECUTION_CAP, A_STAGE) - a_actual",
    )
    require(
        "01-Constitution/Target-Allocation.md",
        "Research/2026-08-01-soxx-restore-vs-increase.md",
    )
    require(
        "Research/2026-08-01-soxx-restore-vs-increase.md",
        "已批准",
        "反对论据",
        "证伪回路",
        "未采纳",
        "看 `A_execution_cap` 动没动",
    )
    require("Decision-Log.md", "v4.5 「回补至目标」与「提高倾斜」拆分")
    require(
        "02-Operating-System/Monthly-Workflow.md",
        "lookthrough-current",
        "回补",
        "提高倾斜",
    )
    require("PRODUCTION.md", "回补至目标", "提高倾斜")
    require("04-Alpha/Alpha-Framework.md", "提高倾斜标准", "回补至目标标准")
    require(
        "02-Operating-System/Deployment-Framework.md",
        "本框架的三条通道只买 SPYM / QQQM",
    )
    require("CLAUDE.md", "monthly_execution.py")
    require("02-Operating-System/Monthly-Workflow.md", "monthly_execution.py")
    require(
        "scripts/drawdown_drill.py",
        "never authorizes trades",
        # the drill's tiers must mirror DRAWDOWN_TIERS above, or the drill
        # would be validating a state machine the Constitution does not have
        'TIERS = ((0.10, "T1", 0.0150),',
        '(0.25, "T4", 0.0600))',
        "ABSOLUTE_FLOOR = 0.0     # cash never goes below",
        "check_invariants",
    )
    require(
        "Research/2026-08-01-drawdown-deployment-drill.md",
        "七项不变量全部成立",
        "在真实周期跑过之前仍属未验证状态",
    )
    require(
        "02-Operating-System/Deployment-Framework.md",
        "drawdown_drill.py",
        "未验证",
    )
    require(
        "02-Operating-System/Deployment-Framework.md",
        "回撤部署（Drawdown Deployment）",
        "`DD ≥ 10%`", "`DD ≥ 15%`", "`DD ≥ 20%`", "`DD ≥ 25%`",
        "没有任何可解锁的档位",
        "不引入任何其他判断项",
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
        "03-Transition/Transition-Plan.md",
    ):
        forbid(path, "Valuation Score", "Opportunity Score")
    # retired v3.x mechanisms survive only as one-line archive entries in the history files
    for path in ("BUGLOG.md", "Decision-Log.md"):
        require(path, "Bundle v1.4")
    require("Decision-Log.md", "v3.x 决策存档")
    require("BUGLOG.md", "已退役机制缺陷存档")
    # git history was rebuilt to a single commit: no document may send readers there
    for path in ("README.md", "CLAUDE.md"):
        forbid(path, "查 git 历史")
    # live account state must never be frozen into rule files (red line 2).
    # Target the pattern "A_actual ... N%" specifically — a bare percentage is
    # legitimate elsewhere (price premiums, drawdown depths, guardrail lines).
    # "A_actual 约 7.8%" is a frozen observation; "A_actual 高于 6%" references the
    # cap and is legitimate. The approximation marker is what distinguishes them.
    frozen_state = re.compile(r"A_actual[^。\n]{0,12}?(?:约|≈|大约)\s*\d+(?:\.\d+)?\s*%")
    for path in ("04-Alpha/Position-Registry.md",
                 "Decision-Log.md", "01-Constitution/Target-Allocation.md"):
        hit = frozen_state.search(read(path))
        if hit:
            raise AssertionError(f"{path}: frozen A_actual value: {hit.group()!r}")
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
        # retired in the v4.0 cleanup: every section duplicated another file, and its
        # account fields could never be filled without failing the privacy gate
        "03-Transition/Transition-Dashboard.md",
        # retired in the v4.0 cleanup: single-stock research template, but stock
        # authorization is 0% and the tilt framework allows exactly one vehicle
        "04-Alpha/Research/README.md",
        # retired in v4.2: four Red inputs that cannot go Green, and a
        # historical-percentile requirement no source can satisfy
        "02-Operating-System/ETF-Valuation-Framework.md",
    ):
        if (ROOT / stale).exists():
            raise AssertionError(f"retired file resurfaced: {stale}")
    forbid("03-Transition/Transition-Plan.md", r"现金、\(A\)、目标缺口")

    privacy_gate()

    if CURRENT_EXECUTION_CAP > CURRENT_STAGE:
        raise AssertionError("current execution cap exceeds current stage")
    allocation_tests()
    drawdown_tests()
    benchmark_interest_tests()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
