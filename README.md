# Investment OS v3.2 LTS

一套以资产配置为中心、以低决策复杂度长期运行的个人投资系统。

> 使命：通过纪律性的资产配置和少量高确信投资，实现长期财富增长。

## 当前架构

- 现金：15%
- SPYM：42%
- QQQM：28%
- Alpha：15%（最多 3–5 只，单只不超过 6%）
- 每月新增投入：2,000 美元

核心收益由市场提供，Alpha 只负责有限度地争取超额收益。目标配置决定长期资金流向；价格回撤与估值共同决定超额现金的部署力度。

## v3.2 LTS 目标

v3.2 LTS 不增加新的交易策略，重点是提高生产可靠性：

- 真实账户数据必须从 IBKR 实时读取，不得用历史快照冒充今日状态。
- IBKR Positions 是当前持仓数量的权威来源。
- 每日巡检采用固定流程，任何数据缺失都必须显式停止交易建议。
- 所有真实资金建议必须通过 Trade Gate。
- Production 与 Research 严格隔离；研究内容未经正式版本发布不得影响交易。
- 已知错误记录在 `BUGLOG.md`，并包含根因、修复和防复发控制。

当前生产入口：[PRODUCTION.md](PRODUCTION.md)

## v3.2 策略框架

- Core 标的为 SPYM / QQQM。
- 使用 Valuation-Aware Deployment Framework。
- 回撤决定部署时机，估值决定部署力度，现金决定可执行规模。
- PE 数据必须注明口径、数据源和历史窗口；无法验证的数据不得单独触发交易。

## 如何使用

1. 先读 [生产契约](PRODUCTION.md)。
2. 再读 [投资政策声明](00-IPS/Investment-Policy-Statement.md) 和 [目标配置](01-Constitution/Target-Allocation.md)。
3. 每日按 [Daily Review Workflow](02-Operating-System/Daily-Review.md) 读取 IBKR 并检查账户。
4. 每月按 [月度流程](02-Operating-System/Monthly-Workflow.md) 更新配置并投入 2,000 美元。
5. 部署超额现金前，执行 [估值感知部署框架](02-Operating-System/Deployment-Framework.md)。
6. 转型期维护 [Transition Dashboard](03-Transition/Transition-Dashboard.md)。
7. 所有新假设进入 [Research Sandbox](Research/README.md)，不得直接影响生产交易。
8. 每季度审核 Alpha；每年才允许审议系统规则。

## 目录

- `PRODUCTION.md`：生产系统入口、规则冻结、每日巡检和交易闸门
- `BUGLOG.md`：可靠性缺陷、根因和防复发措施
- `Research/`：未生效的研究、假设和版本提案
- `00-IPS/`：使命、期限、风险与治理
- `01-Constitution/`：不可随意改变的目标配置和边界
- `02-Operating-System/`：月度、季度、年度流程、交易闸门及部署框架
- `03-Transition/`：2026–2028 转型计划与仪表盘
- `04-Alpha/`：高确信 Alpha 规则和研究档案
- `05-Journal/`：重大投资决策记录
- `06-Lessons/`：长期有效的经验
- `07-Releases/`：版本说明
- `Archive/`：旧规则与历史运行记录，仅供追溯

## 优先级

发生冲突时：投资政策声明 → Constitution → Operating System → Transition Dashboard → Journal。`PRODUCTION.md` 负责执行契约和入口，不覆盖以上策略优先级。聊天记录、Research 和 Archive 不具有现行规则效力。

本仓库用于个人决策纪律与记录，不构成面向他人的投资建议。