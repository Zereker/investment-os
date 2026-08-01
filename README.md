# Investment OS v5.0

一套开源的长期投资决策操作系统。它帮助投资者持续观察市场与组合、理解变化、依据预先批准的规则形成一致且可审计的决策，并明确下一观察条件。

> Investment OS 的目标，是让正确的决策成为最容易做出的决策。

系统优化的是**决策质量**，不是预测准确率，也不是交易频率。完整产品定义见 [PROJECT.md](PROJECT.md)。

## 系统每天做什么

Investment OS 遵循唯一决策循环：

```text
Observe → Understand → Decide → Monitor → Repeat
```

每日产品是 [Investment Daily Report](02-Operating-System/Daily-Report-Contract.md)，固定回答：

1. 今天发生了什么？
2. 当前组合状态如何？
3. 这些变化在现行策略下意味着什么？
4. 哪些动作获得规则授权，哪些没有？
5. 今天需要注意什么？
6. 下一件值得观察的事情是什么？

每日巡检不是每日交易。`HOLD` 是正常且完整的产品结果。

## 隐私边界

> **仓库保存规则，不保存个人组合。**

公开仓库只保存政策、流程、公式、状态机、数据契约、测试和不含个人状态的研究证据。

真实账户状态只存在于受信任的运行时或当前私有会话，包括但不限于：账户标识、NAV、现金金额、持仓市值、股数、成本、订单、成交、入金、收益、税务和任何可反推出个人资产的信息。这些内容不得进入提交、Issue、PR、日志、fixture、截图或快照。

测试只能使用明确标记、不可反推真实账户的 synthetic 数据。隐私与产品契约由 `scripts/check_product_contract.py` 在 CI 中检查。

## 当前策略架构

v5.0 是产品化重构，不改变 v4.6 已发布的投资参数。

- 现金：15%（常态区间 12%–18%；严重回撤时按回撤部署条款分档下调下限）
- QQQM：28% 战略成长引擎（允许区间 25%–31%）
- SPYM + SOXX实际持仓 + SOXX阶段储备：57%组合袖套
- SOXX：唯一自主板块倾斜（半导体行业 beta，不是 alpha），永久硬上限 6%，当前执行上限 3%
- 其他板块倾斜新增授权：0%
- SPYM：目标为 `57%−A_basis`
- 每月固定新增投入：数额不入库，运行时从 IBKR 读取实际到账

其中 `A_basis=max(A_actual,A_stage)`，`A_stage` 固定为 6%，`U=max(A_stage-A_actual,0)`。未完成的 SOXX 额度作为现金中的用途标签保留，不先投入 SPYM。风险护栏和数据门优先于执行档目标，QQQM 28% 保持不变。

SOXX 买入分为两条路径：

- **回补至目标**：`A_execution_cap` 不动，走月度例行路径，资金只来自 `U`；
- **提高倾斜**：推进执行档，必须通过完整 Investment Committee。

SPYM 回撤部署采用四档：≥10% / 15% / 20% / 25%，分别释放 1.5 / 3 / 4.5 / 6pp of NAV；25% 处把普通现金投出至 `0+U`，之后不再解锁，也不借款。

## 生产原则

- 规则优先于情绪，策略优先于预测。
- 真实账户数据必须从 IBKR 实时读取，不得用历史快照冒充今日状态。
- IBKR Positions 是当前持仓数量的权威来源。
- 关键数据缺失、过期或冲突时输出 `DATA INCOMPLETE`，停止新的买卖候选。
- 非例行真实资金建议必须通过 Trade Gate 与 Investment Committee Packet。
- Production 与 Research 严格隔离；研究内容未经批准不得影响交易。
- 系统永不下单，最终交易由账户所有者在 IBKR 中亲自确认。
- 相同的有效输入和相同的生产规则，应得到相同、可解释、可复核的结论。

## 如何使用

> AI 执行者从 [CLAUDE.md](CLAUDE.md) 开始；产品目标与隐私边界先读 [PROJECT.md](PROJECT.md)。

1. 读取 [产品契约](PROJECT.md)，确认任务属于系统职责且不越过隐私边界。
2. 读取 [生产契约](PRODUCTION.md)。
3. 读取 [投资政策声明](00-IPS/Investment-Policy-Statement.md) 和 [目标配置](01-Constitution/Target-Allocation.md)。
4. 每日按 [Daily Review Workflow](02-Operating-System/Daily-Review.md) 取得实时数据，并按 [Daily Report Contract](02-Operating-System/Daily-Report-Contract.md) 输出日报。
5. 每周按 [Weekly Review Workflow](02-Operating-System/Weekly-Review.md) 汇总运行质量与待处理项。
6. 每月按 [Monthly Workflow](02-Operating-System/Monthly-Workflow.md) 执行固定投入、战略现金迁移与达档的回撤部署。
7. 超出月度基线的部署只有回撤档位一条机械路径；主动加速属于规则例外，须进入完整 IC。
8. 任何非例行真实资金候选先完成 [Investment Committee Packet](02-Operating-System/Decision-Checklist.md)。
9. 每季度完成 [穿透手工核查](08-Data/LOOKTHROUGH_CHECK.md) 并审核倾斜与集中度。
10. 所有新假设进入 [Research Sandbox](Research/README.md)，不得直接影响 Production。
11. 每年审核系统规则、Policy Benchmark、影子基准和系统自身的决策质量。

## 仓库结构

- `PROJECT.md`：项目使命、产品边界、决策循环与隐私契约
- `PRODUCTION.md`：生产系统入口、规则冻结、运行流程和交易闸门
- `BUGLOG.md`：可靠性缺陷、根因和防复发措施
- `Decision-Log.md`：改变系统方向或产生长期影响的决定
- `Research/`：未生效的研究、假设和版本提案
- `00-IPS/`：使命、期限、风险与治理
- `01-Constitution/`：不可随意改变的目标配置和边界
- `02-Operating-System/`：日报契约、每日、周度、月度、季度、年度流程及交易闸门
- `03-Transition/`：转型计划
- `04-Alpha/`：板块倾斜规则、生命周期和当前登记
- `05-Journal/`：重大投资决策记录；不得保存个人账户状态
- `06-Lessons/`：长期有效的经验
- `07-Releases/`：版本发布说明
- `08-Data/`：Production 数据契约、质量闸门和不含个人状态的公共核查资料
- `scripts/`：政策、产品与隐私检查，以及规则计算工具
- `CLAUDE.md`：AI 执行手册

## 权威顺序

`PROJECT.md` 定义产品目标、隐私边界和系统行为原则，不创造资产配置参数。

具体投资规则发生冲突时：投资政策声明 → Constitution → Operating System → Transition Plan → Journal。`PRODUCTION.md` 负责执行契约和入口，不覆盖以上策略优先级。聊天记录和 Research 不具有现行规则效力。

本仓库用于长期投资决策纪律与工具研究，不构成面向他人的投资建议，不保证投资收益。
