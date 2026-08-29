#!/usr/bin/env python3
"""Test executable policy mathematics and the public-repository privacy boundary."""

from __future__ import annotations

from math import isfinite, nan, inf
from pathlib import Path
import importlib.util
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION = "skills/investment-os/references/00-constitution.md"
sys.path.insert(0, str(ROOT / "skills" / "investment-os" / "scripts"))

# Four explicit per-ticker targets summing to 100%.
TARGETS = {"cash": 0.15, "spym": 0.50, "qqqm": 0.30, "soxx": 0.05}
# Bands are disclosure and transition-completion criteria, NOT no-trade zones:
# routine DCA still buys any positive gap with no threshold. SOXX has no band —
# a symmetric band on a 5% position is meaningless; its criterion is gap == 0.
BANDS = {"cash": (0.10, 0.20), "spym": (0.45, 0.55), "qqqm": (0.25, 0.35)}
CASH_TARGET = TARGETS["cash"]
# The cash floor is a RISK constraint, not the lower band edge. The band
# describes state (a market move may carry cash to 10%); the floor constrains
# trades (routine buying must not drive cash under it).
NORMAL_CASH_FLOOR = 0.12
# Each tier releases a FIXED tranche of NAV, graded 1:2:3:4 so the first shot
# stays small while most of the money lands at the deepest entries. The four
# tranches sum to the cash target, so the ladder spends the cash out entirely.
DRAWDOWN_TIERS = ((0.10, 0.0150), (0.15, 0.0300), (0.20, 0.0450), (0.25, 0.0600))
DRAWDOWN_TRIGGERS = tuple(t for t, _ in DRAWDOWN_TIERS)
TIER_NAMES = ("T1", "T2", "T3", "T4")
LADDER = sum(w for _, w in DRAWDOWN_TIERS)   # 15pp: all of the cash is ammunition
ABSOLUTE_FLOOR = 0.0     # drawdown deployment never takes cash below this


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def positive_gap(target: float, actual: float) -> float:
    """Weight of NAV to buy for one ticker. Drift above target yields 0, never a
    sell signal: the rules repair overweight by dilution, never by rebalancing out."""
    for value in (target, actual):
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            raise ValueError("weights must be finite numbers")
    if not 0 <= actual <= 1:
        raise ValueError("actual weight outside [0, 100%]")
    return max(target - actual, 0.0)


def allocation_tests() -> None:
    # the four targets are explicit and close to exactly 100%
    if abs(sum(TARGETS.values()) - 1.0) > 1e-12:
        raise AssertionError(f"targets do not sum to 100%: {TARGETS}")
    if any(not 0.0 < value < 1.0 for value in TARGETS.values()):
        raise AssertionError(f"a target sits outside (0, 100%): {TARGETS}")

    # every band brackets its own target, and no band is inverted
    for name, (low, high) in BANDS.items():
        if not low < TARGETS[name] < high:
            raise AssertionError(f"{name} band {low}-{high} does not bracket {TARGETS[name]}")
    # SOXX deliberately has no band; its criterion is a closed gap
    if "soxx" in BANDS:
        raise AssertionError("SOXX must not carry a band")

    # the cash floor is a separate object from the band: it sits below the
    # target (so routine buying has room) and above the band's lower edge (a
    # market move may legitimately carry cash under the floor without a trade)
    if not BANDS["cash"][0] <= NORMAL_CASH_FLOOR < CASH_TARGET:
        raise AssertionError("cash floor must sit within the band and below the target")

    # gaps: at target and above target nothing is bought; below target the gap
    # is exactly the shortfall
    for name, target in TARGETS.items():
        if positive_gap(target, target) != 0.0:
            raise AssertionError(f"{name} at target must produce no gap")
        if positive_gap(target, min(target + 0.02, 1.0)) != 0.0:
            raise AssertionError(f"{name} above target must produce no gap (dilution, not sale)")
    if abs(positive_gap(TARGETS["qqqm"], 0.25) - 0.05) > 1e-12:
        raise AssertionError("gap must equal the shortfall")

    for args in ((0.5, -0.01), (0.5, 1.01), (0.5, nan), (0.5, inf), (0.5, True)):
        try:
            positive_gap(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"illegal weight accepted: {args}")


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
    # the graded ladder ends at 25% — 30%, 35% and 100% all release the same
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
        raise AssertionError("ladder does not span the cash target down to the floor")
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
    canonical values above, so a corrupted middle tier cannot slip through."""
    monthly = load_runtime_module(
        "skills/investment-os/scripts/monthly_execution.py")
    tiers = tuple((trigger, tranche) for trigger, _name, tranche in monthly.TIERS)
    if tiers != DRAWDOWN_TIERS:
        raise AssertionError(f"monthly_execution.TIERS diverged: {tiers}")
    names = tuple(name for _trigger, name, _tranche in monthly.TIERS)
    if names != TIER_NAMES:
        raise AssertionError(f"monthly_execution.TIERS names diverged: {names}")
    if monthly.ABSOLUTE_FLOOR != ABSOLUTE_FLOOR:
        raise AssertionError(f"monthly_execution.ABSOLUTE_FLOOR diverged: {monthly.ABSOLUTE_FLOOR}")
    if monthly.TARGETS != TARGETS:
        raise AssertionError(f"monthly_execution.TARGETS diverged: {monthly.TARGETS}")
    if monthly.BANDS != BANDS:
        raise AssertionError(f"monthly_execution.BANDS diverged: {monthly.BANDS}")
    if monthly.CASH_FLOOR != NORMAL_CASH_FLOOR:
        raise AssertionError("monthly_execution cash floor diverged")


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


def frozen_state_gate() -> None:
    """Live account state must never be frozen into rule files (red line 2).

    Target an observed WEIGHT specifically — a bare percentage is legitimate
    elsewhere (targets, band edges, drawdown depths). "SOXX 实际权重 约 7.8%" is a
    frozen observation; "SOXX 高于目标权重" references the rule and is legitimate.
    The approximation marker is what distinguishes them.
    """
    frozen_state = re.compile(
        r"(?:实际权重|当前权重|持仓权重|A_actual)[^。\n]{0,12}?(?:约|≈|大约)\s*\d+(?:\.\d+)?\s*%")
    hit = frozen_state.search(read(CONSTITUTION))
    if hit:
        raise AssertionError(f"{CONSTITUTION}: frozen weight observation: {hit.group()!r}")


def main() -> None:
    allocation_tests()
    drawdown_tests()
    mirror_tests()
    frozen_state_gate()
    privacy_gate()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
