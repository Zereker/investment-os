#!/usr/bin/env python3
"""Validate the single-skill Investment OS distribution and privacy boundary."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "investment-os"
SKILLS = PLUGIN_ROOT / "skills"
CANONICAL = SKILLS / "using-investment-os" / "SKILL.md"
REFERENCES = SKILLS / "using-investment-os" / "references"
VERSION = (PLUGIN_ROOT / ".plugin-version").read_text(encoding="utf-8").strip()

FORBIDDEN_VENDOR_TERMS = ("Claude Code tool", "Codex tool", "api_tool", "web.run", "Task tool")
FORBIDDEN_POLICY = {
    "percentages": re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*%"),
    "tier labels": re.compile(r"\bT[1-9]\b"),
    "production identifiers": re.compile(r"\b(?:SPYM|QQQM|SOXX)\b"),
    "allocation formulas": re.compile(r"\b(?:A_basis|A_stage|A_execution_cap|D_max|G_0)\b"),
    "hard-coded money": re.compile(r"\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:USD|美元)\b", re.I),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(path: Path, *needles: str) -> None:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path.relative_to(ROOT)} missing: {needle}")


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("canonical SKILL.md must start with YAML frontmatter")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise AssertionError("canonical SKILL.md frontmatter is not closed")
    result: dict[str, str] = {}
    for line in parts[1].splitlines():
        if line.strip():
            key, sep, value = line.partition(":")
            if not sep:
                raise AssertionError(f"invalid frontmatter line: {line}")
            result[key.strip()] = value.strip()
    return result


def check_single_skill() -> None:
    discovered = sorted(SKILLS.glob("*/SKILL.md"))
    if discovered != [CANONICAL]:
        names = [str(path.relative_to(PLUGIN_ROOT)) for path in discovered]
        raise AssertionError(f"Investment OS must expose exactly one canonical skill: {names}")

    text = CANONICAL.read_text(encoding="utf-8")
    meta = parse_frontmatter(text)
    if meta.get("name") != "using-investment-os":
        raise AssertionError("canonical skill name must match its directory")
    if not meta.get("description", "").startswith("Use when "):
        raise AssertionError("canonical skill description must start with 'Use when '")
    for term in FORBIDDEN_VENDOR_TERMS:
        if term in text:
            raise AssertionError(f"canonical skill contains vendor tool term: {term}")
    violations = [name for name, pattern in FORBIDDEN_POLICY.items() if pattern.search(text)]
    if violations:
        raise AssertionError("canonical skill contains policy parameters: " + ", ".join(violations))

    for needle in (
        "Portfolio first", "Long term first", "Decision first", "HOLD",
        "Rule 1 — Intent continuity", "Rule 2 — No inherited approval",
        "Rule 3 — No runtime guessing", "Rule 4 — No manual authority",
        "Rule 5 — Operation-scoped authorization", "Rule 6 — No policy override",
        "Rule 7 — Fail closed", "Treat `Daily` as a complete request",
        "A recommendation is not authorization", "Do not prepend policy narration",
        "Repository stores rules, never portfolio", "Runtime account state is private and ephemeral",
        "Code and tools own facts and irreversible controls", "Production stays closed",
        "../../.plugin-version", "references/00-constitution.md",
        "references/01-operating-manual.md", "references/02-data-contract.md",
        "references/03-journal.md", "current working directory", "Do not clone, fetch",
    ):
        if needle not in text:
            raise AssertionError(f"canonical skill missing product rule: {needle}")


def check_manifests() -> None:
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", VERSION):
        raise AssertionError(".plugin-version must contain plain SemVer")

    claude = load_json(PLUGIN_ROOT / ".claude-plugin" / "plugin.json")
    codex = load_json(PLUGIN_ROOT / ".codex-plugin" / "plugin.json")
    for label, manifest in (("Claude", claude), ("Codex", codex)):
        if manifest.get("name") != "investment-os":
            raise AssertionError(f"{label} manifest has wrong name")
        if manifest.get("version") != VERSION:
            raise AssertionError(f"{label} manifest version must match {VERSION}")
        if manifest.get("repository") != "https://github.com/Zereker/investment-os":
            raise AssertionError(f"{label} manifest has wrong repository")
    if codex.get("skills") != "./skills/" or "hooks" in codex:
        raise AssertionError("Codex must use native discovery for ./skills/")

    privacy = (
        "https://github.com/Zereker/investment-os/blob/master/plugins/"
        "investment-os/skills/using-investment-os/SKILL.md"
    )
    if codex.get("interface", {}).get("privacyPolicyURL") != privacy:
        raise AssertionError("Codex privacy policy URL is stale")

    command = claude["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    bootstrap = SKILLS / "using-investment-os" / "scripts" / "claude-session-start"
    if "skills/using-investment-os/scripts/claude-session-start" not in command or not bootstrap.is_file():
        raise AssertionError("Claude bootstrap is not wired")

    claude_marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    if claude_marketplace["plugins"][0].get("version") != VERSION:
        raise AssertionError("Claude marketplace version must match .plugin-version")


def check_product_assets() -> None:
    for path in (
        REFERENCES / "00-constitution.md",
        REFERENCES / "01-operating-manual.md",
        REFERENCES / "02-data-contract.md",
        REFERENCES / "03-journal.md",
        SKILLS / "running-daily-review" / "scripts" / "daily_brief.py",
        SKILLS / "running-daily-review" / "scripts" / "decision_packet.py",
        SKILLS / "running-monthly-review" / "scripts" / "monthly_execution.py",
        SKILLS / "execution-runtime" / "scripts" / "execution_runtime.py",
    ):
        if not path.is_file():
            raise AssertionError(f"missing internal product asset: {path.relative_to(ROOT)}")

    require(
        REFERENCES / "00-constitution.md",
        "Production 是封闭投资宇宙",
        "Out-of-Universe",
        "任何 AI、脚本、日报或临时会话都无权自行扩展投资宇宙",
    )
    require(
        REFERENCES / "01-operating-manual.md",
        "Investment Daily Report", "Production Decision", "Next Observation Conditions",
    )
    require(
        SKILLS / "running-daily-review" / "scripts" / "daily_brief.py",
        "DATA INCOMPLETE", "build_packet", "render_packet", "--packet-json",
    )
    require(
        SKILLS / "execution-runtime" / "scripts" / "execution_runtime.py",
        "operation_digest", "submit_count", "EXECUTION UNKNOWN", "authoritative read_back missing",
    )


def check_repository_hygiene() -> None:
    for retired in (
        "check_policy_consistency_legacy.py", "check_release_governance.py",
        "check_product_contract.py", "check_document_governance.py",
    ):
        if (ROOT / "scripts" / retired).exists():
            raise AssertionError(f"retired checker must not exist: scripts/{retired}")
    for retired in ("product-contract.md", "agent-execution-contract.md"):
        if (REFERENCES / retired).exists():
            raise AssertionError(f"retired contract layer must not exist: {retired}")
    if (ROOT / "07-Releases").exists():
        raise AssertionError("07-Releases is retired")


def reject_runtime_artifacts() -> None:
    forbidden_names = {
        "account.json", "portfolio.json", "positions.json", "balances.json",
        "orders.json", "trades.json", "fills.json", "daily-report.md",
        "daily_report.md", "daily-brief.md", "daily_brief.md", "ibkr.json", "ibkr.csv",
        "execution-receipt.json", "authorization.json",
    }
    forbidden_parts = {"runtime", "account-data", "portfolio-data", "private-data"}
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT)
        if rel.name.lower() in forbidden_names or ({part.lower() for part in rel.parts[:-1]} & forbidden_parts):
            violations.append(str(rel))
    if violations:
        raise AssertionError("runtime portfolio artifacts found:\n" + "\n".join(sorted(violations)))


def main() -> None:
    check_single_skill()
    check_manifests()
    check_product_assets()
    check_repository_hygiene()
    reject_runtime_artifacts()
    print("Single-skill distribution, policy assets, and privacy checks passed.")


if __name__ == "__main__":
    main()
