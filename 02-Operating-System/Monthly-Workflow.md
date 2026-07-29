# 月度流程

月度流程是 Investment OS 的核心执行层，目标用时不超过 20 分钟。

## 输入

- 固定执行日前实时读取的 Account Summary、Balances、Positions、Open Orders
- 本月净入金：默认 2,000 美元
- 当前税务或流动性约束
- `04-Alpha/Position-Registry.md` 中的 Alpha 与 Observation
- SPYM 与 QQQM 的动态目标和正缺口
- 到 2028-12 剩余的月度执行次数
- 战术加速需要的可验证回撤和 PE 历史百分位数据

## 七步执行

1. 通过 Data Gate，更新 Cash、SPYM、QQQM、各 Alpha / Observation 和 Legacy 的市值。
2. 计算 \(A\)、SPYM 动态目标 `57%−A`、当前权重与正缺口。
3. 检查 Cash、QQQM、`SPYM + Alpha` 袖套及 Alpha 硬上限。
4. 每月固定投入优先分配给 SPYM / QQQM 的最大正缺口。
5. 以 Routine DCA 后的预计现金和剩余 Core 正缺口，按 Deployment Framework 计算并执行战略现金迁移基线 \(B\)。
6. 只有估值数据合格且完整 IC 批准时，才允许执行基线之外的战术加速 \(T\)。
7. 更新 Transition Dashboard；仅在非例行决定时写入 Journal。

## 资金分配算法

- \(A\) = 全部实盘 Alpha（含 Observation）市值 ÷ 账户净值。
- \(D\) = 本月实际可执行的固定投入；先将 \(D\) 分配到 Core 正缺口，再计算战略剩余。
- QQQM 目标美元值 = 调整后账户净值 × 28%。
- SPYM 目标美元值 = 调整后账户净值 × \((57\%-A)\)。
- 正缺口 = `max(目标美元值 − 当前市值, 0)`。
- 固定新增资金和 \(B\) 按正缺口分配；为减少碎片交易，可只购买缺口最大的 1–2 项。
- Alpha 未使用额度自动留在 SPYM，不为未来候选预留空置现金。
- Alpha / Observation 追加不属于月度例行路径。

## 例行路径检查

固定投入与 \(B\) 无需完整四视角 Packet，但必须全部满足：

- 四项 IBKR 数据实时读取成功；
- 只买 SPYM / QQQM；
- 金额完全由已发布公式产生；
- 交易后现金不低于 12%，且不使用融资；
- 没有重复或冲突订单；
- 没有突破 Constitution；
- 订单类型、数量、限价和有效期明确。

任一项不满足时，升级为完整 IC 或 `HOLD / STOP`。

## 非例行部署记录

每次 \(T>0\)、Alpha 动作、卖出或公式例外，Journal 至少记录：

- 数据日期与来源；
- 当前价格和高点回撤；
- PE 数值、计算口径、历史窗口和百分位；
- Price / Valuation / Opportunity Score；
- \(V,C_0,D,C,R,S,G,B,T\)；
- 部署金额、订单类型和限价；
- 下一档触发条件；
- 交易后 Cash / QQQM / SPYM / Alpha 权重；
- Investment Committee Verdict。

## 完成条件

- 交易后现金仍在约束范围内，或按 Transition Plan 明确向范围靠拢。
- 没有未经审核的新标的。
- Dashboard 已更新。
- Red / N/A 估值没有触发 \(T\)，但没有阻塞合格的固定投入与 \(B\)。
- SOXX 等 Observation 没有通过月度例行路径获得追加。
- 无操作也是有效结果。

## Maintenance Mode

当 Cash、QQQM、`SPYM + Alpha` 袖套连续三个自然月落在允许区间，且 Legacy 已按计划处理后，退出 Transition Mode。维护期 \(B=0\)，仅用每月新增资金修复偏差；任何非例行部署继续使用完整 IC。
