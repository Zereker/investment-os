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
MONTHLY_REF = "skills/investment-os/references/02-monthly.md"
sys.path.insert(0, str(ROOT / "skills" / "investment-os" / "scripts"))

# Four explicit per-ticker targets summing to 100%.
TARGETS = {"cash": 0.15, "spym": 0.50, "qqqm": 0.30, "soxx": 0.05}
# Bands are disclosure and transition-completion criteria, NOT no-trade zones:
# routine DCA still buys any positive gap with no threshold. SOXX has no
# symmetric band — one is meaningless on a 5% position — so being underweight is
# caught by its positive gap and being OVERWEIGHT is caught by a disclosure-only
# ceiling. Without that ceiling an overweight SOXX is reported by nothing: it is
# outside the band check and an overweight position's gap is zero.
BANDS = {"cash": (0.10, 0.20), "spym": (0.45, 0.55), "qqqm": (0.25, 0.35)}
SOXX_CEILING = 0.075
CASH_TARGET = TARGETS["cash"]
# SPYM and QQQM each carry their OWN ladder against their OWN all-time high,
# sized so a tranche is proportionate to the position it buys. Within a ladder
# the four tiers are graded 1:2:3:4. The two ladders sum to the cash target, so
# a market-wide crash still spends exactly the 15% cash position — what changed
# is that one ticker alone can no longer reach for it.
#
# SOXX carries NO ladder: its tranches could not buy one whole share at this
# account's size, and for a sleeve that small the gap mechanism already IS the
# drawdown response.
LADDERS = {"spym": 0.09, "qqqm": 0.06}
DRAWDOWN_TRIGGERS = (0.10, 0.15, 0.20, 0.25)
TIER_GRADES = (1, 2, 3, 4)
TIER_NAMES = ("T1", "T2", "T3", "T4")
# (ticker, trigger, tier name, released NAV weight)
DRAWDOWN_TIERS = tuple(
    (t, trig, name, LADDERS[t] * grade / sum(TIER_GRADES))
    for t in LADDERS
    for trig, name, grade in zip(DRAWDOWN_TRIGGERS, TIER_NAMES, TIER_GRADES))
LADDER = sum(LADDERS.values())   # 15pp: all of the cash is ammunition
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

    # the SOXX ceiling is a disclosure line above the target, not a band edge:
    # it must sit above the target or it would fire while SOXX is at policy
    if SOXX_CEILING <= TARGETS["soxx"]:
        raise AssertionError("the SOXX ceiling must sit above its target")

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


def drawdown_release(dd: float, executed: set[float] | None = None,
                     ticker: str = "spym") -> float:
    """Weight of NAV ONE ticker's ladder releases at this level, given fired tiers."""
    if not isinstance(dd, (int, float)) or isinstance(dd, bool) or not isfinite(dd):
        raise ValueError("drawdown must be a finite number")
    if not 0 <= dd <= 1:
        raise ValueError("drawdown outside [0, 100%]")
    executed = executed or set()
    return sum(weight for t, trigger, _name, weight in DRAWDOWN_TIERS
               if t == ticker and dd >= trigger and trigger not in executed)


def drawdown_tests() -> None:
    if drawdown_release(0.0) != 0.0:
        raise AssertionError("no drawdown must release nothing")
    if drawdown_release(0.099999) != 0.0:
        raise AssertionError("below-tier drawdown must not unlock deployment")
    # the graded ladder ends at 25% — 30%, 35% and 100% all release the same
    # 15pp, because past T4 the ammunition is spent by design.
    expected = {0.10: 0.0090, 0.1499: 0.0090, 0.15: 0.0270, 0.20: 0.0540,
                0.25: 0.0900, 0.30: 0.0900, 0.35: 0.0900, 1.0: 0.0900}
    for dd, weight in expected.items():
        if abs(drawdown_release(dd) - weight) > 1e-12:
            raise AssertionError(f"wrong release at drawdown {dd}")
    # graded, not equal: within EACH ladder every tier is strictly larger than
    # the one above it, and each ladder's four tranches sum to its total
    for t, ladder in LADDERS.items():
        coded = [w for tk, _tr, _n, w in DRAWDOWN_TIERS if tk == t]
        if any(b <= a for a, b in zip(coded, coded[1:])):
            raise AssertionError(f"{t} tranches must grow strictly with depth")
        if abs(sum(coded) - ladder) > 1e-12:
            raise AssertionError(f"{t} tranches do not sum to its ladder")
    # a fully spent ladder releases nothing however deep the fall goes
    if drawdown_release(0.60, executed=set(DRAWDOWN_TRIGGERS)) != 0.0:
        raise AssertionError("spent ladder must release nothing at any depth")
    # once-per-cycle: an executed tier no longer releases
    if drawdown_release(0.12, executed={0.10}) != 0.0:
        raise AssertionError("executed tier must not re-authorize deployment")
    if abs(drawdown_release(0.30, executed={0.10}) - 0.0810) > 1e-12:
        raise AssertionError("deeper tiers must stay available after shallower executed")
    # the three ladders together take cash from the 15% target exactly to the floor
    if abs(LADDER + ABSOLUTE_FLOOR - CASH_TARGET) > 1e-12:
        raise AssertionError("the three ladders do not span the cash target down to the floor")
    # ammunition is proportionate to the position it buys, within 2pp of the
    # target's share of the equity allocation
    equity = sum(TARGETS[t] for t in LADDERS)
    for t, ladder in LADDERS.items():
        if abs(ladder / LADDER - TARGETS[t] / equity) > 0.03:
            raise AssertionError(f"{t} ladder is not proportionate to its target weight")
    # SOXX must carry no ladder: its tranches cannot buy one whole share, and
    # its positive gap already is its drawdown response
    if "soxx" in LADDERS:
        raise AssertionError("SOXX must carry no drawdown ladder")
    # all three at the same tier reproduce the old single ladder's tranche
    for trig, single in zip(DRAWDOWN_TRIGGERS, (0.0150, 0.0300, 0.0450, 0.0600)):
        across = sum(w for _t, tr, _n, w in DRAWDOWN_TIERS if tr == trig)
        if abs(across - single) > 1e-12:
            raise AssertionError(
                f"a market-wide fall to {trig:.0%} must still release {single:.2%}")
    # the floor may be zero but never negative: that would be borrowing, which
    # the IPS forbids outright
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


NAME_BY_LABEL = {"结构性现金": "cash", "SPYM": "spym", "QQQM": "qqqm", "SOXX": "soxx"}


def published_allocation() -> tuple[dict[str, float], dict[str, tuple[float, float]]]:
    """Parse the constitution's strategy table back into targets and bands.

    The numbers live in prose as well as in code, and nothing used to compare
    the two: a target edited in the constitution and not in the runtime (or the
    reverse) left every test green.
    """
    targets, bands = {}, {}
    row = re.compile(
        r"^\|\s*(结构性现金|SPYM|QQQM|SOXX)\s*\|\s*(\d+(?:\.\d+)?)%\s*\|\s*"
        r"(?:(\d+(?:\.\d+)?)%\s*[–-]\s*(\d+(?:\.\d+)?)%|—)\s*\|")
    for line in read(CONSTITUTION).splitlines():
        hit = row.match(line.strip())
        if not hit:
            continue
        name = NAME_BY_LABEL[hit.group(1)]
        targets[name] = float(hit.group(2)) / 100
        if hit.group(3) is not None:
            bands[name] = (float(hit.group(3)) / 100, float(hit.group(4)) / 100)
    return targets, bands


def published_soxx_ceiling() -> float:
    """Parse the SOXX disclosure ceiling out of the constitution."""
    hit = re.search(r"只作披露的上沿[：:]\s*(\d+(?:\.\d+)?)%", read(CONSTITUTION))
    if not hit:
        raise AssertionError("00-constitution.md no longer publishes the SOXX ceiling")
    return float(hit.group(1)) / 100


def published_migration_months() -> int:
    """Parse R out of the monthly reference's strategic-baseline definition."""
    hit = re.search(r"\\\(R=(\d+)\\\)", read(MONTHLY_REF))
    if not hit:
        raise AssertionError("02-monthly.md no longer publishes R")
    return int(hit.group(1))


def published_ladders() -> dict[str, float]:
    """Parse the constitution's per-ticker ladder totals out of its tier table."""
    row = re.compile(
        r"^\|\s*(SPYM|QQQM|SOXX)\s*\|\s*\d+%\s*\|\s*(\d+\.\d+)pp\s*\|")
    out = {}
    for line in read(CONSTITUTION).splitlines():
        hit = row.match(line.strip())
        if hit:
            out[hit.group(1).lower()] = float(hit.group(2)) / 100
    return out


def published_tranches() -> dict[str, tuple[float, ...]]:
    """Parse each ticker's four published tranches, left to right."""
    row = re.compile(
        r"^\|\s*(SPYM|QQQM|SOXX)\s*\|\s*\d+%\s*\|\s*\d+\.\d+pp\s*\|"
        r"\s*(\d+\.\d+)pp\s*\|\s*(\d+\.\d+)pp\s*\|\s*(\d+\.\d+)pp\s*\|"
        r"\s*(\d+\.\d+)pp\s*\|")
    out = {}
    for line in read(CONSTITUTION).splitlines():
        hit = row.match(line.strip())
        if hit:
            out[hit.group(1).lower()] = tuple(
                float(hit.group(i)) / 100 for i in range(2, 6))
    return out


def published_matches_code() -> None:
    """The constitution is the authority; the code must state the same numbers."""
    targets, bands = published_allocation()
    if targets != TARGETS:
        raise AssertionError(f"constitution targets {targets} != code {TARGETS}")
    if bands != BANDS:
        raise AssertionError(f"constitution bands {bands} != code {BANDS}")
    ladders = published_ladders()
    if ladders != LADDERS:
        raise AssertionError(f"constitution ladders {ladders} != code {LADDERS}")
    tranches = published_tranches()
    for t, published in tranches.items():
        coded = tuple(w for tk, _tr, _n, w in DRAWDOWN_TIERS if tk == t)
        if any(abs(a - b) > 1e-12 for a, b in zip(published, coded)):
            raise AssertionError(f"constitution {t} tranches {published} != code {coded}")
    if set(tranches) != set(LADDERS):
        raise AssertionError(f"constitution publishes tranches for {set(tranches)}")


def load_runtime_module(rel_path: str):
    """Load the module from SOURCE, never from a cached .pyc.

    The default loader validates bytecode on (mtime, size); an edit that keeps
    the size and lands inside the mtime resolution is served from the stale
    cache. A checker whose whole job is catching edits must not be able to
    compare against the file as it used to be.
    """
    path = ROOT / rel_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_text(), str(path), "exec"), module.__dict__)
    return module


def mirror_tests() -> None:
    """Compare the ACTUAL constants of the shipped runtime modules against the
    canonical values above, so a corrupted middle tier cannot slip through."""
    monthly = load_runtime_module(
        "skills/investment-os/scripts/monthly_execution.py")
    if monthly.TIERS != DRAWDOWN_TIERS:
        raise AssertionError(f"monthly_execution.TIERS diverged: {monthly.TIERS}")
    if monthly.LADDERS != LADDERS:
        raise AssertionError(f"monthly_execution.LADDERS diverged: {monthly.LADDERS}")
    if monthly.TIER_NAMES != TIER_NAMES:
        raise AssertionError(f"monthly_execution.TIER_NAMES diverged: {monthly.TIER_NAMES}")
    if monthly.ABSOLUTE_FLOOR != ABSOLUTE_FLOOR:
        raise AssertionError(f"monthly_execution.ABSOLUTE_FLOOR diverged: {monthly.ABSOLUTE_FLOOR}")
    if monthly.TARGETS != TARGETS:
        raise AssertionError(f"monthly_execution.TARGETS diverged: {monthly.TARGETS}")
    if monthly.BANDS != BANDS:
        raise AssertionError(f"monthly_execution.BANDS diverged: {monthly.BANDS}")
    if monthly.SOXX_CEILING != SOXX_CEILING:
        raise AssertionError(f"monthly_execution.SOXX_CEILING diverged: {monthly.SOXX_CEILING}")
    if monthly.SOXX_CEILING != published_soxx_ceiling():
        raise AssertionError(
            "00-constitution.md and monthly_execution.SOXX_CEILING disagree on the ceiling")
    if hasattr(monthly, "CASH_FLOOR"):
        raise AssertionError(
            "CASH_FLOOR is back: the percentage cash floor was removed because "
            "B <= S and D <= F make it unreachable under every input")
    if monthly.MIGRATION_MONTHS < 2:
        raise AssertionError(
            "R must stay above 1, or the strategic baseline becomes a lump sum")
    if monthly.MIGRATION_MONTHS != published_migration_months():
        raise AssertionError(
            "02-monthly.md and monthly_execution.MIGRATION_MONTHS disagree on R")
    # A fired tier drops the bound straight to the absolute floor; what limits
    # the deployment is the tier's own tranche, not any percentage line.
    # Asserted so this is a checked intent, not an accident of the expression.
    fired = monthly.compute(100_000, 20_000, 40_000, 28_000, 5_000, 0,
                            {"spym": 0.10, "qqqm": None, "soxx": None},
                            {"spym": set()})
    if fired["structural_bound_w"] != ABSOLUTE_FLOOR:
        raise AssertionError(f"a fired tier must drop the bound to {ABSOLUTE_FLOOR}")
    if abs(fired["dd_amount"] - LADDERS["spym"] / 10 * 100_000) > 1e-6:
        raise AssertionError("the tranche, not a floor, must cap the deployment")
    # a SPYM tranche buys SPYM: it must not reach into another ticker's gap
    if fired["dd_alloc"]["qqqm"] or fired["dd_alloc"]["soxx"]:
        raise AssertionError("a SPYM tranche deployed into another ticker")


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
    published_matches_code()
    mirror_tests()
    frozen_state_gate()
    privacy_gate()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
