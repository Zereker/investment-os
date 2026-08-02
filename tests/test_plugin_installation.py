#!/usr/bin/env python3
"""Prove the plugin runs from an installed cache, not a source checkout."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise AssertionError(f"missing skill frontmatter: {path}")
        frontmatter = text.split("---\n", 2)[1]
        name_line = next(
            (line for line in frontmatter.splitlines() if line.startswith("name:")),
            "",
        )
        name = name_line.partition(":")[2].strip()
        if name != path.parent.name:
            raise AssertionError(f"skill name mismatch: {path}")
        if name in names:
            raise AssertionError(f"duplicate installed skill: {name}")
        names.add(name)
    return names


def verify_marketplaces() -> None:
    codex = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert codex["name"] == "investment-os"
    assert len(codex["plugins"]) == 1
    codex_entry = codex["plugins"][0]
    assert codex_entry["name"] == "investment-os"
    assert codex_entry["source"] == {"source": "local", "path": "./"}
    assert codex_entry["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert (ROOT / codex_entry["source"]["path"]).resolve() == ROOT

    claude = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    assert claude["name"] == "investment-os"
    assert len(claude["plugins"]) == 1
    claude_entry = claude["plugins"][0]
    assert claude_entry["name"] == "investment-os"
    assert claude_entry["source"] == "./"
    assert (ROOT / claude_entry["source"]).resolve() == ROOT
    version = (ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
    assert claude_entry["version"] == version


def main() -> None:
    verify_marketplaces()
    source_skills = skill_names(ROOT)

    with tempfile.TemporaryDirectory(prefix="investment-os-install-test-") as temp:
        temp_root = Path(temp)
        installed = temp_root / "cache" / "investment-os" / "0.3.0"
        shutil.copytree(
            ROOT,
            installed,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "artifacts"),
        )
        neutral_cwd = temp_root / "unrelated-user-project"
        neutral_cwd.mkdir()

        assert installed != ROOT
        assert not (installed / ".git").exists()
        assert skill_names(installed) == source_skills
        for relative in (
            ".plugin-version",
            "AGENTS.md",
            "PROJECT.md",
            "PRODUCTION.md",
            "scripts/broker_runtime.py",
            "scripts/decision_packet.py",
        ):
            assert (installed / relative).is_file(), f"installed file missing: {relative}"

        codex_manifest = load_json(installed / ".codex-plugin" / "plugin.json")
        assert codex_manifest["skills"] == "./skills/"
        assert "hooks" not in codex_manifest
        assert not (installed / "hooks" / "hooks.json").exists()

        claude_manifest = load_json(installed / ".claude-plugin" / "plugin.json")
        hook = claude_manifest["hooks"]["SessionStart"][0]["hooks"][0]
        assert hook["command"] == 'bash "${CLAUDE_PLUGIN_ROOT}/scripts/claude-session-start"'

        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(installed)
        result = subprocess.run(
            ["bash", str(installed / "scripts" / "claude-session-start")],
            cwd=neutral_cwd,
            env=env,
            text=True,
            capture_output=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        context = payload["hookSpecificOutput"]["additionalContext"]
        assert "INVESTMENT_OS_BOOTSTRAP" in context
        assert "installed plugin distribution" in context
        assert "current working directory" in context
        assert "runtime network fetch" in context
        assert str(ROOT) not in context

        router_dir = installed / "skills" / "using-investment-os"
        for relative in ("../../.plugin-version", "../../PROJECT.md", "../../PRODUCTION.md"):
            assert (router_dir / relative).resolve().is_file(), relative

    print("Native plugin installation and cache-isolation tests passed.")


if __name__ == "__main__":
    main()
