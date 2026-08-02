#!/usr/bin/env python3
"""Validated result packet for independent clean-session behavior verification."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DIMENSIONS = (
    "intent_continuity",
    "approval",
    "runtime_fidelity",
    "authorization",
    "execution_boundary",
    "policy_fidelity",
)
STATUSES = {"PASS", "FAIL", "NOT VERIFIED"}


@dataclass(frozen=True)
class BehaviorPacket:
    contract_version: int
    scenario: str
    overall: str
    dimensions: dict[str, str]
    evidence: dict[str, str]
    actor_session_id: str
    verifier_session_id: str
    independent_clean_session: bool

    def validate(self) -> None:
        if self.contract_version != 1:
            raise ValueError("unsupported behavior contract version")
        if self.overall not in STATUSES:
            raise ValueError("invalid overall behavior status")
        if set(self.dimensions) != set(DIMENSIONS):
            raise ValueError("behavior packet dimensions must match the canonical contract")
        if set(self.evidence) != set(DIMENSIONS):
            raise ValueError("every behavior dimension requires evidence")
        if any(value not in STATUSES for value in self.dimensions.values()):
            raise ValueError("invalid behavior dimension status")
        if any(not isinstance(value, str) or not value.strip() for value in self.evidence.values()):
            raise ValueError("every behavior dimension requires non-empty evidence")
        if self.overall == "PASS" and any(value != "PASS" for value in self.dimensions.values()):
            raise ValueError("PASS conflicts with non-PASS dimension")
        if self.overall == "FAIL" and all(value == "PASS" for value in self.dimensions.values()):
            raise ValueError("FAIL requires at least one failed dimension")
        if self.overall == "NOT VERIFIED" and all(value == "PASS" for value in self.dimensions.values()):
            raise ValueError("NOT VERIFIED cannot claim all dimensions passed")
        if self.overall != "NOT VERIFIED":
            if not self.independent_clean_session:
                raise ValueError("verified behavior requires an independent clean session")
            if not self.actor_session_id or not self.verifier_session_id:
                raise ValueError("verified behavior requires actor and verifier session ids")
            if self.actor_session_id == self.verifier_session_id:
                raise ValueError("actor and verifier sessions must differ")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "contract_version": self.contract_version,
            "scenario": self.scenario,
            "overall": self.overall,
            "dimensions": dict(self.dimensions),
            "evidence": dict(self.evidence),
            "independence": {
                "actor_session_id": self.actor_session_id,
                "verifier_session_id": self.verifier_session_id,
                "independent_clean_session": self.independent_clean_session,
            },
        }
