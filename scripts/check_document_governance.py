#!/usr/bin/env python3
"""Prevent entry documents from drifting behind the runtime architecture."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    value = text(path)
    missing = [needle for needle in needles if needle not in value]
    if missing:
        raise AssertionError(f"{path}: missing current contract text: {missing}")


def forbid(path: str, *needles: str) -> None:
    value = text(path)
    present = [needle for needle in needles if needle in value]
    if present:
        raise AssertionError(f"{path}: contains retired contract text: {present}")


def versionless_title(path: str) -> None:
    first = text(path).splitlines()[0]
    if re.search(r"\bv\d+(?:\.\d+)+\b", first, re.I):
        raise AssertionError(f"{path}: policy version must not appear in title: {first}")


def main() -> None:
    for path in ("README.md", "PROJECT.md", "PRODUCTION.md"):
        versionless_title(path)

    require(
        "PRODUCTION.md",
        "Broker Adapter",
        "DecisionPacket",
        "execution-runtime",
        "当前会话存在账户所有者明确授权",
        "只提交一次",
        "权威 Broker 状态",
        "授权不跨操作、不跨会话",
        "EXECUTION UNKNOWN",
        "IC 批准只表示该候选可以进入执行授权阶段",
    )
    forbid(
        "PRODUCTION.md",
        "批准只允许进入人工下单",
        "账户所有者仍需在 IBKR 中亲手确认",
        "v4.x 期间",
    )

    require(
        "CLAUDE.md",
        "using-investment-os",
        "broker-runtime",
        "DecisionPacket",
        "execution-runtime",
        "account_reconciliation.py",
        "Skill 只保存流程，不保存易变参数",
        "Real Harness behavior: NOT YET VERIFIED",
        "bash tests/run-all.sh",
    )
    forbid("CLAUDE.md", "永远不下单", "当前 v4.6")

    require(
        "02-Operating-System/Monthly-Workflow.md",
        "Account Reconciliation",
        "--open-orders-status clear|conflicting|unknown",
        "默认 `unknown`",
        "缺失 `F` 不得静默按零处理",
        "cash_transactions",
        "DATA INCOMPLETE / HOLD",
        "execution-runtime",
    )

    require(
        "README.md",
        "仓库保存规则，不保存个人组合",
        "Broker Runtime",
        "DecisionPacket",
        "Execution Runtime",
        ".plugin-version",
    )
    forbid("README.md", "Policy compatibility anchor", "系统永不下单")

    require(
        "PROJECT.md",
        "Observe → Understand → Decide → Monitor → Repeat",
        "Repository Stores Knowledge, Never Portfolio",
        "Owner-Authorized Broker Execution",
        "Decision Engine / DecisionPacket",
        "现行政策以默认分支 HEAD 为准",
    )

    print("Documentation governance checks passed.")


if __name__ == "__main__":
    main()
