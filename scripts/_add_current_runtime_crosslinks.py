#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

updates = {
    "PRODUCTION.md": """

## 10. 倾斜路径术语

- **回补至目标**：不提高已批准风险预算，只在现行规则允许范围内恢复被市场漂移压低的已批准权重；
- **提高倾斜**：推进或扩大风险预算，必须进入完整 IC，不能伪装成例行回补。
""",
    "02-Operating-System/Monthly-Workflow.md": """

## 12. 回补与提高倾斜

`--lookthrough-current` 只证明相关当季核查有效，不创造风险预算。**回补至目标**必须保持现行执行上限不变；任何推进执行上限或扩大预算的行为都属于**提高倾斜**，必须进入完整 IC。
""",
    "CLAUDE.md": """

## 11. Deterministic Entry Points

月度确定性计算入口是 `scripts/monthly_execution.py`。调用前必须先通过 Broker Runtime、账户对账、权威 `F` 与 Open Orders 状态门；脚本输出候选，不自动形成执行权限。
""",
}

for rel, appendix in updates.items():
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    marker = appendix.strip().splitlines()[0]
    if marker not in text:
        path.write_text(text.rstrip() + "\n" + appendix, encoding="utf-8")
