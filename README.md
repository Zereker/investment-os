# Investment OS v3.5

一套以资产配置为中心、以低决策复杂度长期运行的个人投资系统。

> 使命：通过纪律性的资产配置和少量高确信投资，实现长期财富增长。

## 当前架构

- 现金：15%（允许区间 12%–18%）
- QQQM：28% 战略成长引擎（允许区间 25%–31%）
- SPYM + SOXX实际持仓 + SOXX阶段储备：57%组合袖套
- SOXX：唯一Alpha载体，长期硬上限与最终治理阶段15%，当前阶段6%
- 其他Alpha新增授权：0%
- SPYM：目标为`57%−A_basis`
- 每月新增投入：2,000 美元

其中`A_basis=max(A_actual,A_stage)`，`U=max(A_stage-A_actual,0)`；未完成的当前SOXX阶段额度作为现金中的用途标签保留，不先投入SPYM。风险护栏和数据门优先于阶段目标。QQQM 28%保持不变。

## v3.4.2数据门执行化

v3.4.2不改变v3.4策略或v3.4.1可靠性规则：SOXX长期硬上限15%、当前阶段6%、当前执行上限3%。本补丁以Look-through Evidence Bundle v1.4把穿透Data Gate执行化：管理人专用解析器覆盖真实字段，证券标识使用CUSIP / ISIN / SEDOL优先的带类型ID，发行人由CIK / LEI注册表统一；同时绑定账户快照、未失效Candidate、名义敞口和独立故障测试。验证通过只证明数据证据合格，不改变Registry、不创建或批准交易候选。SOXX仍为`Frozen — DATA GATE`，发布不产生交易。

当前穿透契约已升级为Bundle v1.5。日常巡检在运行时组合IBKR、基金管理人、身份源和权威分类源；仓库不维护重复的中央证券数据库。普通数据变化不更新项目，只有形成真实决策证据时才保存带来源、`as_of`和哈希的不可变Bundle。

## v3.5三只ETF估值执行

日常与月度估值范围固定为SPYM、QQQM、SOXX。Forward P/E相对各自历史百分位形成`CHEAP / FAIR / EXPENSIVE / VERY EXPENSIVE`基础等级，盈利增长、三个月预测修正和盈利收益率相对美国10年期国债的利差只做确认；SOXX另加周期保护。价格回撤只辅助执行时点，不再与估值相加。估值等级可减少或暂停新增资金，但估值贵本身不卖出，也不能绕过目标配置、SOXX Data Gate或人工下单边界。

v3.3的以下基础继续有效：

- v3.3用`SPYM=57%-A`修复机会预算数学；v3.4已由`A_basis`与阶段储备模型取代该执行公式。
- 将 Observation 定义为 Alpha 的生命周期状态，而不是第五个资产层。
- v3.3曾将SOXX置于Observation生命周期；v3.4已由Position Registry升级。
- 将历史超额现金的战略迁移与估值驱动的战术加速分开。
- Liquidity 只限制可执行金额，不再与价格、估值相加制造买入信号。
- 增加科技、半导体和单一发行人的穿透集中度护栏。
- 统一现行 Core 名称为 SPYM / QQQM。
- 区分例行月度执行与需要完整 Investment Committee Packet 的非例行交易。

## 生产可靠性

- 真实账户数据必须从 IBKR 实时读取，不得用历史快照冒充今日状态。
- IBKR Positions 是当前持仓数量的权威来源。
- 每日巡检和周度复盘采用固定流程，任何关键数据缺失都必须显式停止交易建议。
- 非例行真实资金建议必须通过 Trade Gate 与 Investment Committee Packet。
- Production 与 Research 严格隔离；研究内容未经正式批准不得影响交易。
- 已知错误记录在`BUGLOG.md`，并包含根因、修复和防复发控制。
- 每个PR由`Policy consistency`工作流检查关键公式、生命周期、研究来源、输入域、逐档执行、候选失效约束和Look-through Packet完整性。

当前生产入口：[PRODUCTION.md](PRODUCTION.md)；补丁说明：[v3.4.2](07-Releases/v3.4.2.md)

## 如何使用

1. 先读 [生产契约](PRODUCTION.md)。
2. 再读 [投资政策声明](00-IPS/Investment-Policy-Statement.md) 和 [目标配置](01-Constitution/Target-Allocation.md)。
3. 每日按 [Daily Review Workflow](02-Operating-System/Daily-Review.md) 读取 IBKR 并检查账户。
4. 每周按 [Weekly Review Workflow](02-Operating-System/Weekly-Review.md) 汇总运行质量与待处理项。
5. 每月先按 [三只ETF估值框架](02-Operating-System/ETF-Valuation-Framework.md) 确定新增资格，再按 [月度流程](02-Operating-System/Monthly-Workflow.md) 执行固定投入和战略现金迁移。
6. 只有估值为`CHEAP`且超出月度基线的战术加速才使用 [部署框架](02-Operating-System/Deployment-Framework.md) 并进入完整IC。
7. 任何非例行真实资金候选先完成 [Investment Committee Packet](02-Operating-System/Decision-Checklist.md)。
8. 每季度按 [Quarterly Workflow](02-Operating-System/Quarterly-Workflow.md) 审核 Alpha、Observation 与穿透集中度。
9. 转型期维护 [Transition Dashboard](03-Transition/Transition-Dashboard.md)。
10. 所有新假设进入 [Research Sandbox](Research/README.md)，不得直接影响生产交易。
11. 每年审核系统规则与 Policy Benchmark。

## 目录

- `PRODUCTION.md`：生产系统入口、规则冻结、运行流程和交易闸门
- `BUGLOG.md`：可靠性缺陷、根因和防复发措施
- `Decision-Log.md`：改变系统方向或产生长期影响的决定
- `Research/`：未生效的研究、假设和版本提案
- `00-IPS/`：使命、期限、风险与治理
- `01-Constitution/`：不可随意改变的目标配置和边界
- `02-Operating-System/`：每日、周度、月度、季度、年度流程及交易闸门
- `03-Transition/`：2026–2028 转型计划与仪表盘
- `04-Alpha/`：Alpha 规则、生命周期和当前分类
- `05-Journal/`：重大投资决策记录
- `06-Lessons/`：长期有效的经验
- `07-Releases/`：版本说明
- `08-Data/`：Production 数据注册表、字段定义、质量闸门和快照

## 优先级

发生冲突时：投资政策声明 → Constitution → Operating System → Transition Dashboard → Journal。`PRODUCTION.md` 负责执行契约和入口，不覆盖以上策略优先级。聊天记录和 Research 不具有现行规则效力。

本仓库用于个人决策纪律与记录，不构成面向他人的投资建议。
