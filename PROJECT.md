# Investment OS v5.0 — Product Contract

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
- 把运行时账户状态转化为可解释结论的确定性决策系统；
- 在账户所有者明确授权下执行并验证单次 Broker 操作的受控运行时。

Investment OS 不是：

- 市场预测器；
- 无人值守自动交易机器人；
- 每日制造交易信号的工具；
- 收益保证或面向他人的个性化投资建议；
- 个人账户数据库。

## 3. North Star

每次巡检必须回答六个问题：

1. 今天发生了什么？
2. 当前组合状态如何？
3. 这些变化在现行策略下意味着什么？
4. 哪些动作获得规则授权，哪些没有？
5. 今天需要注意什么？
6. 下一件值得观察的事情是什么？

系统的北极星不是“今天是否交易”，而是：

> 相同的有效输入和相同的生产规则，应得到相同、可解释、可复核的结论。

## 4. Decision Loop

所有日常产品遵循唯一循环：

```text
Observe → Understand → Decide → Monitor → Repeat
```

### Observe

只陈述可验证事实：账户健康、市场价格、持仓、现金、订单、损益、权重和回撤。

### Understand

把事实映射到现行策略：目标缺口、超配、回撤档位、风险边界、数据质量和订单冲突。

### Decide

只使用已发布规则输出受控词表：

- `HOLD`
- `WAIT`
- `BUY CANDIDATE`
- `SELL CANDIDATE`
- `REVIEW`
- `REJECT`
- `DATA INCOMPLETE`

“候选”只表示规则授权进入账户所有者确认，不自动形成订单。

### Monitor

每次输出必须给出下一观察条件，包括阈值、待补数据、待完成订单、月度资金到账或下一例行审核日期。

## 5. Core Principles

### P1 — Rule over Emotion
规则优先于情绪。

### P2 — Policy over Prediction
策略优先于预测。

### P3 — Repository Stores Knowledge, Never Portfolio
仓库保存投资知识和决策规则，永远不保存个人组合。

### P4 — Separate Knowledge from State
知识属于 Git；状态只存在于受信任的运行时。

### P5 — Runtime Data Is Ephemeral
运行时账户数据仅用于当次计算、报告和执行验证，不得写回公开仓库。

### P6 — Fail Closed
关键数据缺失、过期或冲突时，结论必须是 `DATA INCOMPLETE`，并停止新的买卖候选或执行。

### P7 — Owner-Authorized Broker Execution
系统可以通过 Broker 执行任何当前适配器支持的操作，但必须满足：账户所有者在当前会话对一个完整、规范化的单次操作明确授权；授权绑定该操作摘要；执行后必须读取权威 Broker 状态并验证结果；不允许泛化授权、跨操作继承、跨会话继承、静默重试或无人值守执行链。

### P8 — Every Decision Is Explainable
每个结论必须同时给出事实依据、适用规则、阻止条件和下一观察点。

### P9 — Reproducible by Construction
公式应实现为纯计算，连接器、状态读取、决策计算、执行和报告渲染相互分离。

### P10 — Open by Default, Private by Design
规则和工具尽可能开源；个人数据从架构上排除。

## 6. Daily Product

系统的主要产品是 `Investment Daily Report`，规范见 `02-Operating-System/Daily-Report-Contract.md`。每日巡检不是每日交易。无动作时，`HOLD` 是完整且成功的产品结果。

## 7. Privacy Boundary

以下内容不得进入公开仓库：券商账户标识、凭证、真实 NAV、现金、持仓、订单、成交、入金、费用、税务、收益、执行回执以及可推导个人资产的信息。

允许进入仓库的内容包括：政策权重与阈值、数学公式、字段定义、流程、明确标注的 synthetic 示例、不含个人状态的研究证据，以及经过隐私门检查的治理记录。

## 8. Change Test

任何功能或 PR 必须先回答：

1. 它是否提高长期投资决策质量？
2. 它是否遵守知识与状态分离？
3. 它是否让结论或执行更可重复、更可解释或更安全？
4. 它是否避免引入未经批准的新策略语义？

任一答案为否，默认不进入 Production。

## 9. Authority

本文件定义项目产品目标、隐私边界和系统行为原则，不创造具体资产配置或交易参数。

具体投资规则的权威顺序仍为：

1. `00-IPS/`
2. `01-Constitution/`
3. `02-Operating-System/`
4. `03-Transition/`
5. `05-Journal/`
