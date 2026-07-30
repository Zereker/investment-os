#!/usr/bin/env python3
"""Fail CI when Production policy formulas or lifecycle wording diverge."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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


def allocation_tests() -> None:
    cases = [
        (0.00, 0.06), (0.03, 0.06), (0.06, 0.06), (0.08, 0.06),
        (0.06, 0.10), (0.10, 0.10), (0.12, 0.10),
        (0.10, 0.125), (0.125, 0.125), (0.15, 0.15),
    ]
    for actual, stage in cases:
        basis = max(actual, stage)
        reserve = max(stage - actual, 0)
        total = 0.15 + reserve + 0.28 + (0.57 - basis) + actual
        if abs(total - 1.0) > 1e-12:
            raise AssertionError(
                f"allocation does not sum to 100%: actual={actual}, stage={stage}, total={total}"
            )


def main() -> None:
    dictionary = "08-Data/DATA_DICTIONARY.md"
    require(
        dictionary,
        r"SPYM \(57\%-A_{basis}\)",
        r"\(S=\max(C-(15\%+U)\times V,0)\)",
        r"C_{B,m,0}=15\%\times V_{B,m,0}",
        "月内现金袖套按状态递推",
    )
    forbid(
        dictionary,
        r"SPYM \(57\%-A\)",
        r"\(S=\max(C-15\%\times V,0)\)",
        r"C_{B,d}=15\%\times V_{B,d}",
    )

    active_lifecycle_files = [
        "README.md",
        "PRODUCTION.md",
        "02-Operating-System/Daily-Review.md",
        "02-Operating-System/Monthly-Workflow.md",
        "02-Operating-System/Weekly-Review.md",
        "03-Transition/Transition-Dashboard.md",
        "03-Transition/Transition-Plan.md",
        "04-Alpha/Alpha-Framework.md",
        "04-Alpha/Position-Registry.md",
        "04-Alpha/Research/SOXX.md",
    ]
    for path in active_lifecycle_files:
        forbid(path, "Approved / Frozen")

    require(
        "04-Alpha/Position-Registry.md",
        "Frozen — DATA GATE",
        "Approved / Add Candidate",
        "IC批准只允许进入账户所有者人工下单",
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
    forbid("02-Operating-System/Monthly-Workflow.md", "SOXX 等 Observation")
    forbid("03-Transition/Transition-Plan.md", r"现金、\(A\)、目标缺口")
    require("README.md", "# Investment OS v3.4.1")
    require("PRODUCTION.md", "# Investment OS v3.4.1 — Production Contract")
    require("07-Releases/v3.4.1.md", "本发布不授权任何订单")

    allocation_tests()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
