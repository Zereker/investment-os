#!/usr/bin/env python3
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

from mcp_server import policy


def main() -> None:
    assert policy.supported_tasks() == (
        "daily",
        "monthly_funding",
        "periodic_review",
        "transaction_judgment",
        "research",
        "broker_execution",
        "system_audit",
    )

    daily = policy.load_task_context("daily")
    assert daily["task"] == "daily"
    assert set(daily["references"]) == {
        "00-constitution.md",
        "01-daily.md",
        "05-state.md",
    }
    assert "02-monthly.md" not in daily["references"]
    assert daily["runtime_data_persisted"] is False

    monthly = policy.load_task_context("monthly_funding")
    assert set(monthly["references"]) == {
        "00-constitution.md",
        "02-monthly.md",
        "05-state.md",
        "06-data-contract.md",
    }

    try:
        policy.load_task_context("unknown")
    except ValueError as exc:
        assert "unsupported task" in str(exc)
    else:
        raise AssertionError("unknown task was accepted")

    with tempfile.TemporaryDirectory(prefix="investment-os-mcp-") as temp:
        fake_root = Path(temp)
        fake_skill = fake_root / "skills" / "investment-os"
        (fake_skill / "references").mkdir(parents=True)
        (fake_skill / "SKILL.md").write_text("canonical skill", encoding="utf-8")
        for name in policy.TASK_REFERENCES["daily"]:
            (fake_skill / "references" / name).write_text(name, encoding="utf-8")
        with patch.object(policy, "SKILL_ROOT", fake_skill):
            loaded = policy.load_task_context("daily")
        assert loaded["skill"] == "canonical skill"

    print("MCP policy loader tests passed.")


if __name__ == "__main__":
    main()
