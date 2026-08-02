# Investment OS — Product Contract

## 1. Mission

Investment OS 是一套开源的长期投资决策操作系统。它帮助投资者持续观察市场与组合、理解变化、依据预先批准的规则形成一致且可审计的决策，并明确下一观察条件。

系统优化的是**决策质量**，不是预测准确率，也不是交易频率。

> Investment OS should make the right decision the easiest decision.
>
> Investment OS 的目标，是让正确的决策成为最容易做出的决策。

## 2. Product Definition

Investment OS 是：

- 长期投资决策助手；
- 规则、流程、数学模型和风险边界的版本化知识库；
- 把运行时账户状态转化为可解释结构化结论的确定性决策系统；
- 在账户所有者明确授权下执行并验证单次 Broker 操作的受控运行时；
- 可在 Claude Code、Codex 和其他 Harness 中分发的可组合 Skill 系统。

Investment OS 不是：

- 市场预测器；
- 无人值守自动交易机器人；
- 每日制造交易信号的工具；
- 收益保证或面向他人的个性化投资建议；
- 个人账户数据库。

## 3. North Star

每次巡检必须回答：

1. 今天发生了什么？
2. 当前组合状态如何？
3. 这些变化在现行策略下意味着什么？
4. 哪些动作获得规则授权，哪些没有？
5. 今天需要注意什么？
6. 下一件值得观察的事情是什么？

> 相同的有效输入和相同的生产规则，应得到相同、可解释、可复核的结论。

## 4. Decision Loop

```text
Observe → Understand → Decide → Monitor → Repeat
```

- **Observe**：只读取可验证事实；
- **Understand**：由确定性运行时把事实映射到现行规则；
- **Decide**：输出受控结论与阻塞项；
- **Monitor**：给出下一观察条件；
- **Execute**：仅在存在单次所有者授权时，经 Execution Runtime 执行并验证。

## 5. Runtime Architecture

```text
Broker Adapter
→ Broker Runtime
→ Account Reconciliation
→ Decision Engine / DecisionPacket
→ Behavioral Controls
→ Presentation
→ Execution Runtime（仅有授权时）
```

LLM 位于 orchestration 与 presentation 层。它可以调用工具、解释和格式化，但不能替代数据验证、资金计算、权限判断、执行状态机或 read-back verification。

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

### P6 — Fail Closed
关键数据、能力、授权或验证缺失时，停止新的候选或执行。

### P7 — Owner-Authorized Broker Execution
任何 Broker 写操作必须绑定当前会话中的一个完整单次操作，并在提交后读取权威状态验证结果。禁止泛化授权、跨操作继承、跨会话继承、静默重试和无人值守执行链。

### P8 — Every Decision Is Explainable
每个结论必须给出事实、规则、阻塞项和下一观察条件。

### P9 — Reproducible by Construction
连接器、状态验证、计算、决策、展示和执行相互分离。

### P10 — Open by Default, Private by Design
规则和工具尽可能开源；个人数据从架构上排除。

## 7. Daily Product

主要产品是 `Investment Daily Report`，规范见 `02-daily-report-contract.md`。每日巡检不是每日交易；`HOLD` 是完整且成功的结果。

Daily 必须先生成机器权威 `DecisionPacket`，再由确定性 renderer 或 LLM 形成报告。展示层不得改变结论、金额、阻塞项或执行权限。

## 8. Privacy Boundary

不得进入公开仓库：券商账户标识、凭证、真实 NAV、现金、持仓、订单、成交、入金、费用、税务、收益、授权状态、执行回执和任何可推导个人资产的信息。

允许进入仓库：政策与流程、数学公式、字段定义、synthetic 示例、不含个人状态的研究证据和经过隐私门检查的治理记录。

## 9. Change Test

任何功能或 PR 必须回答：

1. 是否提高长期决策质量？
2. 是否遵守知识与状态分离？
3. 是否使结论或执行更可重复、更可解释或更安全？
4. 是否避免引入未经批准的新策略语义？

任一答案为否，默认不进入 Production。

## 10. Authority and Versioning

本文件定义产品目标、隐私边界和系统行为原则，不创造具体资产配置或交易参数。

投资规则权威顺序：

1. `00-*` IPS reference
2. `01-*` Constitution references
3. `02-*` Operating System references
4. `03-*` Transition reference
5. `05-*` Journal reference

现行政策以默认分支 HEAD 为准——这是规范来源。会话实际读取的是**本次安装所分发的政策文件**，不在运行时另行获取更新；已发布分发的 source commit 由对应 Git tag 在发版时记录。`.plugin-version` 仅用于 Skill / Plugin 分发 SemVer，不表示投资政策版本。
