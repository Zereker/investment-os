#!/usr/bin/env python3
"""Prove the one-skill plugin runs from an installed cache, not a source checkout."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "investment-os"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def skill_names(root: Path) -> set[str]:
    names: set[str] = set()
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"missing skill frontmatter: {path}"
        frontmatter = text.split("---\n", 2)[1]
        name_line = next((line for line in frontmatter.splitlines() if line.startswith("name:")), "")
        name = name_line.partition(":")[2].strip()
        assert name == path.parent.name, f"skill name mismatch: {path}"
        assert name not in names, f"duplicate installed skill: {name}"
        names.add(name)
    return names


def verify_marketplaces() -> None:
    codex = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    assert codex["name"] == "investment-os"
    assert len(codex["plugins"]) == 1
    codex_entry = codex["plugins"][0]
    assert codex_entry["name"] == "investment-os"
    assert codex_entry["source"] == {"source": "local", "path": "./plugins/investment-os"}
    assert codex_entry["policy"] == {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}
    assert (ROOT / codex_entry["source"]["path"]).resolve() == PLUGIN_ROOT

    claude = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    assert claude["name"] == "investment-os"
    assert len(claude["plugins"]) == 1
    entry = claude["plugins"][0]
    assert entry["name"] == "investment-os"
    assert entry["source"] == "./plugins/investment-os"
    version = (PLUGIN_ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
    assert entry["version"] == version


def main() -> None:
    verify_marketplaces()
    source_skills = skill_names(PLUGIN_ROOT)
    assert source_skills == {"using-investment-os"}

    with tempfile.TemporaryDirectory(prefix="investment-os-install-test-") as temp:
        temp_root = Path(temp)
        version = (PLUGIN_ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
        installed = temp_root / "cache" / "investment-os" / version
        shutil.copytree(PLUGIN_ROOT, installed, ignore=shutil.ignore_patterns(".git", "__pycache__", "artifacts"))
        neutral_cwd = temp_root / "unrelated-user-project"
        neutral_cwd.mkdir()

        assert installed != ROOT
        assert not (installed / ".git").exists()
        assert skill_names(installed) == {"using-investment-os"}
        for source_only in ("tests", "evals", "docs"):
            assert not (installed / source_only).exists(), f"source-only tree leaked into plugin: {source_only}"
        assert not (installed / "scripts").exists(), "runtime scripts remain internal to skill directories"

        for relative in (
            ".plugin-version",
            "skills/using-investment-os/SKILL.md",
            "skills/using-investment-os/references/00-constitution.md",
            "skills/using-investment-os/references/01-operating-manual.md",
            "skills/using-investment-os/references/02-data-contract.md",
            "skills/using-investment-os/references/03-journal.md",
            "skills/broker-runtime/scripts/broker_runtime.py",
            "skills/reconstructing-portfolio-state/scripts/account_reconciliation.py",
            "skills/running-monthly-review/scripts/monthly_execution.py",
            "skills/validating-drawdown-state/scripts/alert_pointer_check.py",
            "skills/execution-runtime/scripts/execution_runtime.py",
        ):
            assert (installed / relative).is_file(), f"installed file missing: {relative}"

        assert sorted(installed.glob("skills/*/SKILL.md")) == [
            installed / "skills" / "using-investment-os" / "SKILL.md"
        ]

        codex_manifest = load_json(installed / ".codex-plugin" / "plugin.json")
        assert codex_manifest["skills"] == "./skills/"
        assert "hooks" not in codex_manifest
        assert codex_manifest["interface"]["privacyPolicyURL"].endswith("/skills/using-investment-os/SKILL.md")

    print("Single-skill plugin installation and cache-isolation tests passed.")


if __name__ == "__main__":
    main()
