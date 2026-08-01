#!/usr/bin/env python3
"""Validate the v5 product contract and public-repository privacy boundary."""

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
    """Reject common paths that would persist personal portfolio state."""
    forbidden_names = {
        "account.json", "portfolio.json", "positions.json", "balances.json",
        "orders.json", "trades.json", "fills.json", "daily-report.md",
        "daily_report.md", "ibkr.json", "ibkr.csv",
    }
    forbidden_parts = {"runtime", "account-data", "portfolio-data", "private-data"}
    violations: list[str] = []

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(ROOT)
        lowered_parts = {part.lower() for part in rel.parts[:-1]}
        if rel.name.lower() in forbidden_names:
            violations.append(str(rel))
        elif lowered_parts & forbidden_parts:
            violations.append(str(rel))

    if violations:
        raise AssertionError(
            "runtime portfolio artifacts must not live in the public repository:\n"
            + "\n".join(sorted(violations))
        )


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
        "README.md",
        "PROJECT.md",
        "Daily-Report-Contract.md",
        "仓库保存规则，不保存个人组合",
    )
    reject_runtime_artifacts()
    print("Product contract checks passed.")


if __name__ == "__main__":
    main()
