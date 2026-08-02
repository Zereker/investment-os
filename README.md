# Investment OS v5.0

<!-- Policy compatibility anchor: # Investment OS v4.6. v5.0 changes the product contract, not the v4.6 strategy parameters. -->

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
- 仓库不维护重复的中央证券数据库；公共市场数据按已登记来源在运行时读取。
- 普通数据变化不更新项目；只有规则、契约、公开证据或工具发生变化时才提交。

## Agent Skills

Investment OS 以一个跨 Harness 插件分发多个可组合 Skills，而不是把全部能力塞进一个大 Skill：

- `using-investment-os`：统一入口与任务路由；
- `reconstructing-portfolio-state`：重建实时账户与市场状态；
- `enforcing-behavioral-controls`：执行多 Agent、订单与流程拦截；
- `running-daily-review`：生成每日决策产品；
- `running-monthly-review`：执行月度资金审查；
- `evaluating-transaction-candidates`：评估具体真实资金候选；
- `routing-investment-research`：将新标的和新规则隔离到 Research；
- `auditing-investment-os`：审计政策、实现、隐私、CI 和运行准备度。

共享 Skill 源位于 [`skills/`](skills/README.md)，Claude Code 与 Codex 通过各自的薄 manifest 分发。`tests/` 验证插件和确定性基础设施，`evals/` 定义 synthetic 压力场景验证 Agent 的实际行为。

## 如何使用

> AI 执行者从 [AGENTS.md](AGENTS.md) 和 `using-investment-os` 开始；产品目标与隐私边界先读 [PROJECT.md](PROJECT.md)。

1. 读取产品契约与生产契约。
2. 从当前默认分支 HEAD 选择相关 Skills。
3. 每次从 IBKR 重建实时账户状态。
4. 调用现行确定性脚本执行计算和一致性检查。
5. 按当前 Daily、Monthly、Research 或 Audit 工作流输出。
6. 数据或控制条件不足时失败关闭。
7. 最终交易始终由账户所有者确认。

## 仓库结构

- `PROJECT.md`：项目使命、产品边界、决策循环与隐私契约
- `PRODUCTION.md`：生产系统入口、规则冻结、运行流程和交易闸门
- `AGENTS.md`：跨 Agent 执行与授权契约
- `skills/`：可组合、平台无关的 Agent Skills
- `.claude-plugin/`、`.codex-plugin/`：跨 Harness 分发元数据
- `tests/`：非 LLM 插件与基础设施测试
- `evals/`：synthetic Agent 行为压力场景
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
- `scripts/`：政策、产品、Skill 与隐私检查，以及规则计算工具

## 权威顺序

`PROJECT.md` 定义产品目标、隐私边界和系统行为原则，不创造资产配置参数。

具体投资规则发生冲突时：投资政策声明 → Constitution → Operating System → Transition Plan → Journal。`PRODUCTION.md` 负责执行契约和入口，不覆盖以上策略优先级。聊天记录、旧 Skill 摘要和 Research 不具有现行规则效力。

本仓库用于长期投资决策纪律与工具研究，不构成面向他人的投资建议，不保证投资收益。
