# Strategic Baseline and Valuation-Aware Deployment Framework

> 原则：目标配置决定战略基线；价格与估值只决定是否加速；现金只限制可执行规模。

本框架用于 Transition Mode 下历史超额现金的迁移。外部入金驱动的 Routine DCA 与战略基线是例行执行；超过基线的金额才属于战术加速。

## 1. 战略现金迁移基线

在每个固定月度执行日，用实时账户数据和本月例行投入计划定义：

- \(A_{actual}\)：SOXX实际权重；\(A_{stage}\)：Registry当前阶段；\(A_{basis}=\max(A_{actual},A_{stage})\)；
- \(U=\max(A_{stage}-A_{actual},0)\)：现金中的SOXX阶段储备；
- \(F\)：本月已到账的实际外部净入金，且 \(F\ge0\)；计划值为2,000美元，提款或未到账计划额不得计入；
- \(V\)：\(F\) 到账后、交易前的账户净值；
- \(C_0\)：包含 \(F\)、全部例行订单前的投资组合现金；
- \(G_0\)：按QQQM 28%与SPYM \(57\%-A_{basis}\)计算的Routine DCA前正缺口；
- \(D=\min(F,G_0)\)：本月实际可执行的 Routine DCA Core 买入额；\(F-D\) 留在现金；
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

估值字段为 Yellow / Red / N/A 不会把 \(B\) 降为零；它只关闭战术加速。若账户数据不完整、没有 Core 正缺口或现金已不高于目标，则 \(B=0\)。

## 2. Price Score：从近期高点的回撤

| 回撤 | 分数 |
|---:|---:|
| < 5% | 0 |
| 5%–10% | 1 |
| 10%–15% | 2 |
| 15%–20% | 3 |
| > 20% | 4 |

优先使用对应指数或同一指数 ETF 的可验证高点。QQQM 使用 Nasdaq-100 / QQQM 同口径数据；SPYM 使用 S&P 500 / SPYM 同口径数据。

## 3. Valuation Score：PE 历史百分位

| PE 历史百分位 | 分数 |
|---:|---:|
| > 80% | 0 |
| 60%–80% | 1 |
| 40%–60% | 2 |
| 20%–40% | 3 |
| < 20% | 4 |

PE 数据必须同时记录指数、PE 与盈利口径、数据源、历史窗口和时间戳。若数值冲突、口径不明或来源不可验证，Valuation Score 为 `N/A`，不得猜测。

## 4. Tactical Opportunity Score

\[
\text{Opportunity Score}=\text{Price Score}+\text{Valuation Score}
\]

Liquidity 不参与加分，只约束金额。

| Opportunity Score | 基线之外的默认动作 |
|---:|---|
| 0–3 | 不加速；只执行 Routine DCA \(D\) 与 \(B\) |
| 4–5 | 第一档：最多额外 \(1\times B\) |
| 6–7 | 第二档：最多额外 \(2\times B\) |
| 8 | 第三档：最多额外 \(3\times B\) |

当 Valuation Score 为 `N/A` 时，战术加速金额 \(T=0\)，但 Routine DCA \(D\) 与战略基线仍可执行。

## 5. Liquidity Capacity

战术加速金额还必须满足：

- 不超过战略剩余 \(S-B\)；
- 不超过执行基线后仍高于 12%现金下限、且保留未来两期基线的金额；
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
| 高点回撤 / Price Score | 待更新 | 待更新 |
| PE、口径与历史百分位 | 待更新 | 待更新 |
| Valuation Score | 待更新 | 待更新 |
| 基线分配 | 待更新 | 待更新 |
| 战术加速 | 0 / 第一档 / 第二档 / 第三档 | 0 / 第一档 / 第二档 / 第三档 |

账户层同时披露 \(F,V,C_0,G_0,D,C,R,S,G,B,T\)、现金比例、融资借款和未完成订单。
