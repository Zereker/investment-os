# Investment OS v3.4

一套以资产配置为中心、以低决策复杂度长期运行的个人投资系统。

> 使命：通过纪律性的资产配置、长期成长倾斜和一个受严格护栏约束的半导体 Alpha 袖套，实现长期财富增长。

## 当前架构

- 结构性投资组合现金：15%（普通允许区间 12%–18%）
- QQQM：28% 战略成长引擎（允许区间 25%–31%）
- SPYM + SOXX实际持仓 + SOXX阶段储备：57%组合袖套
- SOXX：唯一 Alpha 载体；长期战略上限与最终治理阶段 15%
- 当前 SOXX 治理阶段上限：6%
- 其他 Alpha：0%；未来半导体个股必须与 SOXX 共用同一 15%预算
- 每月计划外部净入金：2,000 美元，实际执行只使用已到账金额

v3.4 区分 SOXX 的实际权重、当前批准阶段与长期上限。未完成的当前阶段额度保留为 SOXX 阶段储备，不先投入 SPYM；该储备只是现金的用途标签，不是第五个资产层，也不是买入授权。

## v3.4 目标

- 将 SOXX 从一般 Observation 明确为唯一战略 Alpha 载体。
- 将 15%定义为长期上限和最终治理阶段，而不是立即执行目标。
- 当前阶段上限保持 6%；之后仅能按 `10% → 12.5% → 15%` 经季度治理推进。
- 用 `A_actual`、`A_stage`、`A_basis` 与阶段储备 `U` 消除先买 SPYM、后为 SOXX 回转的路径依赖。
- 保留科技 50%冻结线、半导体 15% IC 线和发行人护栏；风险护栏优先于阶段目标。
- 完成 SOXX 的政策级 Thesis；当前仍因实时账户与同日穿透快照缺失而 `ADD FROZEN`。
- 修复 Transition Dashboard 的 `F/D` 标签。
- Policy Benchmark 的 15%现金袖套改用假设现金余额重新运行 IBKR 公布的计息规则，不再套用实际账户现金收益率。

## 生产可靠性

- 真实账户数据必须从 IBKR 实时读取，不得用历史快照冒充今日状态。
- SOXX 追加必须同时通过账户 Data Gate、同日 ETF 穿透、阶段上限和完整 Investment Committee。
- 价格档位、回撤或研究结论本身不构成下单授权。
- Production 与 Research 严格隔离；任何交易仍由账户所有者在 IBKR 中亲手确认。

当前生产入口：[PRODUCTION.md](PRODUCTION.md)

## 关键文件

- [投资政策声明](00-IPS/Investment-Policy-Statement.md)
- [目标配置与 SOXX 例外](01-Constitution/Target-Allocation.md)
- [交易前决策清单](02-Operating-System/Decision-Checklist.md)
- [月度流程](02-Operating-System/Monthly-Workflow.md)
- [转型仪表盘](03-Transition/Transition-Dashboard.md)
- [Alpha Position Registry](04-Alpha/Position-Registry.md)
- [SOXX Thesis](04-Alpha/Research/SOXX.md)
- [v3.4 Release](07-Releases/v3.4.md)

## 优先级

发生冲突时：投资政策声明 → Constitution → Operating System → Transition Dashboard → Journal。聊天记录、Research 草稿和 Archive 不具有现行规则效力。

本仓库用于个人决策纪律与记录，不构成面向他人的投资建议。
