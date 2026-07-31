# 月度流程

月度流程是 Investment OS 的核心执行层，目标用时不超过 20 分钟。

## 输入

- 固定执行日前实时读取的 Account Summary、Balances、Positions、Open Orders
- 本月计划外部净入金：默认 2,000 美元；实际计算只使用已到账金额 \(F\)
- 当前税务或流动性约束
- `04-Alpha/Position-Registry.md` 中的全部Alpha生命周期状态
- SPYM 与 QQQM 的动态目标和正缺口
- 到 2028-12 剩余的月度执行次数
- SPYM / QQQM / SOXX 按 `ETF-Valuation-Framework.md` 生成的合格估值等级、确认项与时效状态

## 七步执行

1. 通过 Data Gate，更新 Cash、SPYM、QQQM、各 Alpha / Observation 和 Legacy 的市值。
2. 读取`A_stage`与`A_execution_cap`，计算`A_actual`、`A_basis=max(A_actual,A_stage)`、`U=max(A_stage-A_actual,0)`及SPYM动态目标`57%-A_basis`；检查执行上限不得高于阶段。
3. 检查Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套及SOXX阶段/硬上限。
4. 确认实际外部净入金 \(F\)，计算入金后 Core 正缺口 \(G_0\)，再按每只 Core 的估值新增资格计算 Routine DCA \(D\)；未分配金额留在现金。
5. 以 Routine DCA 后的预计现金和剩余 Core 正缺口，按 Deployment Framework 计算战略现金迁移基线 \(B\)，并再次应用估值资格。
6. 只有等级为`CHEAP`、数据为Green且完整 IC 批准时，才允许执行基线之外的战术加速 \(T\)。
7. 更新 Transition Dashboard；仅在非例行决定时写入 Journal。

## 资金分配算法

- \(F\) = 本月已到账的实际外部净入金，且 \(F\ge0\)；提款或未到账计划额不计入。
- \(V\)=入金后、交易前净值；`A_actual`=SOXX市值÷V；`A_stage`与`A_execution_cap`来自Registry；`A_execution_cap≤A_stage`；`A_basis=max(A_actual,A_stage)`；`U=max(A_stage-A_actual,0)`。
- QQQM 目标美元值 = \(V\times28\%\)。
- SPYM目标美元值=\(V\times(57\%-A_{basis})\)。
- \(G_0\) = Routine DCA 前两只 Core 的 `max(目标美元值 − 当前市值, 0)` 合计。
- 先计算 \(D_{max}=\min(F,G_0)\)，再按每只Core的最终估值等级应用资格：`CHEAP / FAIR / N/A`可接受Routine DCA，`EXPENSIVE`只接受Routine DCA且关闭`B/T`，`VERY EXPENSIVE`暂停该标的`D/B/T`。\(D\le D_{max}\)，未分配金额留在现金。
- \(C=C_0-D\)，\(G\) = 分配 \(D\) 后两只 Core 的剩余正缺口合计。
- \(S=\max(C-(15\%+U)\times V,0)\)，\(B=\min(S/R,G)\)。
- \(B\) 只在`CHEAP / FAIR`标的之间按剩余正缺口分配；`EXPENSIVE / VERY EXPENSIVE / N/A`的`B=0`。为减少碎片交易，可只购买缺口最大的1–2项。
- 一般未授权Alpha额度不预留；已发布SOXX当前阶段差额`U`作为现金用途标签保留，不先投入SPYM。
- Alpha / Observation 追加不属于月度例行路径。

## 例行路径检查

Routine DCA \(D\) 与 \(B\) 无需完整四视角 Packet，但必须全部满足：

- 四项 IBKR 数据实时读取成功；
- 只买 SPYM / QQQM；
- 金额完全由已发布公式和 `ETF-Valuation-Framework.md` 的新增资格产生；
- 交易后物理现金不低于`12%+U`，且不使用融资；
- 没有重复或冲突订单；
- 没有突破 Constitution；
- 订单类型、数量、限价和有效期明确。

任一项不满足时，升级为完整 IC 或 `HOLD / STOP`。

## 非例行部署记录

每次 \(T>0\)、Alpha 动作、卖出或公式例外，Journal 至少记录：

- 数据日期与来源；
- 当前价格和高点回撤；
- Forward P/E、计算口径、历史窗口、百分位和最终估值等级；
- 盈利收益率利差、盈利增长、三个月预测修正和置信度；
- \(F,V,C_0,G_0,D,C,R,S,G,B,T\)；
- 部署金额、订单类型和限价；
- 下一档触发条件；
- 交易后 Cash / QQQM / SPYM / Alpha 权重；
- Investment Committee Verdict。

## 完成条件

- 交易后现金仍在约束范围内，或按 Transition Plan 明确向范围靠拢。
- 没有未经审核的新标的。
- Dashboard 已更新。
- `N/A / DATA INCOMPLETE`估值没有触发\(B/T\)，但不阻塞合格的Routine DCA \(D\)；`VERY EXPENSIVE`暂停对应标的全部新增。
- 估值等级只改变新增资金节奏，没有单独触发卖出。
- 处于`Frozen`或`Observation`的SOXX及其他Alpha没有通过月度例行路径获得追加。
- 无操作也是有效结果。

## Maintenance Mode

当Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套连续三个自然月落在允许区间，且 Legacy 已按计划处理后，退出 Transition Mode。维护期 \(B=0\)，仅用每月新增资金修复偏差；任何非例行部署继续使用完整 IC。
