#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "investment-os"
SKILLS = PLUGIN_ROOT / "skills"
CANONICAL = SKILLS / "using-investment-os" / "SKILL.md"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"missing frontmatter: {path}"
    raw = text.split("---\n", 2)[1]
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if line.strip():
            key, sep, value = line.partition(":")
            assert sep, f"invalid frontmatter: {path}: {line}"
            data[key.strip()] = value.strip()
    return data


def test_single_skill() -> None:
    discovered = sorted(SKILLS.glob("*/SKILL.md"))
    assert discovered == [CANONICAL], f"distribution must expose one canonical skill: {discovered}"
    meta = frontmatter(CANONICAL)
    assert meta["name"] == "using-investment-os"
    assert meta["description"].startswith("Use when ")

    text = CANONICAL.read_text(encoding="utf-8")
    for needle in (
        "Portfolio first", "Long term first", "Decision first", "HOLD",
        "Rule 1 — Intent continuity", "Rule 2 — No inherited approval",
        "Rule 3 — No runtime guessing", "Rule 4 — No manual authority",
        "Rule 5 — Operation-scoped authorization", "Rule 6 — No policy override",
        "Rule 7 — Fail closed", "Treat `Daily` as a complete request",
        "A recommendation is not authorization", "Do not prepend policy narration",
        "Repository stores rules, never portfolio", "Runtime account state is private and ephemeral",
    ):
        assert needle in text, f"canonical skill missing: {needle}"


def test_internal_assets() -> None:
    # Old workflow directories may keep scripts, but none may expose another
    # SKILL.md. They are implementation details of one product.
    for path in (
        SKILLS / "using-investment-os" / "references" / "00-constitution.md",
        SKILLS / "using-investment-os" / "references" / "01-operating-manual.md",
        SKILLS / "using-investment-os" / "references" / "02-data-contract.md",
        SKILLS / "using-investment-os" / "references" / "03-journal.md",
        SKILLS / "running-daily-review" / "scripts" / "daily_brief.py",
        SKILLS / "running-monthly-review" / "scripts" / "monthly_execution.py",
        SKILLS / "execution-runtime" / "scripts" / "execution_runtime.py",
    ):
        assert path.is_file(), f"missing internal product asset: {path}"


def test_manifests() -> None:
    claude = json.loads((PLUGIN_ROOT / ".claude-plugin/plugin.json").read_text())
    codex = json.loads((PLUGIN_ROOT / ".codex-plugin/plugin.json").read_text())
    version = (PLUGIN_ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
    assert claude["name"] == codex["name"] == "investment-os"
    assert claude["version"] == codex["version"] == version
    assert codex["skills"] == "./skills/"
    assert "hooks" not in codex
    assert codex["interface"]["privacyPolicyURL"].endswith("/skills/using-investment-os/SKILL.md")
    command = claude["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert "skills/using-investment-os/scripts/claude-session-start" in command


def test_bootstrap() -> None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    bootstrap = SKILLS / "using-investment-os" / "scripts" / "claude-session-start"
    result = subprocess.run(["bash", str(bootstrap)], check=True, capture_output=True, text=True, env=env)
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "INVESTMENT_OS_BOOTSTRAP" in context
    assert "using-investment-os" in context
    assert "installed plugin distribution" in context
    assert "current working directory" in context
    assert "runtime network fetch" in context


def main() -> None:
    test_single_skill()
    test_internal_assets()
    test_manifests()
    test_bootstrap()
    print("Single-skill Investment OS integration tests passed.")


if __name__ == "__main__":
    main()
