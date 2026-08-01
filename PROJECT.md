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
- 由人类账户所有者最终确认交易的辅助系统。

Investment OS 不是：

- 市场预测器；
- 自动交易机器人；
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

“候选”只表示规则授权进入人工确认，不是订单，也不保证执行。

### Monitor

每次输出必须给出下一观察条件，包括阈值、待补数据、待完成订单、月度资金到账或下一例行审核日期。

## 5. Core Principles

### P1 — Rule over Emotion

规则优先于情绪。临时恐惧、兴奋、新闻和价格叙事不得绕过生产规则。

### P2 — Policy over Prediction

策略优先于预测。系统不以预测未来为核心能力，不因无法预测而停止执行长期规则。

### P3 — Repository Stores Knowledge, Never Portfolio

仓库保存投资知识和决策规则，永远不保存个人组合。

### P4 — Separate Knowledge from State

知识属于 Git；状态只存在于受信任的运行时。

- 知识：政策、目标、公式、流程、状态机、数据契约、测试和公开研究证据。
- 状态：账户编号、净值、金额、持仓数量、成本、成交、订单、收益、入金、税务和任何可反推出个人资产的信息。

### P5 — Runtime Data Is Ephemeral

运行时账户数据仅用于当次计算和报告，不得写回公开仓库，不得进入提交、Issue、PR、日志、fixture、截图或快照。

公开仓库可保存匿名、合成且不可反推出真实账户的测试数据，但必须明确标记为 synthetic。

### P6 — Fail Closed

关键数据缺失、过期或冲突时，结论必须是 `DATA INCOMPLETE`，并停止新的买卖候选。不得用旧快照、估算值或记忆填补。

### P7 — Human Executes Trades

系统不下单，不保存券商凭证，不生成绕过人工判断的自动执行链。最终订单由账户所有者在券商端亲自确认。

### P8 — Every Decision Is Explainable

每个结论必须同时给出事实依据、适用规则、阻止条件和下一观察点。

### P9 — Reproducible by Construction

公式应实现为纯计算，连接器、状态读取、决策计算和报告渲染相互分离。同样输入不得因模型偏好不同而改变结果。

### P10 — Open by Default, Private by Design

规则和工具尽可能开源；个人数据从架构上排除，而不是依靠提交者事后记得删除。

## 6. Daily Product

系统的主要产品是 `Investment Daily Report`，规范见 `02-Operating-System/Daily-Report-Contract.md`。

每日巡检不是每日交易。无动作时，`HOLD` 是完整且成功的产品结果。

日报必须清楚分开：

- **Fact**：直接读取或计算的事实；
- **Interpretation**：事实在现行规则下的含义；
- **Decision**：规则授权的结论；
- **Monitor**：下一观察条件。

## 7. Privacy Boundary

以下内容不得进入公开仓库，无论是否经过四舍五入、截屏、日志或示例包装：

- 券商账户标识、用户名、令牌、Cookie、API Key 和凭证；
- 真实 NAV、现金金额、持仓市值、股数、成本和成交价格；
- 真实订单、成交、入金、分红、费用、税务和收益记录；
- 能通过多个字段组合推导个人资产规模的百分比与金额组合；
- 包含上述信息的终端输出、报告、截图、fixture、缓存和调试文件。

允许进入仓库的内容：

- 不绑定真实账户的政策权重与阈值；
- 数学公式、字段定义和流程；
- 明确标注的 synthetic 示例；
- 不含个人状态的公共市场研究证据；
- 经过隐私门检查的发布说明和决策记录。

任何不确定内容默认视为私有，不提交。

## 8. Change Test

任何功能或 PR 必须先回答：

1. 它是否提高长期投资决策质量？
2. 它是否遵守知识与状态分离？
3. 它是否让结论更可重复、更可解释或更安全？
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

当产品实现与本文件冲突时，必须修复实现；当具体投资参数与本文件无关时，仍由上述政策层级裁决。
