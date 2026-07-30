# Strategic Baseline and Valuation-Aware Deployment Framework

> 目标配置决定战略基线；价格与估值只决定是否加速；阶段储备不得被 Core 部署占用。

## 1. 定义

- `F`：已到账外部净入金；
- `V`：入金后、交易前净值；
- `A_actual`：SOXX实际权重；
- `A_stage`：当前批准阶段上限；
- `A_basis=max(A_actual,A_stage)`；
- `U=max(A_stage-A_actual,0)`；
- `C0`：例行订单前物理现金；
- `G0`：按 QQQM 28%与SPYM `57%-A_basis`计算的Core正缺口；
- `D=min(F,G0)`；
- `C=C0-D`；
- `G`：执行D后剩余Core正缺口；
- `R`：到2028-12剩余执行次数，最小1；
- `S=max(C-(15%+U)×V,0)`。

战略基线：

\[
B=\min(S/R,G)
\]

基线必须保证交易后物理现金不低于 `(12%+U)×V`，不使用融资，只进入 SPYM / QQQM 正缺口。

## 2. Tactical Acceleration

沿用 v3.3 的 Price Score 与 Valuation Score。估值 Red / N/A 令战术加速 `T=0`，不阻塞合格的 `D` 与 `B`。Liquidity 只限制金额，不构成信号。

\[
T\le \min(\text{评分档位上限},S-B,\text{Liquidity Capacity},\text{剩余Core正缺口})
\]

任何 `T>0` 必须完成完整 IC。SOXX 不使用本框架；所有 SOXX 追加独立走 Alpha IC。

## 3. 记录

每次月度执行记录 `F,V,A_actual,A_stage,A_basis,U,C0,G0,D,C,R,S,G,B,T`。不得把 `F`、`D`或`U`互相替代。
