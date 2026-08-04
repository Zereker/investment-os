# Investment OS

一套开源的长期投资决策操作系统。它帮助投资者持续观察市场与组合、理解变化、依据预先批准的规则形成一致且可审计的决策，并明确下一观察条件。

> Investment OS 的目标，是让正确的决策成为最容易做出的决策。

完整产品定义与生产运行边界见 [product-contract.md](plugins/investment-os/skills/using-investment-os/references/product-contract.md)，跨 Agent 运行契约见 [agent-execution-contract.md](plugins/investment-os/skills/using-investment-os/references/agent-execution-contract.md)，行为纪律见 [financial-agent-discipline](plugins/investment-os/skills/financial-agent-discipline/SKILL.md)，每日产品规范见 [01-operating-manual.md](plugins/investment-os/skills/using-investment-os/references/01-operating-manual.md) 日报契约部分。

## Decision Loop

```text
Observe → Understand → Decide → Monitor → Repeat
```

每日巡检必须回答：发生了什么、组合状态如何、现行规则意味着什么、哪些动作被授权、需要注意什么、下一观察条件是什么。每日巡检不是每日交易；`HOLD` 是完整且成功的结果。

## Privacy Boundary

> **仓库保存规则，不保存个人组合。**

公开仓库只保存政策、流程、公式、状态机、数据契约、测试和不含个人状态的研究证据。

真实账户标识、NAV、现金、持仓、股数、订单、成交、入金、收益、税务、授权和执行回执只存在于受信任运行时或当前私有会话，不得进入提交、Issue、PR、日志、fixture、截图或快照。

## Architecture

```text
Broker Adapter
→ Broker Runtime
→ Account Reconciliation
→ Decision Engine / DecisionPacket
→ Behavioral Controls
→ Presentation
→ Execution Runtime（仅有单次授权时）
```

- Broker Runtime 验证能力、时间、来源和数据完整性；
- DecisionPacket 保存机器权威的事实、计算、阻塞项、结论和执行权限；
- LLM 只负责编排、解释和格式化，不得重算或改写机器结果；
- Execution Runtime 只在当前会话获得针对一个完整单次操作的所有者明确授权后执行，并要求权威 read-back verification。

## Agent Skills

Investment OS 通过一个 router 分发多个可组合 Skills：

- `using-investment-os`
- `financial-agent-discipline`
- `broker-runtime`
- `reconstructing-portfolio-state`
- `enforcing-behavioral-controls`
- `running-daily-review`
- `running-monthly-review`
- `evaluating-transaction-candidates`
- `validating-drawdown-state`
- `execution-runtime`
- `routing-investment-research`
- `auditing-investment-os`

可安装产品完整位于 [`plugins/investment-os/`](plugins/investment-os/skills/using-investment-os/SKILL.md)。每个 Skill 自带自己的流程、参考文件和确定性脚本；Claude Code 与 Codex 共享同一插件源码。Skill 流程不复制易变投资参数，每次运行必须重读本次分发的编号政策参考文件（规范来源为默认分支 HEAD，但会话不在运行时获取更新）。

### Install once, load natively

用户不需要克隆本仓库或在本仓库目录中启动 Harness。安装器会把完整插件分发复制到自己的缓存；后续会话由 Harness 原生发现 Skills，并从该安装副本读取政策文件和确定性脚本。

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

安装或更新后使用新会话。详细接受条件见 [`docs/INSTALL-CODEX.md`](docs/INSTALL-CODEX.md) 与 [`docs/INSTALL-CLAUDE-CODE.md`](docs/INSTALL-CLAUDE-CODE.md)。

## Fail-Closed Rules

- 关键数据缺失、过期或冲突：`DATA INCOMPLETE`；
- Broker capability 不可用：如实声明，不猜测、不倒推；
- 月度入金 `F` 未知：不得默认为零；
- Open Orders 未明确为 clear：阻断月度候选；
- NAV、现金与持仓无法对账：停止计算；
- 候选、IC Verdict、历史批准或其他 Agent 输出：均不自动形成执行权限；
- Broker 结果不确定：`EXECUTION UNKNOWN`，禁止静默重试。

## Validation

本地和 CI 使用同一个入口：

```bash
bash tests/run-all.sh
```

该套件验证 Skill、Broker Runtime、账户对账、DecisionPacket、Execution Runtime、月度输入门、Eval harness 完整性、产品契约和隐私边界。

非 LLM 测试全绿不等于真实 Agent 行为合规。clean-session eval 尚未执行通过时，项目必须继续声明：

```text
Real Harness behavior: NOT YET VERIFIED
```

## Repository Map

- `plugins/investment-os/`：唯一可安装运行时产品
- `plugins/investment-os/skills/using-investment-os/references/`：四份合并规则文件（`00-constitution`、`01-operating-manual`、`02-data-contract`、`03-journal`）与产品契约的唯一真源
- `plugins/investment-os/skills/*/scripts/`：由各 Skill 拥有的确定性运行时
- `AGENTS.md`、`CLAUDE.md`：仅用于源码仓库开发的薄入口
- `scripts/`：源码级发布、治理和一致性检查器，不进入插件
- `tests/`：非 LLM 与 harness 完整性测试
- `evals/`：synthetic 行为压力场景
- `Decision-Log.md`：长期治理决定
- `BUGLOG.md`：缺陷、根因与防复发
- `Research/`：未生效研究

## Authority and Versioning

具体投资规则发生冲突时，按插件 references 中的编号顺序执行：`00-constitution.md` → `01-operating-manual.md` → `03-journal.md`；唯一沿用旧制的例外是宪法转型计划部分与操作手册冲突时仍以操作手册为准。`02-data-contract.md` 约束数据可用性，不创造投资参数。

聊天记录、旧报告、旧 Skill 摘要和 `Research/` 不具有现行规则效力。现行政策以默认分支 HEAD 为准。

`plugins/investment-os/.plugin-version` 只表示 Skill / Plugin 分发 SemVer，不表示投资政策版本。

本仓库用于长期投资决策纪律与工具研究，不构成面向他人的投资建议，也不保证投资收益。


## Data Maintenance Boundary

仓库不维护重复的中央证券数据库。行情、ETF 成分、issuer 和行业分类按已登记来源在运行时读取；只有规则、契约、公开证据或工具变化才提交。**普通数据变化不更新项目**。
