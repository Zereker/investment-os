# 月度流程

## 输入

- 实时 IBKR Account Summary、Balances、Positions、Open Orders
- 已到账外部净入金 `F`
- `A_actual`、Registry 中的 `A_stage`
- QQQM、SPYM 动态目标和到2028-12剩余执行次数

## v3.4 变量

\[
A_{basis}=\max(A_{actual},A_{stage}),\qquad U=\max(A_{stage}-A_{actual},0)
\]

- QQQM目标美元值：`28%×V`
- SPYM目标美元值：`(57%-A_basis)×V`
- 物理现金目标：`(15%+U)×V`
- 物理现金下限：`(12%+U)×V`

## 七步执行

1. 通过账户 Data Gate，更新全部市值。
2. 计算 `A_actual`、`A_stage`、`A_basis`、`U` 和动态目标。
3. 确认 `F`；计算 Routine DCA 前 Core 正缺口 `G0`。
4. 计算 `D=min(F,G0)`；`F-D` 保留为现金。
5. Routine DCA 后现金为 `C=C0-D`，剩余 Core 正缺口为 `G`。
6. 计算：

\[
S=\max(C-(15\%+U)\times V,0),\qquad B=\min(S/R,G)
\]

7. 更新 Dashboard。任何 SOXX 操作均转完整 IC，不走月度例行路径。

## 例行路径限制

- `D` 是实际 Core 买入额，不得标记为默认2,000美元。
- 计划2,000美元只属于入金计划；只有已到账金额才进入 `F`。
- `D`与`B`只买 SPYM / QQQM 正缺口。
- SOXX 阶段储备不得被战略基线部署到 Core。
- 交易后物理现金不低于 `12%+U`，且不使用融资。
- 任一实时账户输入失败则 `HOLD / STOP`。

无操作是有效结果；本流程不自动生成 SOXX 买单。
