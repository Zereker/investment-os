#!/usr/bin/env python3
"""Validate product, agent-control, skill and public-repository privacy contracts.

Rules-first scope (v0.5.0): this checker keeps the REAL invariants — no runtime
account artifacts in the repo, no policy parameters inside distributed skill
prose, no runtime HEAD resolution in distributed skills, and the load-bearing
contract statements that define the product boundary. The long per-file prose
inventories were retired with the 29->9 rule consolidation.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "plugins/investment-os"
SKILLS = f"{PLUGIN}/skills"
REFERENCES = f"{SKILLS}/using-investment-os/references"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path}: missing required product contract text: {needle}")


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


def reject_policy_parameters(path: str) -> None:
    text = read(path)
    forbidden = {
        "percentages": re.compile(r"(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*%"),
        "allocation formulas": re.compile(r"\b(?:A_basis|A_stage|A_execution_cap|D_max|G_0)\b"),
        "drawdown tiers": re.compile(r"\bT[1-9]\b"),
        "production tickers": re.compile(r"\b(?:SPYM|QQQM|SOXX)\b"),
        "hard-coded money": re.compile(r"\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*(?:USD|美元)\b", re.I),
    }
    violations = [name for name, pattern in forbidden.items() if pattern.search(text)]
    if violations:
        raise AssertionError(f"{path} must contain procedure, never policy parameters: " + ", ".join(violations))


def main() -> None:
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
    for skill in (ROOT / SKILLS).rglob("*.md"):
        rel = str(skill.relative_to(ROOT))
        # auditing-investment-os reviews the repository itself, where git exists
        if "auditing-investment-os" in rel:
            continue
        if "repository HEAD" in read(rel):
            raise AssertionError(f"{rel}: distributed skills must not require resolving repository HEAD at runtime")
    require(f"{SKILLS}/execution-runtime/SKILL.md", "name: execution-runtime", "single-operation-current-session", "read back authoritative broker state", "no silent retry")
    reject_policy_parameters(f"{REFERENCES}/agent-execution-contract.md")
    for skill in (ROOT / SKILLS).glob("*/SKILL.md"):
        reject_policy_parameters(str(skill.relative_to(ROOT)))
    reject_runtime_artifacts()
    print("Product contract checks passed.")


if __name__ == "__main__":
    main()
