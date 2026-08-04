#!/usr/bin/env python3
"""Validate a broker-neutral Investment OS runtime.

This module never connects to a broker and never persists account data. A concrete
adapter supplies an ephemeral JSON object; this validator enforces capability,
freshness, consistency, and fail-closed semantics before domain skills consume it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from account_reconciliation import reconcile_nav  # noqa: E402

VALID_CAPABILITY_STATES = {"available", "unavailable", "stale", "conflicting"}
REQUIRED_SECTIONS = {
    "identity",
    "snapshot",
    "capabilities",
    "observations",
    "account_summary",
    "balances",
    "positions",
    "open_orders",
    "cash_transactions",
    "market_inputs",
    "alert_inventory",
    "standing_automations",
    "reconciliation",
}


@dataclass(frozen=True)
class ValidationResult:
    status: str
    blocking_issues: tuple[str, ...]
    observation_skew_seconds: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_status": self.status,
            "blocking_issues": list(self.blocking_issues),
            "observation_skew_seconds": self.observation_skew_seconds,
        }


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _position_values(value: Any) -> list[float] | None:
    if isinstance(value, dict):
        result = []
        for item in value.values():
            number = _number(item if not isinstance(item, dict) else item.get("market_value"))
            if number is None:
                return None
            result.append(number)
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            if not isinstance(item, dict):
                return None
            number = _number(item.get("market_value", item.get("marketValue")))
            if number is None:
                return None
            result.append(number)
        return result
    return None


def validate_runtime(
    runtime: dict[str, Any],
    required_capabilities: Iterable[str],
    *,
    now: datetime | None = None,
    max_age_seconds: int = 300,
) -> ValidationResult:
    issues: list[str] = []
    missing_sections = sorted(REQUIRED_SECTIONS - set(runtime))
    if missing_sections:
        issues.append("missing runtime sections: " + ", ".join(missing_sections))

    capabilities = runtime.get("capabilities")
    if not isinstance(capabilities, dict):
        capabilities = {}
        issues.append("capabilities must be an object")

    required = tuple(required_capabilities)
    observations = runtime.get("observations")
    if not isinstance(observations, dict):
        observations = {}
        issues.append("observations must be an object")

    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    observed_times: list[datetime] = []
    for name in required:
        state = capabilities.get(name)
        if state not in VALID_CAPABILITY_STATES:
            issues.append(f"required capability {name} is not declared")
        elif state != "available":
            issues.append(f"required capability {name} is {state}")
            if runtime.get(name) in ([], {}, 0, 0.0, ""):
                issues.append(
                    f"unavailable capability {name} must use null, not an empty or zero value"
                )
        else:
            if runtime.get(name) is None:
                issues.append(f"available capability {name} has no value")
            observation = observations.get(name)
            if not isinstance(observation, dict):
                issues.append(f"available capability {name} has no observation metadata")
                continue
            if not observation.get("source"):
                issues.append(f"observation {name}.source is required")
            observed_at = _parse_timestamp(observation.get("observed_at"))
            if observed_at is None:
                issues.append(
                    f"observation {name}.observed_at must be an ISO-8601 timezone-aware timestamp"
                )
                continue
            age = (current - observed_at).total_seconds()
            if age < -5:
                issues.append(f"observation {name} timestamp is in the future")
            elif age > max_age_seconds:
                issues.append(
                    f"observation {name} is stale ({int(age)}s old; limit {max_age_seconds}s)"
                )
            observed_times.append(observed_at)

    snapshot = runtime.get("snapshot")
    if not isinstance(snapshot, dict):
        issues.append("snapshot must be an object")
    else:
        timestamp = _parse_timestamp(snapshot.get("as_of"))
        if timestamp is None:
            issues.append("snapshot.as_of must be an ISO-8601 timezone-aware timestamp")
        else:
            age = (current - timestamp).total_seconds()
            if age < -5:
                issues.append("snapshot timestamp is in the future")
            elif age > max_age_seconds:
                issues.append(f"snapshot is stale ({int(age)}s old; limit {max_age_seconds}s)")
        if not snapshot.get("source"):
            issues.append("snapshot.source is required")
        if not snapshot.get("timezone"):
            issues.append("snapshot.timezone is required")
        if not snapshot.get("currency_basis"):
            issues.append("snapshot.currency_basis is required")

    reconciliation = runtime.get("reconciliation")
    if not isinstance(reconciliation, dict):
        issues.append("reconciliation must be an object")
    else:
        if reconciliation.get("status") != "PASS":
            issues.append("reconciliation status is not PASS")
        declared = reconciliation.get("issues", [])
        if declared:
            issues.extend(f"reconciliation: {item}" for item in declared)

    summary = runtime.get("account_summary")
    balances = runtime.get("balances")
    nav = _number(summary.get("net_liquidation")) if isinstance(summary, dict) else None
    cash = None
    if isinstance(balances, dict):
        cash = _number(balances.get("total_cash", balances.get("cash")))
    positions = _position_values(runtime.get("positions"))
    if nav is None or cash is None or positions is None:
        issues.append("actual reconciliation inputs are unavailable")
    else:
        try:
            actual = reconcile_nav(nav, cash, positions)
        except ValueError as exc:
            issues.append(f"actual reconciliation invalid: {exc}")
        else:
            if not actual.passed:
                issues.append(actual.issue or "actual reconciliation failed")

    observation_skew = None
    if observed_times:
        observation_skew = (max(observed_times) - min(observed_times)).total_seconds()
        if observation_skew > max_age_seconds:
            issues.append(
                "required capability observations are not a coherent snapshot "
                f"({int(observation_skew)}s skew; limit {max_age_seconds}s)"
            )

    status = "PASS" if not issues else "DATA INCOMPLETE"
    return ValidationResult(status, tuple(issues), observation_skew)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require", action="append", default=[], help="required capability; repeat as needed")
    parser.add_argument("--max-age-seconds", type=int, default=300)
    args = parser.parse_args()
    try:
        runtime = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        print(json.dumps({"runtime_status": "DATA INCOMPLETE", "blocking_issues": [f"invalid JSON: {exc}"]}))
        return 2
    if not isinstance(runtime, dict):
        print(json.dumps({"runtime_status": "DATA INCOMPLETE", "blocking_issues": ["runtime must be an object"]}))
        return 2
    result = validate_runtime(runtime, args.require, max_age_seconds=args.max_age_seconds)
    print(json.dumps(result.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
