#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
updates = {
    "README.md": """

## Data Maintenance Boundary

仓库不维护重复的中央证券数据库。行情、ETF 成分、issuer 和行业分类按已登记来源在运行时读取；只有规则、契约、公开证据或工具变化才提交。**普通数据变化不更新项目**。
""",
    "PRODUCTION.md": """

## 11. 数据维护边界

仓库不维护行情、ETF成分、issuer或GICS中央数据库。普通巡检不写仓库；运行时数据和普通市场变化只存在于当前会话。只有规则、契约、公开证据或工具发生变化时才提交。
""",
}
for rel, appendix in updates.items():
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    marker = appendix.strip().splitlines()[0]
    if marker not in text:
        path.write_text(text.rstrip() + "\n" + appendix, encoding="utf-8")
