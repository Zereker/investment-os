# Investment OS — Product Contract

本文件合并原 Project Contract 与 Production Contract：定义产品目标、隐私边界、系统行为原则，以及 Production 的运行、控制和执行边界。它不创造投资参数；现行参数始终来自 `00-constitution.md`、`01-operating-manual.md` 与 `03-journal.md`——以默认分支 HEAD 为规范来源，会话则读取本次安装所分发的这些文件。

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

Production 必须使用以下分层，不允许由自然语言回答替代确定性运行时：

```text
Broker Adapter
→ broker-runtime
→ account reconciliation
→ deterministic decision engine / DecisionPacket
→ behavioral and procedural controls
→ presentation
→ execution-runtime（仅在存在单次授权时）
```

职责边界：

- Broker Adapter：把具体 Broker 工具映射成规范化输入；它是适配器，不是 Investment OS 的接口本身；
- `broker-runtime`：验证来源、能力、新鲜度、币种、账户合计和任务所需数据；自己验证数据，不信任调用者自报 PASS；
- `account_reconciliation.py`：独立核对 NAV、现金和持仓市值；
- `DecisionPacket`：保存机器权威的事实、计算、阻塞项、结论和执行权限；
- renderer 或 LLM：只解释和格式化，不得重算或改写机器权威字段；
- `execution-runtime`：验证单次授权、能力、提交、权威回读和终态。

LLM 位于 orchestration 与 presentation 层。它可以调用工具、解释和格式化，但不能替代数据验证、资金计算、权限判断、执行状态机或 read-back verification。

任一必要层缺失、过期、冲突或无法验证，相关任务必须失败关闭。

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

## 7. 权威与优先级

投资规则发生冲突时，依次适用：

1. `00-constitution.md`（宪法：IPS、投资宇宙、目标配置、转型计划、倾斜框架与登记表）
2. `01-operating-manual.md`（操作手册：日/周/月/季/年流程、日报契约、部署框架、状态重建、IC 清单）
3. `03-journal.md`（日志与经验）

`00-constitution.md` 内部冲突按其部分顺序解决；唯一例外沿用旧制：其转型计划部分与 `01-operating-manual.md` 冲突时，以操作手册为准（原 `02-*` 优先于 `03-*` 的顺序不因本次合并改变）。`02-data-contract.md` 约束数据来源、质量与口径，不创造投资参数；数据文件不得自行增加或改变交易规则。

聊天记录、旧报告、截图、人工贴数和 [source repository research](https://github.com/Zereker/investment-os/tree/master/Research/) 不具有 Production 规则效力。本契约定义产品与运行边界，`agent-execution-contract.md` 定义 Agent 运行程序；二者不得覆盖上述投资规则。

现行政策以默认分支 HEAD 为准——这是规范来源。会话实际读取的是**本次安装所分发的政策文件**，不在运行时另行获取更新；已发布分发的 source commit 由对应 Git tag 在发版时记录。`.plugin-version` 仅用于 Skill / Plugin 分发 SemVer，不表示投资政策版本。会话报告自己运行的分发版本，不得报告一个自行解析出来的 commit，也不得声称已确认该分发是最新的。

## 8. Daily Product 与每日巡检

主要产品是 `Investment Daily Report`，规范见 `01-operating-manual.md` 日报契约部分。每日巡检不是每日交易；`HOLD` 是完整且成功的结果。

每日巡检必须从受信任 Broker Adapter 获取并验证 `01-operating-manual.md` 每日复盘部分列出的全部端点（含 Account Summary、Balances、Positions、Open Orders、市场输入与警报状态、现金活动，及 Adapter 提供时的 Cash Transactions），完成账户对账、融资与负现金检查、异常持仓分类、订单冲突检查、配置与回撤状态计算，并先生成机器权威 `DecisionPacket`，再由确定性 renderer 或 LLM 形成日报。展示层不得改变结论、金额、阻塞项或执行权限。

关键数据缺失时输出 `DATA INCOMPLETE`，停止新的买卖候选。不得用历史报告、旧快照、截图或人工数字替代实时状态。

## 9. 月度执行

月度流程必须在任何部署公式之前通过 `01-operating-manual.md` 月度流程部分的全部前置闸门（能力、新鲜度、物理对账、Open Orders 明确为 `clear`、权威 `F`、回撤状态、政策一致）。`F` 未知或其数据能力不可用、订单状态为 `unknown` 或 `conflicting`、对账超出容差、回撤输入无法验证，均为 `DATA INCOMPLETE`。

缺失 `F` 时不得默认为零；没有入金的月份也必须由权威来源明确确认零。若当前 Adapter 不支持 `cash_transactions`，必须如实声明能力缺口，不得倒推或估算。

## 10. 候选、批准与执行权限

`HOLD`、`WAIT`、`BUY CANDIDATE`、`SELL CANDIDATE`、IC Verdict 或历史批准均不自动形成 Broker 执行权限。

Agent 可以执行当前 Adapter 支持的 Broker 操作，但必须同时满足：

1. 当前会话存在账户所有者明确授权；
2. 授权绑定一个完整、规范化的单次操作摘要（operation digest）；
3. 所需 Broker capability 可用；
4. 数据门、政策门和行为控制门全部通过；
5. 只提交一次，不进行静默重试；
6. 执行后读取权威 Broker 状态；
7. read-back 与授权操作逐项匹配；
8. 结果形成临时执行回执并向所有者报告；
9. 授权不跨操作、不跨会话、不从其他 Agent 或既往批准继承。

满足全部条件且 read-back 逐项一致时，终态为 `COMPLETED`。不满足任一条件时，终态必须是 `NOT EXECUTED`、`EXECUTION UNKNOWN`、`VERIFICATION FAILED` 或 `DATA INCOMPLETE`，不得声称成功。

## 11. Investment Committee

非例行资金建议、卖出、换仓、规则例外、提高自主倾斜或偏离已发布公式的操作，必须经过仓库定义的完整 IC 流程。

IC 批准只表示该候选可以进入执行授权阶段。它不是 Broker 授权，也不能替代当前会话中针对具体操作的所有者明确授权。

## 12. 研究与规则变更

执行过程中不得临时引入指标、改变阈值或更换口径。新策略语义必须进入 [source repository research](https://github.com/Zereker/investment-os/tree/master/Research/)，经过独立研究、书面提案、所有者批准和 Production 文档同步后方可生效。

## 13. Privacy Boundary

不得进入公开仓库：券商账户标识、凭证、真实 NAV、现金、持仓、订单、成交、入金、费用、税务、收益、授权状态、执行回执和任何可推导个人资产的信息。

允许进入仓库：政策与流程、数学公式、字段定义、synthetic 示例、不含个人状态的研究证据和经过隐私门检查的治理记录。

真实账户数据、订单、成交、执行回执和授权状态仅存在于受信任运行时或当前私有会话。`Decision-Log.md` 只记录长期治理事实和规则理由，不记录账户号、订单号、警报 ID、真实金额、股数或其他私人运行时状态。

## 14. Change Test

任何功能或 PR 必须回答：

1. 是否提高长期决策质量？
2. 是否遵守知识与状态分离？
3. 是否使结论或执行更可重复、更可解释或更安全？
4. 是否避免引入未经批准的新策略语义？

任一答案为否，默认不进入 Production。

## 15. 验证要求

所有 PR 必须通过 canonical suite：

```bash
bash tests/run-all.sh
```

非 LLM 测试通过不等于真实 Agent 行为已验证。只要 clean-session behavior eval 尚未通过，仓库必须继续如实声明：

```text
Real Harness behavior: NOT YET VERIFIED
```

## 16. 倾斜路径术语

- **回补至目标**：不提高已批准风险预算，只在现行规则允许范围内恢复被市场漂移压低的已批准权重；
- **提高倾斜**：推进或扩大风险预算，必须进入完整 IC，不能伪装成例行回补。

## 17. 数据维护边界

仓库不维护行情、ETF成分、issuer或GICS中央数据库。普通巡检不写仓库；运行时数据和普通市场变化只存在于当前会话。只有规则、契约、公开证据或工具发生变化时才提交。
