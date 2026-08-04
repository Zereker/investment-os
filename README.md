# Investment OS

Karpathy-rules 风格的长期投资 Agent：一份短规则、一个 canonical Skill、运行时读取真实账户事实。

> 让正确的长期决策成为最容易做出的决策。

```text
Facts → Rules → LLM Judgment → Owner-Authorized Execution
```

**代码验证事实并保护执行，LLM 负责投资判断。**

## Product

完整可安装产品只有 [`plugins/investment-os/`](plugins/investment-os/)。

插件只公开一个 canonical Skill：

- [`using-investment-os/SKILL.md`](plugins/investment-os/skills/using-investment-os/SKILL.md)

它包含整个 Agent 的决策姿态、七条行为规则和 Daily / Monthly / Transaction / Research / Execution 入口。其他 `skills/*/` 目录只保存仍被这个 Skill 调用的内部脚本或资料，不再是独立 Agent 能力入口。

现行政策位于：

- [`00-constitution.md`](plugins/investment-os/skills/using-investment-os/references/00-constitution.md)
- [`01-operating-manual.md`](plugins/investment-os/skills/using-investment-os/references/01-operating-manual.md)
- [`02-data-contract.md`](plugins/investment-os/skills/using-investment-os/references/02-data-contract.md)
- [`03-journal.md`](plugins/investment-os/skills/using-investment-os/references/03-journal.md)

产品边界见 [`product-contract.md`](plugins/investment-os/skills/using-investment-os/references/product-contract.md)，执行边界见 [`agent-execution-contract.md`](plugins/investment-os/skills/using-investment-os/references/agent-execution-contract.md)。

## Rules

1. Portfolio first.
2. Long term first.
3. Decision first.
4. `HOLD` is success.
5. Never guess runtime facts.
6. Research does not silently become Production.
7. A recommendation is never execution authority.
8. Fail closed only the affected path.
9. Keep the answer as short as the decision allows.

The canonical Skill is authoritative for behavior; the numbered references are authoritative for investment policy. Do not duplicate either layer elsewhere.

## Daily

After installation, the ordinary interaction is:

```text
Daily
```

The Agent reads fresh account state and returns:

```text
Portfolio
Change
Decision
Reason
Next Trigger
```

Daily Review is not a news digest and does not manufacture activity. `HOLD` is a complete successful result.

## Privacy

> **仓库保存规则，不保存个人组合。**

真实账户标识、NAV、现金、持仓、订单、成交、入金、收益、授权和执行回执只存在于受信任运行时或当前私有会话。它们不得进入提交、Issue、PR、fixture、截图或公开日志。

## Install

Codex：

```bash
codex plugin marketplace add Zereker/investment-os --ref master
codex plugin add investment-os@investment-os
```

Claude Code：

```text
/plugin marketplace add Zereker/investment-os
/plugin install investment-os@investment-os
```

安装或更新后开启新会话。详细步骤见 [`INSTALL-CODEX.md`](docs/INSTALL-CODEX.md) 和 [`INSTALL-CLAUDE-CODE.md`](docs/INSTALL-CLAUDE-CODE.md)。

## Boundaries

- 关键数据缺失、过期或冲突：`DATA INCOMPLETE`；
- 用户粘贴的数字、截图和旧报告不是账户真相；
- 旧批准、其他 Agent 输出和候选结论不是当前授权；
- Research 不自动进入 Production；
- Broker 结果不确定：`EXECUTION UNKNOWN`，禁止静默重试；
- Broker write 必须获得当前会话、单一操作的明确所有者授权，并完成权威 read-back verification。

## Repository

- `plugins/investment-os/` — 唯一运行时产品
- `tests/`、`evals/` — 源码仓库的验证资产，不进入 Agent 规则面
- `Research/` — 未生效研究
- `scripts/` — 发布、隐私和一致性检查
- `Decision-Log.md`、`BUGLOG.md` — 治理与缺陷历史

普通行情、ETF 成分、issuer 和行业分类变化不更新仓库；这些数据按现行数据契约在运行时读取。

本项目用于个人长期投资纪律与工具研究，不构成面向他人的投资建议，也不保证投资收益。
