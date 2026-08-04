#!/usr/bin/env python3
"""Validated deterministic facts, controls, and candidate limits for the Agent."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

VALID_DECISIONS = {
    "HOLD", "WAIT", "BUY CANDIDATE", "SELL CANDIDATE",
    "REVIEW", "REJECT", "DATA INCOMPLETE",
}
VALID_RUNTIME = {"PASS", "DATA INCOMPLETE"}
VALID_EXECUTION_AUTHORITY = {"NONE", "OWNER AUTHORIZATION REQUIRED", "AUTHORIZED OPERATION ONLY"}


@dataclass(frozen=True)
class DecisionPacket:
    schema_version: int
    workflow: str
    as_of: str
    runtime_status: str
    decision: str
    facts: dict[str, Any]
    calculations: dict[str, Any]
    source_status: dict[str, dict[str, Any]]
    channel_status: dict[str, str]
    eligible_channels: tuple[dict[str, Any], ...]
    blocking_issues: tuple[str, ...]
    attention_items: tuple[str, ...]
    next_conditions: tuple[str, ...]
    execution_authority: str

    def validate(self) -> None:
        if self.schema_version != 2:
            raise ValueError("unsupported DecisionPacket schema_version")
        if not self.workflow.strip() or not self.as_of.strip():
            raise ValueError("workflow and as_of are required")
        if self.runtime_status not in VALID_RUNTIME:
            raise ValueError("invalid runtime_status")
        if self.decision not in VALID_DECISIONS:
            raise ValueError("invalid decision")
        if self.execution_authority not in VALID_EXECUTION_AUTHORITY:
            raise ValueError("invalid execution_authority")
        if self.runtime_status == "DATA INCOMPLETE" and self.decision != "DATA INCOMPLETE":
            raise ValueError("incomplete runtime must produce DATA INCOMPLETE")
        if self.decision == "DATA INCOMPLETE" and not self.blocking_issues:
            raise ValueError("DATA INCOMPLETE requires blocking_issues")
        if self.decision != "DATA INCOMPLETE" and self.blocking_issues:
            raise ValueError("complete decision cannot retain blocking_issues")
        if self.runtime_status == "DATA INCOMPLETE" and self.eligible_channels:
            raise ValueError("incomplete runtime cannot expose eligible channels")
        if self.runtime_status == "DATA INCOMPLETE" and self.execution_authority != "NONE":
            raise ValueError("incomplete runtime cannot retain execution authority")
        if not isinstance(self.source_status, dict) or not self.source_status:
            raise ValueError("source_status is required")
        for name, status in self.source_status.items():
            if not isinstance(name, str) or not isinstance(status, dict):
                raise ValueError("source_status entries must be objects")
            if status.get("status") not in {"available", "unavailable", "stale", "conflicting"}:
                raise ValueError(f"invalid source status: {name}")
        if not isinstance(self.channel_status, dict) or not self.channel_status:
            raise ValueError("channel_status is required")
        valid_channel_status = {"PASS", "HOLD", "DATA INCOMPLETE"}
        if any(status not in valid_channel_status for status in self.channel_status.values()):
            raise ValueError("invalid channel_status")
        for channel in self.eligible_channels:
            if not isinstance(channel, dict) or not isinstance(channel.get("name"), str):
                raise ValueError("eligible channel must contain name")
            amount = channel.get("amount")
            if not isinstance(amount, (int, float)) or isinstance(amount, bool) or amount < 0:
                raise ValueError("eligible channel amount must be nonnegative")

    def as_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)
