# Transition Dashboard

> 每次执行前重新读取 IBKR；本模板不缓存当前账户数值。

## 政策参数

- 结构性现金：15%（12%–18%）
- QQQM：28%（25%–31%）
- SOXX长期上限：15%
- SOXX当前阶段上限 `A_stage`：6%
- SPYM目标：`57%-A_basis`
- 每月计划外部净入金：2,000美元

## 本月实时状态

- 数据日期：待更新
- 净值 `V`：待更新
- 例行订单前物理现金 `C0`：待更新
- 已到账外部净入金 `F`：待更新
- Routine DCA前Core正缺口 `G0`：待更新
- 实际Routine Core买入 `D=min(F,G0)`：待更新
- SOXX实际权重 `A_actual`：待更新
- 当前阶段 `A_stage`：6%
- `A_basis=max(A_actual,A_stage)`：待更新
- 阶段储备 `U=max(A_stage-A_actual,0)`：待更新
- Routine DCA后现金 `C=C0-D`：待更新
- Core剩余正缺口 `G`：待更新
- 剩余执行次数 `R`：待更新
- `S=max(C-(15%+U)×V,0)`：待更新
- `B=min(S/R,G)`：待更新
- 战术加速 `T`：0 / 待IC

| 分类 | 实时权重 | 动态目标 | 状态 |
|---|---:|---:|---|
| Physical Cash | 待更新 | `15%+U` | 待更新 |
| 其中：SOXX Stage Reserve | 待更新 | `U` | 不重复计入 |
| SPYM | 待更新 | `57%-A_basis` | 待更新 |
| QQQM | 待更新 | 28% | 待更新 |
| SOXX | `A_actual` | 当前阶段≤6% | `Approved / Frozen — DATA GATE` |

## 资金通道

| 通道 | 金额 | 目标 | 闸门 |
|---|---:|---|---|
| 外部净入金 | `F`，非默认值 | 资金来源 | 实际到账 |
| Routine DCA | `D=min(F,G0)` | SPYM/QQQM正缺口 | 月度Gate |
| Strategic Baseline | `B` | SPYM/QQQM正缺口 | 月度Gate |
| Tactical Acceleration | `T` | Core正缺口 | 完整IC |
| SOXX追加 | 独立提案 | 不超过当前阶段 | 完整IC+同日穿透 |

本Dashboard不得把 `D`写成默认2,000美元，也不得把阶段储备当成额外资产。
