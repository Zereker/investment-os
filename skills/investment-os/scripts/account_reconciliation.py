#!/usr/bin/env python3
"""Shared deterministic NAV reconciliation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

DEFAULT_TOLERANCE = 0.005


@dataclass(frozen=True)
class ReconciliationResult:
    passed: bool
    nav: float
    cash: float
    positions_market_value: float
    component_total: float
    absolute_difference: float
    relative_difference: float
    tolerance: float

    def as_dict(self) -> dict[str, float | str | list[str]]:
        return {
            "status": "PASS" if self.passed else "DATA INCOMPLETE",
            "issues": [] if self.passed else [self.issue or "NAV reconciliation failed"],
            "nav": self.nav,
            "cash": self.cash,
            "positions_market_value": self.positions_market_value,
            "component_total": self.component_total,
            "absolute_difference": self.absolute_difference,
            "relative_difference": self.relative_difference,
            "tolerance": self.tolerance,
        }

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

    positions_market_value = sum(values[2:])
    component_total = cash + positions_market_value
    absolute_difference = abs(component_total - nav)
    relative_difference = absolute_difference / nav
    return ReconciliationResult(
        passed=relative_difference <= tolerance,
        nav=nav,
        cash=cash,
        positions_market_value=positions_market_value,
        component_total=component_total,
        absolute_difference=absolute_difference,
        relative_difference=relative_difference,
        tolerance=tolerance,
    )
