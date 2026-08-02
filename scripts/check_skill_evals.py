#!/usr/bin/env python3
"""Validate Investment OS skill behavior scenario coverage and privacy."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SCENARIOS = ROOT / "evals" / "scenarios"

REQUIRED_FIELDS = ("name:", "skills:", "prompt: |", "required:", "forbidden:", "reason:", "synthetic: true")
REQUIRED_SCENARIOS = {
    "manual-figures-are-not-authority",
    "no-inherited-agent-approval",
    "rewording-does-not-reset-intent",
    "research-cannot-enter-production",
    "missing-orders-fails-closed",
}
FORBIDDEN_PRIVATE = re.compile(
    r"\b(?:U\d{5,}|DU\d+|account\s*id|alert\s*id)\b|\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*USD\b",
    re.I,
)


def skill_names() -> set[str]:
    return {path.parent.name for path in SKILLS.glob("*/SKILL.md")}


def parse_list(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []
    values: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith(" "):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:])
    return values


def main() -> None:
    available = skill_names()
    found: set[str] = set()
    for path in sorted(SCENARIOS.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for field in REQUIRED_FIELDS:
            if field not in text:
                raise AssertionError(f"{path}: missing {field}")
        name = text.splitlines()[0].partition(":")[2].strip()
        found.add(name)
        if FORBIDDEN_PRIVATE.search(text):
            raise AssertionError(f"{path}: scenario may contain private runtime data")
        referenced = parse_list(text, "skills:")
        if not referenced:
            raise AssertionError(f"{path}: no skills referenced")
        missing = sorted(set(referenced) - available)
        if missing:
            raise AssertionError(f"{path}: unknown skills: {', '.join(missing)}")
        if not parse_list(text, "required:") or not parse_list(text, "forbidden:"):
            raise AssertionError(f"{path}: required and forbidden behavior lists must be non-empty")

    missing_scenarios = REQUIRED_SCENARIOS - found
    if missing_scenarios:
        raise AssertionError("missing required eval scenarios: " + ", ".join(sorted(missing_scenarios)))

    print("Skill behavior eval scenario checks passed.")


if __name__ == "__main__":
    main()
