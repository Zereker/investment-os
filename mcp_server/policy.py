"""Load the canonical Investment OS behavior and task-specific policy files."""

from __future__ import annotations

from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
SKILL_ROOT: Final = ROOT / "skills" / "investment-os"

TASK_REFERENCES: Final[dict[str, tuple[str, ...]]] = {
    "daily": ("00-constitution.md", "01-daily.md", "05-state.md"),
    "monthly_funding": (
        "00-constitution.md",
        "02-monthly.md",
        "05-state.md",
        "06-data-contract.md",
    ),
    "periodic_review": ("00-constitution.md", "03-periodic.md"),
    "transaction_judgment": ("00-constitution.md", "04-committee.md"),
    "research": ("00-constitution.md", "04-committee.md"),
    "broker_execution": (
        "00-constitution.md",
        "05-state.md",
        "06-data-contract.md",
    ),
    "system_audit": ("00-constitution.md", "06-data-contract.md"),
}


def supported_tasks() -> tuple[str, ...]:
    return tuple(TASK_REFERENCES)


def load_task_context(task: str) -> dict[str, object]:
    """Return the installed Skill plus only the references required for task."""
    normalized = task.strip().lower()
    if normalized not in TASK_REFERENCES:
        expected = ", ".join(supported_tasks())
        raise ValueError(f"unsupported task {task!r}; expected one of: {expected}")

    skill_path = SKILL_ROOT / "SKILL.md"
    references = {
        name: (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
        for name in TASK_REFERENCES[normalized]
    }
    return {
        "task": normalized,
        "skill": skill_path.read_text(encoding="utf-8"),
        "references": references,
        "source": "installed Investment OS distribution",
        "runtime_data_persisted": False,
    }
