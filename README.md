# Investment OS v4.6

一套以资产配置为中心、以低决策复杂度长期运行的个人投资系统。

> 使命：通过纪律性的资产配置和一个受硬上限约束的板块倾斜，实现长期财富增长。

## 当前架构

- 现金：15%（常态区间 12%–18%；严重回撤时按回撤部署条款分档下调下限）
- QQQM：28% 战略成长引擎（允许区间 25%–31%）
- SPYM + SOXX实际持仓 + SOXX阶段储备：57%组合袖套
- SOXX：唯一自主板块倾斜（半导体行业beta，不是alpha），永久硬上限6%，当前执行上限3%
- 其他板块倾斜新增授权：0%
- SPYM：目标为`57%−A_basis`
- 每月固定新增投入（数额按隐私规则不入库，运行时从 IBKR 读取实际到账）

其中`A_basis=max(A_actual,A_stage)`，`A_stage`固定为6%，`U=max(A_stage-A_actual,0)`；未完成的SOXX额度作为现金中的用途标签保留，不先投入SPYM。风险护栏和数据门优先于执行档目标。QQQM 28%保持不变。

v4.5 起 SOXX 的「追加」拆为两条路径，判别只看`A_execution_cap`动没动：**回补至目标**（执行档不动，买回被市场打下去的权重）走月度例行路径，资金只来自`U`；**提高倾斜**（推进执行档）仍须完整IC。

## v4.0核心变化

v4.0 以实测证据（`Research/2026-07-31-v4-Evidence-and-Proposal.md`）驱动四项结构性修正：

1. **SOXX 封顶 6%**：合并穿透实测显示，目标 Core 自身即含约 18% 半导体暴露；SOXX=15% 时组合半导体约 32%、信息技术进入护栏 WARN 区。10%/12.5%/15% 历史治理阶段作废。
2. **回撤部署**：SPYM 相对历史最高收盘回撤达档时，按档释放现金部署至 Core 正缺口；不依赖任何估值数据，每档每轮回撤周期一次。15% 现金的成本（约 0.45–0.75pp/年）与职能自此对得上账。（v4.0 为三档 ≥15/25/35%、一次部署到下限；v4.3 首档下调至 ≥10%；v4.4 改为定额分批；v4.6 定为四档 ≥10/15/20/25%，每档释放 2.25pp of NAV，在 25% 处打光至绝对下限 `6%+U`，此后不再解锁。）
3. **估值框架降级**：估值等级的闸门作用被大幅削减，例行 DCA 与基线不再被估值数据缺失阻塞（BUG-007 类死锁根除）。该框架其后于 v4.2 整体退役。
4. **穿透子系统简化**：删除约 3,300 行 Look-through Bundle 验证器与 JSON 契约，改为 `08-Data/LOOKTHROUGH_CHECK.md` 季度 15 分钟手工核查；护栏阈值保留，护栏语义修正为约束自主倾斜新增、不阻断 Core 例行路径。

同时新增两个只报告的影子基准：SB-1 满仓政策组合（0% 现金,67/33）与 SB-2 单一基金（100% SPYM），用于年度审判现金拖累与系统复杂度的净价值。

## 生产可靠性

- 真实账户数据必须从 IBKR 实时读取，不得用历史快照冒充今日状态。
- IBKR Positions 是当前持仓数量的权威来源。
- 每日巡检和周度复盘采用固定流程，任何关键数据缺失都必须显式停止交易建议。
- 非例行真实资金建议必须通过 Trade Gate 与 Investment Committee Packet。
- Production 与 Research 严格隔离；研究内容未经正式批准不得影响交易。
- 已知错误记录在`BUGLOG.md`，并包含根因、修复和防复发控制。
- 每个PR由`Policy consistency`工作流检查关键公式、生命周期、输入域与文档一致性。
- 仓库不维护重复的中央证券数据库；普通数据变化不更新项目。

当前生产入口：[PRODUCTION.md](PRODUCTION.md)；版本说明：[v4.6](07-Releases/v4.6.md)（结构性变化见 [v4.0](07-Releases/v4.0.md)）

## 如何使用

> AI 执行者从 [CLAUDE.md](CLAUDE.md) 开始——它是运行手册:任务入口、ETF 数据查询方法、红线与验证命令。

1. 先读 [生产契约](PRODUCTION.md)。
2. 再读 [投资政策声明](00-IPS/Investment-Policy-Statement.md) 和 [目标配置](01-Constitution/Target-Allocation.md)。
3. 每日按 [Daily Review Workflow](02-Operating-System/Daily-Review.md) 读取 IBKR、检查账户并记录回撤档位。
4. 每周按 [Weekly Review Workflow](02-Operating-System/Weekly-Review.md) 汇总运行质量与待处理项。
5. 每月按 [月度流程](02-Operating-System/Monthly-Workflow.md) 执行固定投入、战略现金迁移与达档的回撤部署。
6. 超出月度基线的部署只有回撤档位一条机械路径，见 [部署框架](02-Operating-System/Deployment-Framework.md)；主动加速属于规则例外，须进入完整IC。SOXX 被打到执行档以下时的**回补至目标**同属例行路径（v4.5），**提高倾斜**仍须完整IC。
7. 任何非例行真实资金候选先完成 [Investment Committee Packet](02-Operating-System/Decision-Checklist.md)。
8. 每季度按 [Quarterly Workflow](02-Operating-System/Quarterly-Workflow.md) 完成 [穿透手工核查](08-Data/LOOKTHROUGH_CHECK.md) 并审核倾斜与集中度。
9. 转型期按 [Transition Plan](03-Transition/Transition-Plan.md) 推进；月度输出用 Deployment Framework 的输出格式，只在聊天呈现，不写回仓库。
10. 所有新假设进入 [Research Sandbox](Research/README.md)，不得直接影响生产交易。
11. 每年审核系统规则、Policy Benchmark 与影子基准对比。

## 目录

- `PRODUCTION.md`：生产系统入口、规则冻结、运行流程和交易闸门
- `BUGLOG.md`：可靠性缺陷、根因和防复发措施
- `Decision-Log.md`：改变系统方向或产生长期影响的决定
- `Research/`：未生效的研究、假设和版本提案
- `00-IPS/`：使命、期限、风险与治理
- `01-Constitution/`：不可随意改变的目标配置和边界
- `02-Operating-System/`：每日、周度、月度、季度、年度流程及交易闸门
- `03-Transition/`：2026–2028 转型计划
- `04-Alpha/`：板块倾斜规则、生命周期和当前登记（目录名保留历史命名）
- `05-Journal/`：重大投资决策记录
- `06-Lessons/`：长期有效的经验
- `07-Releases/`：现行版本说明（v1.x–v3.5 已移除，要点见 Decision-Log 存档节）
- `08-Data/`：Production 数据注册表、字段定义、质量闸门、穿透核查和快照
- `scripts/`：`check_policy_consistency.py`（CI 规则镜像）与 `fetch_etf_data.py`（ETF 穿透查询工具）
- `CLAUDE.md`：AI 执行手册

## 优先级

发生冲突时：投资政策声明 → Constitution → Operating System → Transition Plan → Journal。`PRODUCTION.md` 负责执行契约和入口，不覆盖以上策略优先级。聊天记录和 Research 不具有现行规则效力。

本仓库用于个人决策纪律与记录，不构成面向他人的投资建议。
