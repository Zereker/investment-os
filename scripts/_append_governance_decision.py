#!/usr/bin/env python3
"""One-shot PR branch edit; removed after Decision-Log migration."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
log_path = ROOT / "Decision-Log.md"
log = log_path.read_text(encoding="utf-8")
entry = """

## 2026-08-02 — Skill 分发版本与政策版本解耦

### 决定

- 删除 `07-Releases/`。长期有效的系统决定统一进入 `Decision-Log.md`，缺陷与防复发措施进入 `BUGLOG.md`，具体实现历史由 commit、PR、Git tag 与 GitHub Release 留痕。
- 当前投资政策只由默认分支 HEAD 与精确 commit SHA 标识，不再用仓库内的 `vX.Y` 发布文件表示政策版本。
- Skill / Plugin 分发保留独立 SemVer，由 `.plugin-version` 作为唯一来源并同步到 Claude Code 与 Codex manifest；首个独立分发版本为 `0.1.0`。
- 行为场景定义与行为执行分开：CI 只验证 YAML 结构、Skill 引用、覆盖和隐私。**真实 Agent 行为 Eval 尚未验证**；只有 clean-session actor 与独立 verifier 实际运行通过后，才能宣称对应 Harness 的行为覆盖。

### 原因

- `07-Releases/` 与现行政策及 `Decision-Log.md` 重复，可能成为脱离 CI 的第二份参数来源。
- 插件 SemVer 服务安装、升级、兼容和回滚，不等于投资政策版本。
- 场景文件合法只证明测试定义存在，不能证明 Agent 在压力下真的遵守 Skill。

### 非交易声明

本决定只修正治理、分发版本和测试陈述，不改变投资宇宙、配置、资金公式、回撤规则或任何交易权限，不授权任何订单。
"""
if "Skill 分发版本与政策版本解耦" not in log:
    marker = "本文件记录改变系统方向或产生长期影响的决定。日常定投不逐笔记录。"
    log = log.replace(marker, marker + entry, 1)
    log_path.write_text(log, encoding="utf-8")

readme_path = ROOT / "README.md"
readme = readme_path.read_text(encoding="utf-8")
readme = re.sub(r"^- `07-Releases/`：.*\n", "", readme, flags=re.M)
anchor = "- `Decision-Log.md`：改变系统方向或产生长期影响的决定\n"
if ".plugin-version" not in readme and anchor in readme:
    readme = readme.replace(
        anchor,
        anchor
        + "- `.plugin-version`：仅用于 Skill / Plugin 分发的独立 SemVer，不表示投资政策版本\n"
        + "- Git tags / GitHub Releases：插件分发发布记录；现行政策始终以默认分支 HEAD 为准\n",
    )
readme_path.write_text(readme, encoding="utf-8")

print("Decision log governance entry applied.")
