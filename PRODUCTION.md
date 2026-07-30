# Investment OS v3.4 — Production Contract

本文件是当前生产系统的入口与执行契约。

## 1. 唯一事实来源

规则优先级：

1. `00-IPS/`
2. `01-Constitution/`
3. `02-Operating-System/`
4. `03-Transition/`
5. `05-Journal/`

SOXX 的分类、阶段与生命周期以 `04-Alpha/Position-Registry.md` 为准，但不得覆盖 Constitution。聊天记录、截图、历史快照和 Research 草稿不具有生产规则效力。

## 2. v3.4 生产冻结

- SOXX 是唯一 Alpha 载体，长期上限和最终治理阶段为总组合 15%。
- 当前批准阶段上限为 6%；15%不是当前买入授权。
- 超过 6%前仍需逐笔完整 IC；从 6%推进至 10%、12.5%或15%必须先更新 Registry 并通过季度治理。
- 科技 50%冻结线、半导体 15% IC 线、发行人 8%/10%护栏和数据完整性优先于任何阶段目标。
- 价格、回撤或达到研究档位只能触发复核，不能自动生成订单。
- 本版本发布本身不产生 BUY / SELL 指令。

## 3. 每日巡检

依次实时读取 IBKR Account Summary、Balances、Positions 与 Open Orders；任一失败即 `DATA INCOMPLETE`，不得给出新 BUY / SELL 建议。

计算并列示：

- Cash、QQQM、SPYM、SOXX 与 Legacy；
- SOXX 实际权重 `A_actual`；
- 当前治理阶段 `A_stage`、计算基数 `A_basis=max(A_actual,A_stage)`；
- 未完成阶段储备 `U=max(A_stage-A_actual,0)`；
- SOXX 状态：`Approved / Frozen — DATA GATE`。

阶段储备只是对现金的用途标签，不得与现金重复计入净值。

## 4. 交易路径

Routine DCA 与 Strategic Baseline 只进入 SPYM / QQQM 正缺口，并按 v3.4 动态目标计算。战术加速、任何 SOXX 追加、阶段推进、卖出、换仓或规则例外必须完成 `02-Operating-System/Decision-Checklist.md`。

SOXX 追加必须同时满足：

- 四项 IBKR 实时读取成功；
- SOXX 交易后权重不超过当前 `A_stage`；
- SPYM、QQQM、SOXX 使用同日最新官方持仓完成穿透；
- 科技、半导体、发行人和未分类暴露通过 Data Gate；
- Thesis 仍有效，完整 IC Verdict 为 `APPROVE`；
- 订单由账户所有者在 IBKR 中亲手确认。

任一项失败，结论只能为 `WAIT / DATA INCOMPLETE` 或 `REJECT`。

## 5. 数据权威

- 仓位：IBKR Positions
- 订单：IBKR Open Orders
- 现金和净值：IBKR Account Summary 与 Balances
- Alpha 状态：Position Registry
- ETF 价格：IBKR；官方基金页面仅核对
- ETF 持仓与行业：基金管理人官方文件
- 字段、质量和公式：`08-Data/DATA_REGISTRY.md`、`DATA_DICTIONARY.md` 与 `DATA_QUALITY.md`

事实、推断、治理决定和交易授权必须明确分开。
