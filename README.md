# Investment OS v3.2

一套以资产配置为中心、以低决策复杂度长期运行的个人投资系统。

> 使命：通过纪律性的资产配置和少量高确信投资，实现长期财富增长。

## 当前架构

- 现金：15%
- SPYM：42%
- QQQM：28%
- Alpha：15%（最多 3–5 只，单只不超过 6%）
- 每月新增投入：2,000 美元

核心收益由市场提供，Alpha 只负责有限度地争取超额收益。目标配置决定长期资金流向；价格回撤与估值共同决定超额现金的部署力度。

## v3.2 核心升级

- Core 标的由 SPY / QQQ 更新为更适合长期持有的 SPYM / QQQM。
- 新增 Valuation-Aware Deployment Framework。
- 回撤决定部署时机，估值决定部署力度，现金决定可执行规模。
- PE 数据必须注明口径、数据源和历史窗口；无法验证的数据不得单独触发交易。

## 如何使用

1. 先读 [投资政策声明](00-IPS/Investment-Policy-Statement.md) 和 [目标配置](01-Constitution/Target-Allocation.md)。
2. 每月按 [月度流程](02-Operating-System/Monthly-Workflow.md) 更新配置并投入 2,000 美元。
3. 部署超额现金前，执行 [估值感知部署框架](02-Operating-System/Deployment-Framework.md)。
4. 转型期维护 [Transition Dashboard](03-Transition/Transition-Dashboard.md)。
5. 每季度审核 Alpha；每年才允许审议系统规则。

## 目录

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

发生冲突时：投资政策声明 → Constitution → Operating System → Transition Dashboard → Journal。Archive 不具有现行规则效力。

本仓库用于个人决策纪律与记录，不构成面向他人的投资建议。
