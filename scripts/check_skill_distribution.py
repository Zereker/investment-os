#!/usr/bin/env python3
"""Validate the cross-harness Investment OS composable skill distribution."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "investment-os"
SKILLS = PLUGIN_ROOT / "skills"
VERSION = (PLUGIN_ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
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
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", VERSION):
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

    claude = load_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
    codex = load_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")
    for label, manifest in (("Claude", claude), ("Codex", codex)):
        if manifest.get("name") != "investment-os":
            raise AssertionError(f"{label} manifest has wrong name")
        if manifest.get("version") != VERSION:
            raise AssertionError(f"{label} manifest version must match .plugin-version ({VERSION})")
        if manifest.get("repository") != "https://github.com/Zereker/investment-os":
            raise AssertionError(f"{label} manifest has wrong repository")
    if codex.get("skills") != "./skills/":
        raise AssertionError("Codex manifest must distribute ./skills/")
    if "hooks" in codex:
        raise AssertionError("Codex manifest must rely on native Skill discovery without a hooks field")
    if (ROOT / "hooks" / "hooks.json").exists():
        raise AssertionError("Codex must not auto-discover the Claude SessionStart hook")

    command = claude["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    bootstrap = PLUGIN_ROOT / "skills" / "using-investment-os" / "scripts" / "claude-session-start"
    if "skills/using-investment-os/scripts/claude-session-start" not in command or not bootstrap.is_file():
        raise AssertionError("Claude inline SessionStart bootstrap is not wired")

    codex_marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    codex_entry = codex_marketplace["plugins"][0]
    if codex_entry.get("name") != "investment-os":
        raise AssertionError("Codex marketplace must expose investment-os")
    if codex_entry.get("source") != {"source": "local", "path": "./plugins/investment-os"}:
        raise AssertionError("Codex marketplace must install the nested plugin")
    if codex_entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        raise AssertionError("Codex marketplace must declare complete install policy")

    claude_marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    claude_entry = claude_marketplace["plugins"][0]
    if claude_entry.get("name") != "investment-os" or claude_entry.get("source") != "./plugins/investment-os":
        raise AssertionError("Claude marketplace must install the nested plugin")
    if claude_entry.get("version") != VERSION:
        raise AssertionError("Claude marketplace version must match .plugin-version")

    for needle in (
        "Installed distribution root",
        "../../.plugin-version",
        "references/project-contract.md",
        "references/production-contract.md",
        "current working directory",
        "Do not clone, fetch",
    ):
        if needle not in router:
            raise AssertionError(f"router missing installed-runtime boundary: {needle}")

    docs = (ROOT / "docs" / "SKILL-DISTRIBUTION.md").read_text(encoding="utf-8")
    for needle in (
        "composable skill library",
        "Claude Code",
        "Codex",
        "Testing model",
        "Behavior scenarios: DEFINED",
        "Behavior execution: NOT YET VERIFIED",
        "Plugin distribution version",
        "Installed-runtime boundary",
        # The three layers must stay distinct, or the same install ends up with
        # two Mandatory Starts: one telling the session to resolve the default
        # branch, another telling it the distribution is what executes.
        "Canonical authority",
        "Session input",
        "Provenance",
    ):
        if needle not in docs:
            raise AssertionError(f"distribution docs missing: {needle}")

    print("Composable skill distribution checks passed.")


if __name__ == "__main__":
    main()
