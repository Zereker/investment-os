# 月度流程

月度流程是 Investment OS 的核心执行层，目标用时不超过 20 分钟。

## 输入

- 固定执行日前实时读取的 Account Summary、Balances、Positions、Open Orders
- 本月外部净入金：实际计算只使用已到账金额 \(F\)（计划数额按隐私规则不入库，运行时从 IBKR Cash Transactions 读取实际值）
- 当前税务或流动性约束
- `04-Alpha/Position-Registry.md` 中的板块倾斜状态
- SPYM 与 QQQM 的动态目标和正缺口
- 到 2028-12 剩余的月度执行次数
- SPYM 历史最高收盘回撤 `DD` 与回撤档位状态

## 七步执行

1. 通过 Data Gate，更新 Cash、SPYM、QQQM、SOXX 和 Legacy 的市值。
2. 读取 Registry 的 `A_stage` 与 `A_execution_cap`，按 Constitution 的定义计算 `A_actual`、`A_basis`、`U` 及 SPYM 动态目标；检查执行上限不得高于硬上限。
3. 检查Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套及SOXX 6%硬上限。
4. 确认实际外部净入金 \(F\)，计算入金后 Core 正缺口 \(G_0\)，执行 Routine DCA \(D=\min(F,G_0)\)（按正缺口分配）；未分配金额留在现金。
5. 以 Routine DCA 后的预计现金和剩余 Core 正缺口，按 Deployment Framework 计算战略现金迁移基线 \(B\)。
6. 评估回撤部署档位：`DD` 达档且该档在本周期未执行时，按 Deployment Framework 第 2 节执行部署。
7. 按 Deployment Framework 第 6 节的月度输出格式向所有者报告（聊天输出，不落盘），并记录影子基准；仅在非例行决定时写入 Journal。

## 资金分配算法

- \(F\) = 本月已到账的实际外部净入金，且 \(F\ge0\)；提款或未到账计划额不计入。
- \(V\)=入金后、交易前净值；`A_actual`、`A_basis`、`U` 按 Constitution 定义计算。
- QQQM 目标 = \(V\times28\%\)。
- SPYM 目标 = \(V\times(57\%-A_{basis})\)。
- \(G_0\) = Routine DCA 前两只 Core 的 `max(目标 − 当前市值, 0)` 合计。
- \(D=\min(F,G_0)\)。
- \(C=C_0-D\)，\(G\) = 分配 \(D\) 后两只 Core 的剩余正缺口合计。
- \(S=\max(C-(15\%+U)\times V,0)\)，\(B=\min(S/R,G)\)。
- \(B\) 按剩余正缺口在两只 Core 之间分配；为减少碎片交易，可只购买缺口最大的1–2项。
- 已发布SOXX额度差额`U`作为现金用途标签保留，不先投入SPYM。
- SOXX / 板块倾斜追加不属于月度例行路径。

## 例行路径检查

Routine DCA \(D\)、\(B\) 与回撤部署无需完整四视角 Packet，但必须全部满足：

- 四项 IBKR 数据实时读取成功；
- 只买 SPYM / QQQM；
- 金额完全由已发布公式产生（回撤部署按其分档公式）；
- 交易后物理现金不低于现行下限（常态`12%+U`；回撤档生效时按其临时下限），且不使用融资；
- 没有重复或冲突订单；
- 没有突破 Constitution；
- 订单类型、数量、限价和有效期明确。

任一项不满足时，升级为完整 IC 或 `HOLD / STOP`。

## 非例行部署记录

每次回撤部署、倾斜动作、卖出或公式例外，Journal 至少记录：

- 数据日期与来源；
- 当前价格、`DD` 与档位状态（如适用）；
- \(F,V,C_0,G_0,D,C,R,S,G,B\)；
- 部署金额、订单类型和限价；
- 下一档触发条件；
- 交易后 Cash / QQQM / SPYM / SOXX 权重；
- Verdict（完整 IC 路径时）。

## 完成条件

- 交易后现金仍在约束范围内（含回撤档临时下限），或按 Transition Plan 明确向范围靠拢。
- 没有未经审核的新标的。
- 月度输出已按 Deployment Framework 第 6 节格式呈交所有者。
- \(D\) 与 \(B\) 完全由公式产生，没有被任何判断性闸门削减。
- SOXX 没有通过月度例行路径获得追加。
- 无操作也是有效结果。

## Maintenance Mode

当Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套连续三个自然月落在允许区间，且 Legacy 已按计划处理后，退出 Transition Mode。维护期 \(B=0\)，仅用每月新增资金修复偏差；回撤部署条款继续有效；任何非例行部署继续使用完整 IC。
