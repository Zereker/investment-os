#!/usr/bin/env python3
"""Enforce policy-history and plugin-distribution version boundaries."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    legacy_checker = ROOT / "scripts" / "check_policy_consistency_legacy.py"
    if legacy_checker.exists():
        raise AssertionError("legacy policy checker must not exist")

    checker = (ROOT / "scripts" / "check_policy_consistency.py").read_text(encoding="utf-8")
    for forbidden in ("ast.NodeTransformer", "exec(compile", "check_policy_consistency_legacy.py"):
        if forbidden in checker:
            raise AssertionError(f"policy checker must execute directly; found {forbidden!r}")

    retired = ROOT / "07-Releases"
    if retired.exists():
        files = sorted(str(path.relative_to(ROOT)) for path in retired.rglob("*") if path.is_file())
        detail = "\n".join(files) if files else str(retired.relative_to(ROOT))
        raise AssertionError(
            "07-Releases is retired; durable decisions belong in Decision-Log.md "
            "and distribution releases belong in Git tags/GitHub Releases:\n" + detail
        )

    version = (ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", version):
        raise AssertionError(".plugin-version must contain plain SemVer")

    for path in (ROOT / ".claude-plugin/plugin.json", ROOT / ".codex-plugin/plugin.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("version") != version:
            raise AssertionError(f"{path.relative_to(ROOT)} version must match .plugin-version")

    decision_log = (ROOT / "Decision-Log.md").read_text(encoding="utf-8")
    for needle in (
        "Skill 分发版本与政策版本解耦",
        "真实 Agent 行为 Eval 尚未验证",
        "07-Releases",
    ):
        if needle not in decision_log:
            raise AssertionError(f"Decision-Log.md missing governance decision: {needle}")

    print("Release governance checks passed.")


if __name__ == "__main__":
    main()
