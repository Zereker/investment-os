# Transition Dashboard

> 本文件是月度执行模板，不保存伪装成“当前”的历史账户快照。每次执行前必须重新读取 IBKR；旧数值可从 Git 历史追溯。

## 政策参数

- Cash 目标：15%（12%–18%）
- QQQM 目标：28%（25%–31%）
- SOXX长期上限15%，当前`A_stage=6%`，当前`A_execution_cap=3%`
- `A_basis=max(A_actual,A_stage)`；`U=max(A_stage-A_actual,0)`
- SPYM目标：`57%-A_basis`
- 物理现金目标：`15%+U`
- 其他Alpha新增授权0%
- 每月新增投入：2,000 美元
- 战略基线计划完成月：2028-12

## 本月实时状态

- 数据日期与市场状态：待更新
- 最新账户净值 \(V\)：待更新
- 全部例行订单前现金 \(C_0\)：待更新
- 本月已到账外部净入金 \(F\)：待更新
- Routine DCA前Core正缺口 \(G_0\)：待更新
- 本月Routine DCA上限\(D_{max}=\min(F,G_0)\)与按正缺口分配的实际Core买入\(D\le D_{max}\)：待更新
- Routine DCA 后预计现金 \(C=C_0-D\)：待更新
- SOXX实际权重`A_actual`、`A_basis`与阶段储备`U`：待更新
- 到 2028-12 剩余执行次数 \(R\)：待更新
- 战略剩余 \(S=\max(C-(15\%+U)\times V,0)\)：待更新
- Core 正缺口合计 \(G\)：待更新
- 战略基线 \(B=\min(S/R,G)\)：待更新
- 战术加速 \(T\)：0 / 待 IC 批准

| 分类 | 实时市值 | 实时权重 | 动态目标 | 状态 |
|---|---:|---:|---:|---|
| Physical Cash | 待更新 | 待更新 | `15%+U` | 待更新 |
| 其中：SOXX Stage Reserve | 不重复计入 | `U` | `U` | 现金用途标签 |
| SPYM | 待更新 | 待更新 | `57%-A_basis` | 待更新 |
| QQQM | 待更新 | 待更新 | 28% | 待更新 |
| SOXX / Alpha | 待更新 | `A_actual` | 当前执行≤3%，阶段≤6%，长期≤15% | `Frozen — DATA GATE` |
| Legacy / Restricted | 待更新 | 待更新 | 按独立计划 | 待更新 |

## Alpha 状态

| 标的 | 生命周期 | 实时数量 / 市值 | 月度新增分配 | 状态 |
|---|---|---:|---:|---|
| SOXX | Frozen — DATA GATE | 从IBKR读取 | 0 | `HOLD — ADD FROZEN` |

本表不缓存数量；新增、升级或退出以`04-Alpha/Position-Registry.md`和相应治理流程为准。当前顺序为`Frozen → Approved / Hold → 有时效Add Candidate Packet → IC APPROVE → 人工下单`；候选最迟当日收盘失效，账户或数据变化立即失效。

## 三条资金通道

| 通道 | 当月金额 | 目标 | 所需闸门 |
|---|---:|---|---|
| Routine DCA | \(D\le\min(F,G_0)\)；计划入金为$2,000但D无默认值 | SPYM / QQQM正缺口；估值不得关闭D | 月度Data / Execution Gate |
| Strategic Baseline | \(B\) | `CHEAP / FAIR`的SPYM / QQQM正缺口 | 月度Data / Valuation / Execution Gate |
| Tactical Acceleration | \(T\) | `CHEAP`且通过数据质量的Core缺口 | 完整IC |

## Tactical Dashboard

| 指标 | SPYM | QQQM |
|---|---:|---:|
| 当前权重 / 动态目标 | 待更新 | 待更新 |
| 正缺口 | 待更新 | 待更新 |
| 当前价格 / 高点回撤（仅执行时点） | 待更新 | 待更新 |
| Forward P/E、口径与自身历史百分位 | 待更新 | 待更新 |
| 利率差 / 盈利增长 / 三个月预测修正 | 待更新 | 待更新 |
| 最终估值等级 / 置信度 | 待更新 | 待更新 |
| 新增资格 | `D / B / T候选 / PAUSE` | `D / B / T候选 / PAUSE` |

## 完成判断

- 交易后物理现金不低于`12%+U`，且无融资。
- Routine DCA与\(B\)完全符合公式和估值资金权限。
- Red / N/A估值或`PROXY CAUTION`保留Routine DCA \(D\)与既定战略基线\(B\)，并令\(T=0\)；只有生产级`VERY EXPENSIVE`可延缓对应标的\(B\)，不得暂停\(D\)。
- SOXX没有通过月度流程获得追加；任何追加只走独立完整IC。
- 预计进入 Maintenance Mode：待更新。
