# Strategic Baseline and Three-ETF Valuation-Aware Deployment Framework

> 原则：目标配置决定资金方向和上限；三只 ETF 的估值等级决定新增节奏；现金限制可执行规模；估值贵本身不卖出。

本框架用于 Transition Mode 下历史超额现金的迁移。外部入金驱动的 Routine DCA 与战略基线是例行执行；超过基线的金额才属于战术加速。

## 1. 战略现金迁移基线

在每个固定月度执行日，用实时账户数据和本月例行投入计划定义：

- \(A_{actual}\)：SOXX实际权重；\(A_{stage}\)：Registry当前阶段；\(A_{basis}=\max(A_{actual},A_{stage})\)；
- \(U=\max(A_{stage}-A_{actual},0)\)：现金中的SOXX阶段储备；
- \(F\)：本月已到账的实际外部净入金，且 \(F\ge0\)；计划值为2,000美元，提款或未到账计划额不得计入；
- \(V\)：\(F\) 到账后、交易前的账户净值；
- \(C_0\)：包含 \(F\)、全部例行订单前的投资组合现金；
- \(G_0\)：按QQQM 28%与SPYM \(57\%-A_{basis}\)计算的Routine DCA前正缺口；
- \(D_{max}=\min(F,G_0)\)：估值过滤前的Routine DCA上限；\(D\le D_{max}\)是应用每只Core估值新增资格后的实际买入额；\(F-D\)留在现金；
- \(C=C_0-D\)：执行 Routine DCA 后的预计现金；
- \(G\)：分配 \(D\) 后 SPYM 与 QQQM 的剩余正缺口合计；
- \(R\)：到 2028-12（含）剩余的月度执行次数，最小为 1；
- \(S=\max(C-(15\%+U)\times V,0)\)：扣除结构性现金与SOXX阶段储备后的战略剩余。

当月战略迁移基线：

\[
B=\min\left(\frac{S}{R},G\right)
\]

每月用最新数据重算，不沿用旧金额。基线必须同时满足：

- 交易后物理现金不低于总组合\(12\%+U\)；
- 不使用融资；
- 资金只进入 SPYM / QQQM 正缺口；
- Data Gate、订单冲突和执行检查通过。

先计算未经估值过滤的理论基线，再按 `ETF-Valuation-Framework.md` 对每只Core应用新增资格。`CHEAP / FAIR`可执行`B`，`EXPENSIVE / VERY EXPENSIVE / N/A`的`B=0`。若账户数据不完整、没有Core正缺口或现金已不高于目标，则全部`B=0`。

## 2. 价格与估值的职责

- 当前价格：计算市值、仓位、缺口和订单数量。
- 近期高点回撤：只辅助限价和分批时点，不参与估值等级，不与P/E相加。
- Forward P/E自身历史百分位：形成`CHEAP / FAIR / EXPENSIVE / VERY EXPENSIVE`基础等级。
- 利率差、盈利增长与预测修正：确认或保守上调等级。
- SOXX：额外执行周期调整；仅有Trailing P/E不能判定便宜。

完整定义、边界值和失败处理见`ETF-Valuation-Framework.md`。

## 3. 估值等级与部署路径

| 等级 | Routine DCA `D` | 战略基线 `B` | 战术加速 `T` |
|---|---|---|---|
| `CHEAP` | 允许 | 允许 | 可提交完整IC |
| `FAIR` | 允许 | 允许 | 0 |
| `EXPENSIVE` | 允许 | 0 | 0 |
| `VERY EXPENSIVE` | 0 | 0 | 0 |
| `N/A / DATA INCOMPLETE` | 允许 | 0 | 0 |

以上只适用于SPYM / QQQM正缺口。SOXX沿用Alpha、Registry、Data Gate和完整IC路径，估值等级不授权追加。

## 4. Tactical Acceleration

只有相关Core为`CHEAP`、估值数据Green、存在正缺口且完整IC通过时，才允许`T>0`。每次IC单独确定金额，不再使用旧的价格与估值加总分数或固定倍数；回撤和流动性只参与执行约束。

## 5. Liquidity Capacity

战术加速金额还必须满足：

- 不超过战略剩余 \(S-B\)；
- 不超过执行基线后仍高于`12%+U`物理现金下限、且保留未来两期基线的金额；
- 不超过执行基线后的 Core 正缺口；
- 不得一次用尽可部署现金。

因此：

\[
T \le \min(\text{Score 档位上限},\ S-B,\ \text{Liquidity Capacity},\ \text{剩余 Core 正缺口})
\]

任何 \(T>0\) 都属于非例行战术加速，必须完成完整 Investment Committee Packet。Liquidity 高只表示容量较大，不构成买入理由。

## 6. Core 内部资金方向

- 按Constitution分别计算QQQM 28%与SPYM `57%−A_basis`的正缺口。
- Routine DCA \(D\) 与 \(B\) 优先流向正缺口更大的标的；可按缺口比例分配或只买缺口最大的 1–2 项。
- \(T\) 只有在相关标的 Price 与 Valuation 数据通过质量闸门时才可分配。
- Alpha / Observation 的新增资金不使用本框架，必须走 Alpha 与完整 IC 流程。

## 7. 执行约束

- 下跌本身不是买入理由。
- 不预测最低点，不一次性满仓。
- 波动日优先限价单；市价单仅在流动性充足、点差极小且即时成交确有必要时使用。
- 每次例行执行记录 \(F,V,C_0,G_0,D,C,R,S,G,B\) 和交易后权重。
- 每次战术加速额外记录评分、\(T\)、订单方式和下一档触发条件。
- 买入后不因短期反弹追单，也不因继续下跌立即推翻原规则。

## 8. Monthly Deployment Dashboard 模板

| 指标 | SPYM | QQQM |
|---|---:|---:|
| 当前价格 | 待更新 | 待更新 |
| 当前权重 / 动态目标 | 待更新 | 待更新 |
| 正缺口 | 待更新 | 待更新 |
| 当前价格 / 高点回撤（仅执行时点） | 待更新 | 待更新 |
| Forward P/E、口径与自身历史百分位 | 待更新 | 待更新 |
| 利率差 / 盈利增长 / 预测修正 | 待更新 | 待更新 |
| 最终估值等级 / 置信度 | 待更新 | 待更新 |
| 基线分配 | 待更新 | 待更新 |
| 战术加速 | 0 / IC候选 | 0 / IC候选 |

账户层同时披露 \(F,V,C_0,G_0,D,C,R,S,G,B,T\)、现金比例、融资借款和未完成订单。
