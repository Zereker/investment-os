#!/usr/bin/env python3
"""Validate the cross-harness Investment OS composable skill distribution."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
VERSION = (ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
REQUIRED_SKILLS = {
    "using-investment-os",
    "reconstructing-portfolio-state",
    "validating-drawdown-state",
    "enforcing-behavioral-controls",
    "running-daily-review",
    "running-monthly-review",
    "evaluating-transaction-candidates",
    "routing-investment-research",
    "auditing-investment-os",
}
FORBIDDEN_VENDOR_TERMS = ("Claude Code tool", "Codex tool", "api_tool", "web.run", "Task tool")
FORBIDDEN_POLICY = {
    "percentages": re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*%"),
    "tier labels": re.compile(r"\bT[1-9]\b"),
    "production identifiers": re.compile(r"\b(?:SPYM|QQQM|SOXX)\b"),
    "allocation formulas": re.compile(r"\b(?:A_basis|A_stage|A_execution_cap|D_max|G_0)\b"),
    "hard-coded money": re.compile(r"\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:USD|美元)\b", re.I),
}


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise AssertionError("SKILL.md frontmatter is not closed")
    result: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise AssertionError(f"invalid frontmatter line: {line}")
        result[key.strip()] = value.strip()
    return result


def validate_skill(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)
    expected_name = path.parent.name
    if frontmatter.get("name") != expected_name:
        raise AssertionError(f"{path}: name must match directory {expected_name}")
    description = frontmatter.get("description", "")
    if not description.startswith("Use when "):
        raise AssertionError(f"{path}: description must start with 'Use when '")
    if len(description) > 500:
        raise AssertionError(f"{path}: description should remain concise")
    for term in FORBIDDEN_VENDOR_TERMS:
        if term in text:
            raise AssertionError(f"{path}: contains vendor tool term {term}")
    violations = [name for name, pattern in FORBIDDEN_POLICY.items() if pattern.search(text)]
    if violations:
        raise AssertionError(f"{path}: contains policy parameters: {', '.join(violations)}")


def main() -> None:
    if not re.fullmatch(r"0|[1-9]\d*\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", VERSION):
        raise AssertionError(".plugin-version must contain a plain SemVer value")

    actual = {path.parent.name for path in SKILLS.glob("*/SKILL.md")}
    missing = REQUIRED_SKILLS - actual
    if missing:
        raise AssertionError("missing required skills: " + ", ".join(sorted(missing)))
    if "investment-os" in actual:
        raise AssertionError("monolithic investment-os skill must not coexist with the composable library")
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        validate_skill(path)

    router_path = SKILLS / "using-investment-os" / "SKILL.md"
    router = router_path.read_text(encoding="utf-8")
    for name in REQUIRED_SKILLS - {"using-investment-os"}:
        if name not in router:
            raise AssertionError(f"router must reference {name}")
    for mapping in ("references/claude-code-tools.md", "references/codex-tools.md"):
        if mapping not in router or not (router_path.parent / mapping).is_file():
            raise AssertionError(f"router mapping missing: {mapping}")

    claude = load_json(ROOT / ".claude-plugin" / "plugin.json")
    codex = load_json(ROOT / ".codex-plugin" / "plugin.json")
    for label, manifest in (("Claude", claude), ("Codex", codex)):
        if manifest.get("name") != "investment-os":
            raise AssertionError(f"{label} manifest has wrong name")
        if manifest.get("version") != VERSION:
            raise AssertionError(f"{label} manifest version must match .plugin-version ({VERSION})")
        if manifest.get("repository") != "https://github.com/Zereker/investment-os":
            raise AssertionError(f"{label} manifest has wrong repository")
    if codex.get("skills") != "./skills/":
        raise AssertionError("Codex manifest must distribute ./skills/")
    if codex.get("hooks") != {}:
        raise AssertionError("Codex manifest must not load repository hooks")

    hooks = load_json(ROOT / "hooks" / "hooks.json")
    command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    if "session-start" not in command or not (ROOT / "hooks" / "session-start").is_file():
        raise AssertionError("Claude SessionStart bootstrap is not wired")

    docs = (ROOT / "docs" / "SKILL-DISTRIBUTION.md").read_text(encoding="utf-8")
    for needle in (
        "composable skill library",
        "Claude Code",
        "Codex",
        "Testing model",
        "Behavior scenarios: DEFINED",
        "Behavior execution: NOT YET VERIFIED",
        "Plugin distribution version",
    ):
        if needle not in docs:
            raise AssertionError(f"distribution docs missing: {needle}")

    print("Composable skill distribution checks passed.")


if __name__ == "__main__":
    main()
