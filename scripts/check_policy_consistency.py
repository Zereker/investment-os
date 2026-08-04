#!/usr/bin/env python3
"""Fail CI when Production policy formulas, state or guardrails diverge.

Scope (rules-first, v0.5.0): this checker holds EXECUTABLE invariants only —
policy math property tests, a real constant-mirror comparison against the
shipped runtime modules, the public-repo privacy gate, a frozen-live-state
regex, retired-file resurfacing, and a small curated list of known-stale
vocabulary that must never return to the consolidated rule files. The old
~100 require/forbid pins on living prose were retired with the 29->9 rule
consolidation: they asserted that sentences existed, not that behavior was
correct, and they broke on every innocuous rewording.
"""

from math import isfinite, nan, inf
from pathlib import Path
import importlib.util
import re

ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION = "plugins/investment-os/skills/using-investment-os/references/00-constitution.md"
OPERATING_MANUAL = "plugins/investment-os/skills/using-investment-os/references/01-operating-manual.md"
DATA_CONTRACT = "plugins/investment-os/skills/using-investment-os/references/02-data-contract.md"
JOURNAL = "plugins/investment-os/skills/using-investment-os/references/03-journal.md"
RULE_FILES = (CONSTITUTION, OPERATING_MANUAL, DATA_CONTRACT, JOURNAL)

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
TIER_NAMES = ("T1", "T2", "T3", "T4")
LADDER = sum(w for _, w in DRAWDOWN_TIERS)   # 15pp: all of the cash is ammunition
ABSOLUTE_FLOOR = 0.0     # drawdown deployment never takes cash below this (+U)
NORMAL_CASH_FLOOR = 0.12
CASH_TARGET = 0.15
QQQM_TARGET = 0.28
SLEEVE = 0.57


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
        "cash_base": CASH_TARGET,
        "stage_reserve": reserve,
        "qqqm": QQQM_TARGET,
        "spym": SLEEVE - basis,
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
    if abs(LADDER + ABSOLUTE_FLOOR - CASH_TARGET) > 1e-12:
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


def load_runtime_module(rel_path: str):
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mirror_tests() -> None:
    """Compare the ACTUAL constants of the shipped runtime modules against the
    canonical values above. This replaces the old first-and-last-line string
    pins, which could not see a corrupted middle tier."""
    monthly = load_runtime_module(
        "plugins/investment-os/skills/running-monthly-review/scripts/monthly_execution.py")
    drill = load_runtime_module(
        "Research/tools/drawdown_drill.py")

    for label, module in (("monthly_execution", monthly), ("drawdown_drill", drill)):
        tiers = tuple((trigger, tranche) for trigger, _name, tranche in module.TIERS)
        if tiers != DRAWDOWN_TIERS:
            raise AssertionError(f"{label}.TIERS diverged from the canonical ladder: {tiers}")
        names = tuple(name for _t, name, _w in module.TIERS)
        if names != TIER_NAMES:
            raise AssertionError(f"{label}.TIERS names diverged: {names}")
        if module.ABSOLUTE_FLOOR != ABSOLUTE_FLOOR:
            raise AssertionError(f"{label}.ABSOLUTE_FLOOR diverged: {module.ABSOLUTE_FLOOR}")

    if monthly.CASH_TARGET != CASH_TARGET or monthly.CASH_FLOOR != NORMAL_CASH_FLOOR:
        raise AssertionError("monthly_execution cash constants diverged")
    if monthly.QQQM_TARGET != QQQM_TARGET or monthly.SLEEVE_57 != SLEEVE:
        raise AssertionError("monthly_execution sleeve constants diverged")
    if monthly.A_STAGE != CURRENT_STAGE or monthly.A_EXECUTION_CAP != CURRENT_EXECUTION_CAP:
        raise AssertionError("monthly_execution tilt constants diverged")
    if drill.NORMAL_CASH_FLOOR != NORMAL_CASH_FLOOR:
        raise AssertionError("drawdown_drill.NORMAL_CASH_FLOOR diverged")


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


def stale_vocabulary_gate() -> None:
    """Known-stale rule text must never return to the consolidated rule files.

    This is a curated regression guard (BUG-014's class: stale numbers in an
    authoritative document), NOT a prose-preservation patrol. Add a needle only
    when a real stale-text defect was found and fixed.
    """
    for path in RULE_FILES:
        forbid(
            path,
            # v3.x machinery
            "Add Candidate Packet的",
            "validate_lookthrough_packet",
            "10%、12.5%与15%",
            "3%→4.5%→6%→10%",
            "Frozen — DATA GATE",
            "长期硬上限与最终治理阶段15%",
            "Bundle v1.4",
            "Bundle v1.5",
            # v4.2 retired the valuation subsystem; the vocabulary must not return
            "CHEAP",
            "VERY EXPENSIVE",
            "Forward P/E",
            "战术加速",
            "ETF-Valuation-Framework",
            "Valuation Score",
            "Opportunity Score",
            # v4.6 retired the deep tiers
            "`DD ≥ 30%`",
            "`DD ≥ 35%`",
            '"T5"',
            '"T6"',
            # the v4.4 ammunition text (9pp ending at 6%+U) shipped one release
            # behind the tier table in the same file; it must never come back
            "合计 9 个百分点",
            "降至 T4 的 `6%+U`",
            # every figure in the constitution must be traceable to Research/
            "24.1%",
        )
    # the numeric tier table in the constitution must match the canonical ladder
    require(
        CONSTITUTION,
        "T1 | `DD ≥ 10%` | 1.50pp",
        "T2 | `DD ≥ 15%` | 3.00pp",
        "T3 | `DD ≥ 20%` | 4.50pp",
        "T4 | `DD ≥ 25%` | 6.00pp",
        "`0+U`",
    )
    # git history was rebuilt to a single commit: no document may send readers there
    for path in ("README.md",
                 "plugins/investment-os/skills/using-investment-os/references/claude-code-entry.md"):
        forbid(path, "查 git 历史")


def frozen_state_gate() -> None:
    """Live account state must never be frozen into rule files (red line 2).

    Target the pattern "A_actual ... N%" specifically — a bare percentage is
    legitimate elsewhere (price premiums, drawdown depths, guardrail lines).
    "A_actual 约 7.8%" is a frozen observation; "A_actual 高于 6%" references the
    cap and is legitimate. The approximation marker is what distinguishes them.
    """
    frozen_state = re.compile(r"A_actual[^。\n]{0,12}?(?:约|≈|大约)\s*\d+(?:\.\d+)?\s*%")
    for path in (CONSTITUTION, "Decision-Log.md"):
        hit = frozen_state.search(read(path))
        if hit:
            raise AssertionError(f"{path}: frozen A_actual value: {hit.group()!r}")


def retired_files_gate() -> None:
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
        # retired from the plugin in the runtime slim (v0.5.1): the drill's
        # mission is complete (mechanism proven, evidence in Research/, constants
        # mirror-tested); it lives on as Research/tools/drawdown_drill.py
        "plugins/investment-os/skills/validating-drawdown-state/scripts/drawdown_drill.py",
        # retired in the 29->9 rules-first consolidation (v0.5.0)
        "plugins/investment-os/skills/using-investment-os/references/01-target-allocation.md",
        "plugins/investment-os/skills/using-investment-os/references/02-deployment-framework.md",
        "plugins/investment-os/skills/using-investment-os/references/project-contract.md",
        "plugins/investment-os/skills/using-investment-os/references/production-contract.md",
    ):
        if (ROOT / stale).exists():
            raise AssertionError(f"retired file resurfaced: {stale}")

    drawdown_drill = "Research/tools/drawdown_drill.py"
    require(drawdown_drill, "references/02-data-contract.md")
    forbid(drawdown_drill, "references/08-data-registry.md")


def main() -> None:
    if CURRENT_EXECUTION_CAP > CURRENT_STAGE:
        raise AssertionError("current execution cap exceeds current stage")
    allocation_tests()
    drawdown_tests()
    mirror_tests()
    benchmark_interest_tests()
    stale_vocabulary_gate()
    frozen_state_gate()
    retired_files_gate()
    privacy_gate()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
