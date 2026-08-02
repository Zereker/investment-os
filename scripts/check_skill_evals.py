#!/usr/bin/env python3
"""Validate Investment OS behavior scenario definitions and eval integrity."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SCENARIOS = ROOT / "evals" / "scenarios"

COMMON_FIELDS = ("name:", "skills:", "required:", "forbidden:", "reason:", "synthetic: true")
REQUIRED_SCENARIOS = {
    "manual-figures-are-not-authority",
    "no-inherited-agent-approval",
    "rewording-does-not-reset-intent",
    "research-cannot-enter-production",
    "missing-orders-fails-closed",
    "stale-drawdown-alert-tier",
    "incomplete-data-no-estimation",
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
        for field in COMMON_FIELDS:
            if field not in text:
                raise AssertionError(f"{path}: missing {field}")
        has_prompt = re.search(r"^prompt:\s*\|", text, re.M) is not None
        has_turns = re.search(r"^turns:\s*$", text, re.M) is not None
        if has_prompt == has_turns:
            raise AssertionError(f"{path}: define exactly one top-level prompt or turns field")
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

    rewording = (SCENARIOS / "rewording-does-not-reset-intent.yaml").read_text(encoding="utf-8")
    if re.search(r"^turns:\s*$", rewording, re.M) is None or rewording.count("  - role: user") < 2:
        raise AssertionError("rewording scenario must be a genuine multi-turn user sequence")
    if "same purchase" in rewording.lower() or "stopped earlier" in rewording.lower():
        raise AssertionError("rewording scenario must not disclose that the second request repeats the first")

    runner = (ROOT / "evals" / "run.py").read_text(encoding="utf-8")
    for needle in (
        "NOT VERIFIED: no verifier configured",
        "--actor-only",
        "validate_verifier_result",
        "separate_session",
        "verifier_session_id",
        "VERIFIED PASS",
        "VERIFIED FAIL",
    ):
        if needle not in runner:
            raise AssertionError(f"eval runner missing integrity control: {needle}")

    print("Skill behavior eval scenario and integrity checks passed.")


if __name__ == "__main__":
    main()
