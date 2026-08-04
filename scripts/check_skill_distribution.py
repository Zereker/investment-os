#!/usr/bin/env python3
"""Validate the Investment OS distribution: skill packaging, product contract,
and document governance.

Merged scope (v0.6.4): check_release_governance.py was merged here in v0.5.1;
check_product_contract.py and check_document_governance.py were merged here in
the engineering cleanup. Every assertion from the retired checkers is
preserved — the merge only removes duplicate entry points and one duplicated
policy-parameter rejector.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "investment-os"
PLUGIN = "plugins/investment-os"
SKILLS_DIR = PLUGIN_ROOT / "skills"
SKILLS = f"{PLUGIN}/skills"
REFERENCES = f"{SKILLS}/using-investment-os/references"
VERSION = (PLUGIN_ROOT / ".plugin-version").read_text(encoding="utf-8").strip()
REQUIRED_SKILLS = {
    "using-investment-os",
    "financial-agent-discipline",
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
# The single policy-parameter rejector: distributed prose carries procedure,
# never investment parameters (formerly duplicated across two checkers).
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


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path}: missing required product contract text: {needle}")


def reject_policy_parameters(path: str) -> None:
    text = read(path)
    violations = [name for name, pattern in FORBIDDEN_POLICY.items() if pattern.search(text)]
    if violations:
        raise AssertionError(f"{path} must contain procedure, never policy parameters: " + ", ".join(violations))


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
    reject_policy_parameters(str(path.relative_to(ROOT)))


def check_skill_packaging() -> None:
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", VERSION):
        raise AssertionError(".plugin-version must contain a plain SemVer value")

    actual = {path.parent.name for path in SKILLS_DIR.glob("*/SKILL.md")}
    missing = REQUIRED_SKILLS - actual
    if missing:
        raise AssertionError("missing required skills: " + ", ".join(sorted(missing)))
    if "investment-os" in actual:
        raise AssertionError("monolithic investment-os skill must not coexist with the composable library")
    for path in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        validate_skill(path)

    router_path = SKILLS_DIR / "using-investment-os" / "SKILL.md"
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
    expected_privacy_url = (
        "https://github.com/Zereker/investment-os/blob/master/plugins/"
        "investment-os/skills/using-investment-os/references/product-contract.md"
    )
    if codex.get("interface", {}).get("privacyPolicyURL") != expected_privacy_url:
        raise AssertionError("Codex manifest privacy policy URL must target product-contract.md")
    if (ROOT / "hooks" / "hooks.json").exists():
        raise AssertionError("Codex must not auto-discover the Claude SessionStart hook")

    command = claude["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    bootstrap = SKILLS_DIR / "using-investment-os" / "scripts" / "claude-session-start"
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
        "references/product-contract.md",
        "references/agent-execution-contract.md",
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


def check_release_governance() -> None:
    # merged from check_release_governance.py, v0.5.1
    for retired in (
        "check_policy_consistency_legacy.py",
        "check_release_governance.py",
        # merged into this checker in the engineering cleanup
        "check_product_contract.py",
        "check_document_governance.py",
    ):
        if (ROOT / "scripts" / retired).exists():
            raise AssertionError(f"retired checker must not exist: scripts/{retired}")
    checker = (ROOT / "scripts" / "check_policy_consistency.py").read_text(encoding="utf-8")
    for forbidden in ("ast.NodeTransformer", "exec(compile", "check_policy_consistency_legacy.py"):
        if forbidden in checker:
            raise AssertionError(f"policy checker must execute directly; found {forbidden!r}")
    if (ROOT / "07-Releases").exists():
        raise AssertionError(
            "07-Releases is retired; durable decisions belong in Decision-Log.md "
            "and distribution releases belong in Git tags/GitHub Releases")
    decision_log = (ROOT / "Decision-Log.md").read_text(encoding="utf-8")
    for needle in (
        "Skill 分发版本与政策版本解耦",
        "真实 Agent 行为 Eval 尚未验证",
        "07-Releases",
    ):
        if needle not in decision_log:
            raise AssertionError(f"Decision-Log.md missing governance decision: {needle}")


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
        if rel.name.lower() in forbidden_names or ({p.lower() for p in rel.parts[:-1]} & forbidden_parts):
            violations.append(str(rel))
    if violations:
        raise AssertionError("runtime portfolio artifacts must not live in the public repository:\n" + "\n".join(sorted(violations)))


def check_product_contract() -> None:
    # merged from check_product_contract.py in the engineering cleanup.
    # the product boundary: mission, the LLM-judgment split, execution
    # authority, privacy. Per the 2026-08-04 owner ruling, code verifies facts
    # and protects execution while the LLM makes the investment judgment; the
    # North Star is explainable/traceable/verifiable, not byte-identical output.
    require(
        f"{REFERENCES}/product-contract.md",
        "Observe → Understand → Decide → Monitor → Repeat",
        "Repository Stores Knowledge, Never Portfolio",
        "Runtime Data Is Ephemeral",
        "Owner-Authorized Broker Execution",
        "由 LLM 综合事实、政策和研究形成投资判断",
        "代码验证事实并保护执行，LLM 负责投资判断",
        "系统追求结论可解释、证据可追溯、执行可验证",
        "IC 结论不是 Broker 授权，不能替代当前会话中针对具体操作的所有者明确授权",
        "现行政策以默认分支 HEAD 为规范来源",
        "已安装会话读取本次分发的不可变快照",
        "`F` 未知不得默认为零",
        "仓库不维护行情、ETF 成分、issuer 或 GICS 中央数据库",
    )
    # the closed universe, its non-expansion rule, and the sole legacy
    # conflict-resolution exception live in the constitution
    require(
        f"{REFERENCES}/00-constitution.md",
        "Production 是封闭投资宇宙",
        "Out-of-Universe",
        "任何 AI、脚本、日报或临时会话都无权自行扩展投资宇宙",
        "冲突解决例外（沿用旧制）",
        "以操作手册为准",
        "原 `02-*` 优先于 `03-*` 的顺序不因合并改变",
    )
    # the daily product contract lives in the operating manual
    require(
        f"{REFERENCES}/01-operating-manual.md",
        "Investment Daily Report",
        "Fact: 可验证数据或计算结果",
        "Production Decision",
        "Next Observation Conditions",
        "自动提交日报到公开仓库",
    )
    # deterministic engine boundaries (script-level pins are code contracts)
    require(
        f"{SKILLS}/running-daily-review/scripts/daily_brief.py",
        'UNIVERSE = ("SPYM", "QQQM", "SOXX")',
        "DATA INCOMPLETE", "Why Not the Others",
        "never writes inputs or output to disk",
        "build_packet", "render_packet", "--packet-json",
    )
    require(
        f"{SKILLS}/running-daily-review/scripts/decision_packet.py",
        "class DecisionPacket", "assert_renderer_preserves",
        "renderer changed authoritative field", "execution_authority",
    )
    require(
        f"{SKILLS}/execution-runtime/scripts/execution_runtime.py",
        "operation_digest", "submit_count", "EXECUTION UNKNOWN",
        "authoritative read_back missing",
    )
    require("README.md", "product-contract.md", "仓库保存规则，不保存个人组合")
    require(
        f"{REFERENCES}/agent-execution-contract.md",
        "This contract contains procedure, never investment policy parameters",
        "Fresh Rule Source", "Fresh Runtime State",
        "Source and Authority Declaration", "No Inherited Approval",
        "Behavioral and Procedural Control Gate", "Independent Second Opinion",
        "Order and Position Verification", "Broker Execution Runtime",
        "Journal Single-Writer Rule",
        "Manual figures, screenshots, pasted tables and prior reports",
        "Agents must not push directly to the protected default branch",
    )
    # The distributed skill is the authority for the session that loaded it. It
    # must not send the agent off to fetch a newer policy version at runtime:
    # a marketplace install has no repository to resolve, and a stale copy
    # cannot certify its own freshness.
    require(
        f"{SKILLS}/using-investment-os/SKILL.md",
        "name: using-investment-os",
        "Mandatory start", "Never inherit approval", "execution-runtime",
        "financial-agent-discipline",
        "Resolve packaged files relative to this `SKILL.md`",
        "Do not clone, fetch, or substitute another Investment OS checkout at runtime",
        "the policy source used",
        "the operating manual prevails",
    )
    require(
        f"{SKILLS}/financial-agent-discipline/SKILL.md",
        "name: financial-agent-discipline",
        "No inherited approval", "No runtime guessing", "No manual authority",
        "Fail closed", "observable",
        # The source obligation carries its consequence here, once.
        "A result without a source is not a formal result",
    )
    require("README.md", "唯一沿用旧制的例外", "以操作手册为准")
    for skill in SKILLS_DIR.rglob("*.md"):
        rel = str(skill.relative_to(ROOT))
        # auditing-investment-os reviews the repository itself, where git exists
        if "auditing-investment-os" in rel:
            continue
        if "repository HEAD" in read(rel):
            raise AssertionError(f"{rel}: distributed skills must not require resolving repository HEAD at runtime")
    require(f"{SKILLS}/execution-runtime/SKILL.md", "name: execution-runtime", "single-operation-current-session", "read back authoritative broker state", "no silent retry")
    reject_policy_parameters(f"{REFERENCES}/agent-execution-contract.md")
    reject_runtime_artifacts()


# --- document governance (merged from check_document_governance.py) ----------
# Rules-first scope (v0.5.0): structural checks only — the consolidated rule
# files exist, titles carry no policy version, and the honest-verification
# declaration survives everywhere it is required.

REQUIRED_REFERENCES = (
    "00-constitution.md",
    "01-operating-manual.md",
    "02-data-contract.md",
    "03-journal.md",
    "product-contract.md",
    "agent-execution-contract.md",
    "claude-code-entry.md",
    "claude-code-tools.md",
    "codex-tools.md",
)

# run-all.sh phrases it as "remains NOT YET VERIFIED", so match the two parts
NOT_YET_VERIFIED = ("Real Harness behavior", "NOT YET VERIFIED")
NOT_YET_VERIFIED_PATHS = (
    "README.md",
    f"{REFERENCES}/product-contract.md",
    f"{REFERENCES}/claude-code-entry.md",
    "tests/run-all.sh",
    # docs/SKILL-DISTRIBUTION.md carries its own form of the declaration,
    # already enforced by check_skill_packaging()
)


def versionless_title(path: str) -> None:
    first = read(path).splitlines()[0]
    if re.search(r"\bv\d+(?:\.\d+)+\b", first, re.I):
        raise AssertionError(f"{path}: policy version must not appear in title: {first}")


def check_document_governance() -> None:
    missing = [name for name in REQUIRED_REFERENCES
               if not (ROOT / REFERENCES / name).is_file()]
    if missing:
        raise AssertionError("missing consolidated rule files: " + ", ".join(missing))

    for path in ("README.md", f"{REFERENCES}/product-contract.md",
                 f"{REFERENCES}/00-constitution.md", f"{REFERENCES}/01-operating-manual.md",
                 f"{REFERENCES}/02-data-contract.md"):
        versionless_title(path)

    for path in NOT_YET_VERIFIED_PATHS:
        value = read(path)
        if any(part not in value for part in NOT_YET_VERIFIED):
            raise AssertionError(f"{path}: must carry the declaration {' … '.join(NOT_YET_VERIFIED)!r}")

    # a claim of behavior coverage from green CI is the one dishonest sentence
    # this checker still patrols for
    for path in NOT_YET_VERIFIED_PATHS:
        if "Real Harness behavior: VERIFIED" in read(path):
            raise AssertionError(f"{path}: claims verified harness behavior")


def main() -> None:
    check_skill_packaging()
    check_release_governance()
    check_product_contract()
    check_document_governance()
    print("Skill distribution, product contract, and document governance checks passed.")


if __name__ == "__main__":
    main()
