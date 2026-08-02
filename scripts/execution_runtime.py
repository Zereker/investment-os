#!/usr/bin/env python3
"""Deterministic Execution Runtime contract validator.

This module does not connect to a broker. It validates an adapter-produced execution
record and enforces operation-specific authorization, single-submit semantics,
read-back, and internally consistent terminal states.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

TERMINAL = {"COMPLETED", "NOT EXECUTED", "EXECUTION UNKNOWN", "VERIFICATION FAILED"}
REQUIRED_STAGES = [
    "PREPARED",
    "CAPABILITY_CHECKED",
    "AUTHORIZED",
    "EXECUTED",
    "READ_BACK",
    "VERIFIED",
    "COMPLETED",
]


def canonical_operation(operation: dict[str, Any]) -> str:
    return json.dumps(operation, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def operation_digest(operation: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_operation(operation).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ValidationResult:
    status: str
    issues: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.status == "COMPLETED" and not self.issues


def validate(record: dict[str, Any]) -> ValidationResult:
    issues: list[str] = []
    operation = record.get("operation")
    if not isinstance(operation, dict) or not operation:
        return ValidationResult("NOT EXECUTED", ("missing normalized operation",))

    expected_digest = operation_digest(operation)
    authorization = record.get("authorization") or {}
    if authorization.get("scope") != "single-operation-current-session":
        issues.append("authorization scope must be single-operation-current-session")
    if authorization.get("operation_digest") != expected_digest:
        issues.append("authorization does not match normalized operation")
    if not authorization.get("owner_explicit"):
        issues.append("explicit owner authorization missing")
    if not authorization.get("session_id"):
        issues.append("authorization session_id missing")

    capability = record.get("capability")
    adapter = record.get("adapter") or {}
    supported = set(adapter.get("supported_capabilities") or [])
    if not isinstance(capability, str) or not capability.startswith("Broker."):
        issues.append("invalid broker capability")
    elif capability not in supported:
        issues.append("adapter does not support required capability")

    stages = record.get("stages") or []
    terminal = record.get("status")
    if terminal not in TERMINAL:
        issues.append("invalid terminal status")

    submit_count = record.get("submit_count", 0)
    if not isinstance(submit_count, int) or submit_count < 0:
        issues.append("invalid submit_count")
    if submit_count > 1:
        issues.append("operation submitted more than once")

    if issues:
        return ValidationResult("NOT EXECUTED" if submit_count == 0 else "EXECUTION UNKNOWN", tuple(issues))

    if terminal == "NOT EXECUTED":
        if submit_count != 0:
            issues.append("NOT EXECUTED conflicts with submit_count")
        return ValidationResult(terminal, tuple(issues))

    if submit_count != 1:
        issues.append("executed terminal state requires exactly one submit")

    if stages != REQUIRED_STAGES[: len(stages)]:
        issues.append("execution stages are out of order or skipped")

    write_result = record.get("write_result")
    read_back = record.get("read_back")
    verification = record.get("verification") or {}

    if terminal in {"COMPLETED", "VERIFICATION FAILED"}:
        if not isinstance(write_result, dict):
            issues.append("write_result missing")
        if not isinstance(read_back, dict):
            issues.append("authoritative read_back missing")
        if not verification.get("performed"):
            issues.append("verification not performed")
        if not isinstance(verification.get("evidence"), str) or not verification.get("evidence", "").strip():
            issues.append("verification evidence missing")

    if terminal == "COMPLETED":
        if stages != REQUIRED_STAGES:
            issues.append("COMPLETED requires full lifecycle")
        if verification.get("passed") is not True:
            issues.append("COMPLETED requires passed verification")
    elif terminal == "VERIFICATION FAILED":
        if verification.get("passed") is not False:
            issues.append("VERIFICATION FAILED requires failed verification")
    elif terminal == "EXECUTION UNKNOWN":
        if "EXECUTED" not in stages:
            issues.append("EXECUTION UNKNOWN requires a possible submission")
        if "VERIFIED" in stages or "COMPLETED" in stages:
            issues.append("unknown execution cannot be verified or completed")

    return ValidationResult(terminal, tuple(issues))


def main() -> int:
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    result = validate(json.loads(args.record.read_text(encoding="utf-8")))
    print(json.dumps({"status": result.status, "issues": list(result.issues)}, ensure_ascii=False))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
