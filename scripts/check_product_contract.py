#!/usr/bin/env python3
"""Validate product, skill, agent-control and public-repository privacy contracts."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    }
    forbidden_parts = {"runtime", "account-data", "portfolio-data", "private-data"}
    violations: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT)
        lowered_parts = {part.lower() for part in rel.parts[:-1]}
        if rel.name.lower() in forbidden_names or lowered_parts & forbidden_parts:
            violations.append(str(rel))
    if violations:
        raise AssertionError(
            "runtime portfolio artifacts must not live in the public repository:\n"
            + "\n".join(sorted(violations))
        )


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
    require(
        "PROJECT.md",
        "Observe → Understand → Decide → Monitor → Repeat",
        "Repository Stores Knowledge, Never Portfolio",
        "Runtime Data Is Ephemeral",
        "Human Executes Trades",
        "相同的有效输入和相同的生产规则，应得到相同、可解释、可复核的结论",
    )
    require(
        "02-Operating-System/Daily-Report-Contract.md",
        "Investment Daily Report",
        "Fact: 可验证数据或计算结果",
        "Production Decision",
        "Next Observation Conditions",
        "自动提交日报到公开仓库",
    )
    require(
        "01-Constitution/Investment-Universe.md",
        "SPYM", "QQQM", "SOXX", "Production 是封闭投资宇宙", "Out-of-Universe",
        "任何 AI、脚本、日报或临时会话都无权自行扩展投资宇宙",
    )
    require(
        "scripts/daily_brief.py",
        'UNIVERSE = ("SPYM", "QQQM", "SOXX")', "DATA INCOMPLETE",
        "Why Not the Others", "never writes inputs or output to disk",
    )
    require("README.md", "PROJECT.md", "Daily-Report-Contract.md", "仓库保存规则，不保存个人组合")
    require("07-Releases/v6.0.md", "Three-ETF Daily Brief MVP", "不改变目标权重", "scripts/daily_brief.py")
    require(
        "AGENTS.md",
        "This contract contains procedure, never investment policy parameters",
        "Fresh Rule Source", "Fresh Runtime State", "Source and Authority Declaration",
        "No Inherited Approval", "Behavioral and Procedural Control Gate",
        "Independent Second Opinion", "Order and Position Verification",
        "Journal Single-Writer Rule", "Manual figures, screenshots, pasted tables and prior reports",
        "Agents must not push directly to the protected default branch",
    )
    require("07-Releases/v6.1.md", "Agent Control Gate", "control replication, not convenience", "does not store personal trading incidents", "does not change")
    require(
        "skills/README.md",
        "platform-neutral execution and enforcement layer",
        ".claude-plugin/", ".codex-plugin/", "references/authority-and-runtime.md",
        "parameter-free", "check_skill_distribution.py",
    )
    require(
        "skills/investment-os/SKILL.md",
        "name: investment-os", "description: Use when", "Before Any Formal Run",
        "Route the Task", "Runtime and Authority", "Control Gates",
        "Deterministic Execution", "Hard Boundaries", "Completion Standard",
        "references/authority-and-runtime.md", "references/task-routing.md",
        "references/control-gates.md",
    )
    require(
        "07-Releases/v6.2.md",
        "Portable Investment OS Skill",
        "thin skill + authoritative repository + fresh broker state",
        "The skill is an execution and enforcement layer, not a second policy source",
        "No personal trading history", "Strategy Impact",
    )
    reject_policy_parameters("AGENTS.md")
    reject_policy_parameters("skills/investment-os/SKILL.md")
    reject_runtime_artifacts()
    print("Product contract checks passed.")


if __name__ == "__main__":
    main()
