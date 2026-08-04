# Investment OS — Product Contract

本文件定义产品目标、隐私边界、系统行为原则，以及 Production 的运行、控制和执行边界。它不创造投资参数；现行参数始终来自 `00-constitution.md`、`01-operating-manual.md` 与 `03-journal.md`。

## 1. Mission

Investment OS 是一套开源的长期投资决策操作系统。它帮助投资者持续观察市场与组合、理解变化、依据预先批准的规则形成一致且可审计的决策，并明确下一观察条件。

系统优化的是**决策质量**，不是预测准确率，也不是交易频率。

> Investment OS should make the right decision the easiest decision.

## 2. Product Definition

Investment OS 是：

- 长期投资决策助手；
- 规则、流程、数学模型和风险边界的版本化知识库；
- 由 LLM 综合事实、政策和研究形成投资判断的 Agent 系统；
- 验证账户事实、数学计算和执行安全的受控运行时；
- 可在 Claude Code、Codex 和其他 Harness 中分发的可组合 Skill 系统。

Investment OS 不是市场预测器、无人值守自动交易机器人、每日制造交易信号的工具、收益保证或个人账户数据库。

## 3. North Star

每次巡检必须回答：

1. 今天发生了什么？
2. 当前组合状态如何？
3. 这些变化在现行策略下意味着什么？
4. 当前建议是什么，哪些动作被阻断？
5. 今天需要注意什么？
6. 下一件值得观察的事情是什么？

系统追求结论可解释、证据可追溯、执行可验证；不要求复杂投资判断在所有运行中机械地产生完全相同的文字或结论。

## 4. Decision Loop

```text
Observe → Understand → Decide → Monitor → Repeat
```

- **Observe**：读取并验证事实；
- **Understand**：LLM 结合事实、政策和研究理解变化；
- **Decide**：LLM 形成结论、理由、阻塞项与下一观察条件；
- **Monitor**：跟踪使结论失效或需要复核的条件；
- **Execute**：仅在存在单次所有者授权时，经 Execution Runtime 执行并验证。

## 5. Runtime Architecture

```text
Broker / Market Tools
→ verified facts and calculations
→ LLM analysis and decision
→ behavioral and procedural controls
→ presentation
→ execution-runtime（仅在存在单次授权时）
```

职责边界：

- Broker Adapter 与 `broker-runtime` 验证来源、能力、新鲜度、币种和任务所需数据；
- `account_reconciliation.py` 独立核对 NAV、现金和持仓市值；
- 确定性代码负责可机械验证的事实、计算、授权、提交和 read-back verification；
- LLM 负责选择证据、理解上下文、比较方案、形成结论并解释不确定性；
- `DecisionPacket` 清楚分开已验证事实、LLM 判断、阻塞项和执行权限；它不是必须覆盖所有投资推理的通用大 schema；
- `execution-runtime` 验证单次授权、能力、提交、权威回读和终态。

原则：**代码验证事实并保护执行，LLM 负责投资判断。** 不为每个分析细节新增规则、字段、状态机或 Skill；只有真实失败证明必要时才增加结构。

## 6. Core Principles

### P1 — Rule over Emotion
规则优先于情绪。

### P2 — Policy over Prediction
策略优先于预测。

### P3 — Repository Stores Knowledge, Never Portfolio
仓库保存知识和规则，永远不保存个人组合。

### P4 — Separate Knowledge from State
知识属于 Git；状态只存在于受信任运行时。

### P5 — Runtime Data Is Ephemeral
运行时数据、授权和执行回执不进入公开仓库。

### P6 — Fail Closed on Facts and Execution
关键账户事实、能力、授权或执行验证缺失时，停止相关候选或执行；分析本身可继续明确讨论不确定性。

### P7 — Owner-Authorized Broker Execution
任何 Broker 写操作必须绑定当前会话中的一个完整单次操作，并在提交后读取权威状态验证结果。禁止泛化授权、跨操作继承、跨会话继承、静默重试和无人值守执行链。

### P8 — Every Decision Is Explainable
每个结论必须给出主要事实、理由、重要不确定性、阻塞项和下一观察条件。

### P9 — Simple by Default
优先复用现有 Skill 和契约。除非真实缺陷无法用现有结构解决，不新增层级、分类、状态或文件。

### P10 — Open by Default, Private by Design
规则和工具尽可能开源；个人数据从架构上排除。

## 7. 权威与优先级

投资规则发生冲突时，依次适用：

1. `00-constitution.md`
2. `01-operating-manual.md`
3. `03-journal.md`

`02-data-contract.md` 约束数据来源、质量与口径，不创造投资参数。聊天记录、旧报告、截图、人工贴数和 `Research/` 不具有 Production 规则效力。

现行政策以默认分支 HEAD 为规范来源；已安装会话读取本次分发的不可变快照，不在运行时自行更新。

## 8. Daily Product 与每日巡检

主要产品是 `Investment Daily Report`。每日巡检不是每日交易；`HOLD` 是完整且成功的结果。

每日巡检必须从受信任 Broker Adapter 获取并验证操作手册要求的账户与市场输入，完成账户对账、融资与负现金检查、异常持仓分类、订单冲突检查、配置与回撤计算，然后由 LLM 基于这些事实形成结构化结论。

LLM 不得伪造或静默改写已验证账户事实和数学结果，但可以自主解释其意义、比较方案并形成不同于固定公式的投资判断。

关键账户事实缺失时输出 `DATA INCOMPLETE`，阻止依赖这些事实的新买卖候选和执行。不得用历史报告、旧快照、截图或人工数字替代实时状态。

## 9. 月度执行

月度流程必须在部署前验证能力、新鲜度、账户对账、Open Orders、权威月度入金 `F`、回撤状态和政策一致性。

`F` 未知不得默认为零；订单状态不明、账户无法对账或关键回撤输入无法验证时，不得生成依赖这些输入的执行授权。

## 10. 候选、批准与执行权限

`HOLD`、`WAIT`、`BUY CANDIDATE`、`SELL CANDIDATE`、LLM 建议、IC Verdict 或历史批准均不自动形成 Broker 执行权限。

Agent 执行 Broker 操作必须同时满足：

1. 当前会话存在账户所有者明确授权；
2. 授权绑定一个完整、规范化的单次操作摘要；
3. 所需 Broker capability 与账户状态可验证；
4. 必要数据门、政策门和行为控制门通过；
5. 只提交一次，不进行静默重试；
6. 执行后读取权威 Broker 状态并与授权操作匹配；
7. 授权不跨操作、不跨会话、不从其他 Agent 或既往批准继承。

终态必须如实报告为 `COMPLETED`、`NOT EXECUTED`、`EXECUTION UNKNOWN`、`VERIFICATION FAILED` 或 `DATA INCOMPLETE`。

## 11. Investment Committee

非例行资金建议、卖出、换仓、规则例外、提高自主倾斜或偏离已发布公式的操作，必须经过现行规则要求的 IC 流程。

IC 结论不是 Broker 授权，不能替代当前会话中针对具体操作的所有者明确授权。

## 12. 研究与规则变更

LLM 可以在分析中引入相关指标、提出不同解释和挑战现行策略，但必须区分：

- 现行政策下的当前建议；
- 对现行政策本身的修改建议。

只有后者需要进入 `Research/`、书面提案、所有者批准和 Production 文档同步。一次分析不得静默改变长期政策。

## 13. Privacy Boundary

不得进入公开仓库：券商账户标识、凭证、真实 NAV、现金、持仓、订单、成交、入金、费用、税务、收益、授权状态、执行回执和任何可推导个人资产的信息。

允许进入仓库：政策与流程、数学公式、字段定义、synthetic 示例、不含个人状态的研究证据和经过隐私门检查的治理记录。

## 14. Change Test

任何功能或 PR 必须回答：

1. 是否提高长期决策质量？
2. 是否遵守知识与状态分离？
3. 是否使事实、结论或执行更可解释、更安全？
4. 是否可以通过修改现有结构解决，而不是新增结构？

不能明确证明必要的新层级、新分类、新状态、新契约或新 Skill，默认不进入 Production。

## 15. 验证要求

所有 PR 必须通过 canonical suite：

```bash
bash tests/run-all.sh
```

非 LLM 测试通过不等于真实 Agent 行为已验证。只要 clean-session behavior eval 尚未通过，仓库必须继续声明：

```text
Real Harness behavior: NOT YET VERIFIED
```

## 16. 倾斜路径术语

- **回补至目标**：不提高已批准风险预算，只在现行规则允许范围内恢复被市场漂移压低的已批准权重；
- **提高倾斜**：推进或扩大风险预算，必须进入完整 IC，不能伪装成例行回补。

## 17. 数据维护边界

仓库不维护行情、ETF 成分、issuer 或 GICS 中央数据库。普通巡检不写仓库；运行时数据和普通市场变化只存在于当前会话。只有规则、契约、公开证据或工具发生变化时才提交。
