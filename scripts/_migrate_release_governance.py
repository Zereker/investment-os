#!/usr/bin/env python3
"""One-shot branch migration for release/version/eval governance."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


# 1. Consolidate durable governance into Decision-Log.md.
log = read("Decision-Log.md")
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
    write("Decision-Log.md", log)

# 2. Remove the retired release mirror directory.
release_dir = ROOT / "07-Releases"
if release_dir.exists():
    shutil.rmtree(release_dir)

# 3. Remove stale release-file assertions from the legacy policy checker.
policy_path = ROOT / "scripts/check_policy_consistency.py"
policy = policy_path.read_text(encoding="utf-8")
lines = policy.splitlines()
out: list[str] = []
for line in lines:
    if "07-Releases/" not in line:
        out.append(line)
        continue
    stripped = line.strip()
    if stripped.startswith("require(") and stripped.endswith(")"):
        continue
    # Remove a release path element from tuples used by forbid/read loops.
    cleaned = re.sub(r'\s*"07-Releases/[^\"]+",?', "", line)
    if cleaned.strip() not in {"", "):", "("}:
        out.append(cleaned)
policy = "\n".join(out) + "\n"
policy_path.write_text(policy, encoding="utf-8")

# 4. README no longer presents release mirrors as a repository authority.
readme = read("README.md")
readme = re.sub(r"^- `07-Releases/`：.*\n", "", readme, flags=re.M)
if ".plugin-version" not in readme:
    anchor = "- `Decision-Log.md`：改变系统方向或产生长期影响的决定\n"
    replacement = (
        anchor
        + "- `.plugin-version`：仅用于 Skill / Plugin 分发的独立 SemVer，不表示投资政策版本\n"
        + "- Git tags / GitHub Releases：插件分发发布记录；现行政策始终以默认分支 HEAD 为准\n"
    )
    readme = readme.replace(anchor, replacement)
write("README.md", readme)

# 5. Make eval status unambiguous.
evals = read("evals/README.md")
evals = evals.replace(
    "`evals/` verifies real agent behavior under pressure.",
    "`evals/` defines and can execute real-agent behavior checks under pressure; scenario files alone do not verify behavior.",
)
status = """

## Current verification status

- **Behavior scenarios: DEFINED**
- **Behavior execution: NOT YET VERIFIED**

PR CI runs `check_skill_evals.py`, which validates scenario structure, references, coverage, and privacy only. It does not launch Claude Code or Codex. Do not describe a green PR check as behavioral coverage.
"""
if "Behavior execution: NOT YET VERIFIED" not in evals:
    evals = evals.replace("## Execution tiers", status + "\n## Execution tiers")
write("evals/README.md", evals)

tests = read("tests/README.md")
tests = tests.replace(
    "Behavioral compliance belongs in `evals/`, where clean real-agent sessions are tested against synthetic pressure scenarios.",
    "Behavior scenarios and the optional real-agent runner live in `evals/`. PR CI validates the scenario definitions only; behavioral compliance remains unverified until clean sessions are actually executed and independently checked.",
)
write("tests/README.md", tests)

# 6. Wire release governance into deterministic tests and CI.
run_all = read("tests/run-all.sh")
if "check_release_governance.py" not in run_all:
    run_all = run_all.replace(
        "python3 scripts/check_product_contract.py\n",
        "python3 scripts/check_product_contract.py\npython3 scripts/check_release_governance.py\n",
    )
write("tests/run-all.sh", run_all)

workflow = read(".github/workflows/policy-consistency.yml")
if "Validate release and version governance" not in workflow:
    needle = "      - name: Validate composable cross-harness skill distribution\n"
    step = (
        "      - name: Validate release and version governance\n"
        "        env:\n"
        "          PYTHONDONTWRITEBYTECODE: \"1\"\n"
        "        run: python3 scripts/check_release_governance.py\n"
    )
    workflow = workflow.replace(needle, step + needle)
write(".github/workflows/policy-consistency.yml", workflow)

# 7. Test manifests against the independent version source.
test_path = ROOT / "tests/test_skill_system.py"
test = test_path.read_text(encoding="utf-8")
old = '    assert claude["version"] == codex["version"]\n'
new = (
    '    version = (ROOT / ".plugin-version").read_text(encoding="utf-8").strip()\n'
    '    assert claude["version"] == codex["version"] == version\n'
)
if old in test:
    test = test.replace(old, new)
test_path.write_text(test, encoding="utf-8")

# 8. Ensure the product contract invokes the dedicated governance guard by existence.
product_path = ROOT / "scripts/check_product_contract.py"
product = product_path.read_text(encoding="utf-8")
if "check_release_governance.py" not in product:
    product = product.replace(
        "    reject_runtime_artifacts()\n",
        "    require(\"scripts/check_release_governance.py\", \"07-Releases is retired\", \".plugin-version\")\n    reject_runtime_artifacts()\n",
    )
product_path.write_text(product, encoding="utf-8")

# 9. Sanity checks for the migration itself.
if (ROOT / "07-Releases").exists():
    raise SystemExit("release directory still exists")
if 'VERSION = "6.4.0"' in read("scripts/check_skill_distribution.py"):
    raise SystemExit("hard-coded plugin version survived")
if "Behavior execution: NOT YET VERIFIED" not in read("docs/SKILL-DISTRIBUTION.md"):
    raise SystemExit("eval status remains ambiguous")

print("Governance migration complete.")
