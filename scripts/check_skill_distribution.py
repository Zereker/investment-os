#!/usr/bin/env python3
"""Validate the cross-harness Investment OS skill distribution."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "investment-os" / "SKILL.md"
VERSION = "6.4.0"


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    try:
        raw = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise AssertionError("SKILL.md frontmatter is not closed") from exc
    result: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise AssertionError(f"invalid frontmatter line: {line}")
        result[key.strip()] = value.strip()
    return result


def main() -> None:
    text = SKILL.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)

    if frontmatter.get("name") != "investment-os":
        raise AssertionError("skill name must be investment-os")
    description = frontmatter.get("description", "")
    if not description.startswith("Use when "):
        raise AssertionError("skill description must start with 'Use when '")
    if len(description) > 500:
        raise AssertionError("skill description should remain concise")

    required_references = {
        "references/authority-and-runtime.md",
        "references/task-routing.md",
        "references/control-gates.md",
    }
    for relative in required_references:
        if relative not in text:
            raise AssertionError(f"SKILL.md must link {relative}")
        if not (SKILL.parent / relative).is_file():
            raise AssertionError(f"missing skill reference: {relative}")

    forbidden_vendor_terms = (
        "Claude Code tool",
        "Codex tool",
        "api_tool",
        "web.run",
        "Task tool",
    )
    for term in forbidden_vendor_terms:
        if term in text:
            raise AssertionError(f"platform-neutral skill contains vendor tool term: {term}")

    forbidden_policy = {
        "percentages": re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*%"),
        "tier labels": re.compile(r"\bT[1-9]\b"),
        "production identifiers": re.compile(r"\b(?:SPYM|QQQM|SOXX)\b"),
        "allocation formulas": re.compile(r"\b(?:A_basis|A_stage|A_execution_cap|D_max|G_0)\b"),
        "hard-coded money": re.compile(r"\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:USD|美元)\b", re.I),
    }
    violations = [name for name, pattern in forbidden_policy.items() if pattern.search(text)]
    if violations:
        raise AssertionError("SKILL.md contains policy parameters: " + ", ".join(violations))

    claude = load_json(ROOT / ".claude-plugin" / "plugin.json")
    codex = load_json(ROOT / ".codex-plugin" / "plugin.json")
    for name, manifest in (("Claude", claude), ("Codex", codex)):
        if manifest.get("name") != "investment-os":
            raise AssertionError(f"{name} manifest has wrong name")
        if manifest.get("version") != VERSION:
            raise AssertionError(f"{name} manifest version must be {VERSION}")
        if manifest.get("repository") != "https://github.com/Zereker/investment-os":
            raise AssertionError(f"{name} manifest has wrong repository")

    if codex.get("skills") != "./skills/":
        raise AssertionError("Codex manifest must distribute ./skills/")
    if codex.get("hooks") != {}:
        raise AssertionError("Codex manifest must not load repository hooks")

    docs = (ROOT / "docs" / "SKILL-DISTRIBUTION.md").read_text(encoding="utf-8")
    for needle in ("platform-neutral skill source", "Claude Code", "Codex", "Acceptance tests"):
        if needle not in docs:
            raise AssertionError(f"distribution docs missing: {needle}")

    print("Skill distribution checks passed.")


if __name__ == "__main__":
    main()
