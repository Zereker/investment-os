# Transition Plan（2026–2028）

## 目标

从旧的高现金、个股为主组合，渐进迁移至：

\[
\text{Cash }(15\%+U) + \text{QQQM }28\% + \text{SPYM }(57\%-A_{basis}) + \text{SOXX }A_{actual}
\]

其中`A_stage=6%`为SOXX永久硬上限（v4.0 起固定），`A_execution_cap=3%`为当前执行上限，`A_basis=max(A_actual,A_stage)`，`U=max(A_stage-A_actual,0)`。QQQM 28%保持不变；U作为现金中的阶段储备，不先投入SPYM。迁移以纪律、税务效率和可执行性为先，计划基线使用 2028-12 作为完成月，并在每月重算。

## 三条资金通道

1. `Routine DCA`：每月固定外部入金（数额不入库）；只使用已到账的\(F\)，执行\(D=\min(F,G_0)\)，\(F-D\)留在现金；v4.0 起\(D\)不被估值等级削减。
2. `Strategic Baseline`：在固定月度执行日，按 Deployment Framework 的 \(B=\min(S/R,G)\) 公式迁移历史超额现金；仅`VERY EXPENSIVE`暂停对应标的的\(B\)。
3. `Drawdown Deployment`：SPYM 相对历史最高收盘回撤达档时，按 Constitution 分档条款部署现金；不依赖估值数据。
4. `Tactical Acceleration`：只有估值为`CHEAP`、数据合格并通过完整 IC 时，才允许在 \(B\) 之上加速。

Red / N/A 估值只将战术加速降为 0，不阻塞 Routine DCA、Strategic Baseline 与回撤部署。

## 原则

1. Routine DCA \(D\) 和战略基线 \(B\) 只进入 SPYM / QQQM 正缺口。
2. 每月根据实时净值、现金、\(A_{actual}\)、\(A_{stage}\)、\(A_{basis}\)、\(U\)、目标缺口和到 2028-12 的剩余执行次数重算。
3. 交易后物理现金不得低于`12%+U`，不得使用融资。
4. SOXX 板块倾斜的月度例行新增分配恒为 0。
5. 所有倾斜新建、追加和卖出均走完整 Investment Committee。
6. 非目标旧持仓和超上限倾斜采用税务感知的渐进退出；不因“高位/低位”单独卖出。
7. 每月只更新一份 Transition Dashboard。

## 阶段

### 阶段 A：建立 Core

- Routine DCA \(D\) 与 Strategic Baseline \(B\) 进入 SPYM / QQQM。
- 按正缺口分配；为减少交易，可只买缺口更大的一个。
- 战术加速不得替代或追认例行基线。

### 阶段 B：处理板块倾斜与 Legacy

- SOXX按`Hold`持有；永久硬上限6%。追加须满足当季手工穿透核查与完整IC（见 Position Registry 追加闸门）。
- 对其他非 Core 持仓区分倾斜、Legacy、税务成本、投资逻辑和组合重叠。
- 对确定退出的旧持仓制定分批或一次性方案，不用价格预测替代决策。
- 若硬上限无法靠稀释修复，再依据 Constitution 进入卖出评审。

### 阶段 C：进入 Maintenance Mode

当Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套连续三个月都位于允许区间，且 Legacy 已按计划处理，转型完成。此后 \(B=0\)，仅用新增资金维护配置；除非触发卖出规则，不主动换仓。

## 时间判断

2028-12 是战略基线的计划完成月，不是收益承诺或强制清仓日。市场涨跌、税务、入金和 Legacy 处理会改变结果；每季度可重估预计完成月，但延长计划必须明确记录，不能靠估值 Red 静默拖延。
