#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy

from scripts.decision_packet import DecisionPacket, assert_renderer_preserves
from scripts.daily_brief import build_packet, render_packet, synthetic_payload


def main() -> None:
    packet = build_packet(synthetic_payload())
    packet.validate()
    assert packet.workflow == "daily-review"
    assert packet.runtime_status == "PASS"
    assert packet.decision == "BUY CANDIDATE"
    assert packet.execution_authority == "OWNER AUTHORIZATION REQUIRED"
    assert packet.eligible_channels

    # Determinism: identical input produces exactly the same structured packet.
    assert packet.as_dict() == build_packet(deepcopy(synthetic_payload())).as_dict()

    # Rendering consumes the packet but cannot change machine-authoritative fields.
    rendered = render_packet(packet)
    assert f"Decision Status: **{packet.decision}**" in rendered
    assert f"Execution authority: {packet.execution_authority}" in rendered
    try:
        assert_renderer_preserves(packet, {
            "schema_version": packet.schema_version,
            "workflow": packet.workflow,
            "as_of": packet.as_of,
            "runtime_status": packet.runtime_status,
            "decision": "HOLD",
            "execution_authority": packet.execution_authority,
        })
    except ValueError as exc:
        assert "renderer changed authoritative field: decision" in str(exc)
    else:
        raise AssertionError("renderer was allowed to change decision")

    # Missing runtime input changes the packet before presentation and blocks all candidates.
    incomplete = synthetic_payload()
    incomplete["account_inputs"] = {**incomplete["account_inputs"], "open_orders": False}
    blocked = build_packet(incomplete)
    assert blocked.runtime_status == blocked.decision == "DATA INCOMPLETE"
    assert blocked.blocking_issues == ("open_orders",)
    assert blocked.execution_authority == "NONE"
    assert blocked.eligible_channels  # math remains inspectable, but is not authorized
    assert "停止新的购买候选" in render_packet(blocked)
    assert "BUY CANDIDATE —" not in render_packet(blocked)

    # Contract consistency rejects impossible packet combinations.
    invalid = DecisionPacket(
        schema_version=1, workflow="daily-review", as_of="2030-01-15",
        runtime_status="DATA INCOMPLETE", decision="HOLD", facts={}, calculations={},
        eligible_channels=(), blocking_issues=("missing positions",), attention_items=(),
        next_conditions=(), execution_authority="NONE",
    )
    try:
        invalid.validate()
    except ValueError as exc:
        assert "incomplete runtime" in str(exc)
    else:
        raise AssertionError("invalid runtime/decision combination passed")

    print("Decision packet separation tests passed.")


if __name__ == "__main__":
    main()
