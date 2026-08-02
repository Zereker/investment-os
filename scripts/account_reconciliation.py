#!/usr/bin/env python3
"""Shared deterministic NAV reconciliation for broker and decision runtimes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

DEFAULT_TOLERANCE = 0.005


@dataclass(frozen=True)
class ReconciliationResult:
    passed: bool
    nav: float
    component_total: float
    absolute_difference: float
    relative_difference: float
    tolerance: float

    @property
    def issue(self) -> str | None:
        if self.passed:
            return None
        return (
            "cash plus positions does not reconcile to NAV: "
            f"difference {self.relative_difference:.2%} of NAV "
            f"(limit {self.tolerance:.2%})"
        )


def reconcile_nav(
    nav: float,
    cash: float,
    position_values: Iterable[float],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> ReconciliationResult:
    values = [float(nav), float(cash), *(float(value) for value in position_values)]
    if not all(math.isfinite(value) for value in values):
        raise ValueError("reconciliation inputs must be finite")
    if nav <= 0:
        raise ValueError("NAV must be positive for reconciliation")
    if tolerance < 0 or not math.isfinite(tolerance):
        raise ValueError("reconciliation tolerance must be finite and nonnegative")

    component_total = cash + sum(values[2:])
    absolute_difference = abs(component_total - nav)
    relative_difference = absolute_difference / nav
    return ReconciliationResult(
        passed=relative_difference <= tolerance,
        nav=nav,
        component_total=component_total,
        absolute_difference=absolute_difference,
        relative_difference=relative_difference,
        tolerance=tolerance,
    )
