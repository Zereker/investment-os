# Weekly Review Workflow

周度复盘用于确认 Investment OS 是否可靠运行、整理月度流程输入并暴露需要修复的问题。它不创造交易信号，不修改目标配置，也不替代月度、季度或年度治理。

## A. 输入

- 本周 Daily Review 记录
- 复盘时重新读取的 IBKR Account Summary、Balances、Positions、Open Orders
- 最新有效的 `08-Data/SNAPSHOTS/` 数据
- `04-Alpha/Position-Registry.md`
- 本周成交、未完成订单和异常记录
- 当前 Transition Dashboard

若实时 IBKR 数据未完整读取，周报标记为 `DATA INCOMPLETE`，不得给出新的 BUY / SELL 建议。

## B. 账户完整性

- Net Liquidation、Cash、Settled Cash 与 Gross Position Value 的周内变化
- Positions 是否出现未解释的数量、成本或合约变化
- 是否存在融资借款、重复订单、异常碎股或零数量残留
- Open Orders 是否仍与现行计划一致
- Daily Review 是否有缺失、失败或使用历史快照冒充实时数据

## C. 配置与转型

- Cash / SPYM / QQQM / Alpha / Legacy的当前权重，以及`A_actual`、`A_stage`、`A_execution_cap`、`A_basis`、`U`
- Alpha内列示`Research | Observation | Approved / Hold | Frozen | Exit Review`；临时`Add Candidate`单列有效期；有真实资金的Observation全额计入`A_actual`
- 与Constitution的Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套和硬上限差异
- 本月累计固定投入、战略基线 \(B\) 与战术加速 \(T\)
- 是否出现只能靠季度/年度治理处理的结构性偏差

周度复盘只标记偏差，不因一周波动临时再平衡。SOXX当前为`Frozen — DATA GATE`，本身不产生`IC REVIEW`；只有现行指数方法证据完成、Registry已为`Approved / Hold`，并用实时账户及同一审核日/同`source_as_of`的Green穿透形成未过期`Add Candidate` Packet，才可进入完整IC。

## D. 数据质量

- IBKR 账户数据是否保持 Green
- SPYM、QQQM、SOXX价格和估值数据的来源、`source_as_of`、自身历史百分位与刷新状态
- 穿透持仓与行业数据是否足够支持新增 Alpha 审查
- Yellow / Red 字段及其影响范围
- 是否需要新增数据快照、修复解析或更新 Data Registry

Red / N/A估值不得猜测等级；SPYM/QQQM的Routine DCA \(D\)与既定战略基线\(B\)照常，\(T=0\)，SOXX不得产生估值追加结论。板块代理只标记`PROXY CAUTION`，不得改变资金安排；缺失值不得用旧值或估算值填补。

## E. 行为与执行

- 本周是否有未经过相应交易路径的账户操作
- 是否出现追涨、接飞刀、盘中临时起意或规则漂移
- 固定投入与 \(B\) 是否完全符合月度公式和简化 Gate
- \(T\)、Alpha、卖出及例外是否在下单前完成完整 Investment Committee Packet
- Observation 是否出现未批准追加
- 实际执行是否与批准的方向、数量、限价和有效期一致
- 多数日子的 `HOLD` 是否被当作有效结果

## F. Research 边界

- 本周新增研究是否全部留在 `Research/` 或 `04-Alpha/Research/`
- 是否有研究指标被误写入 Production 输出
- 需要升级为正式 Proposal 的问题，仅记录标题、证据缺口和负责人；不得在周报中直接生效

## G. 周度输出

周报只允许形成以下工作项：

- `NO ACTION`：系统正常，无额外动作。
- `MONTHLY INPUT`：记录到下次月度流程，不提前交易。
- `IC REVIEW`：存在真实资金候选，进入 `Decision-Checklist.md`，尚未授权下单。
- `DATA FIX`：先修复数据或流程，Trade Gate 保持关闭。

每项输出必须包含负责人、下一次检查条件和截止到哪个治理窗口；没有工作项时明确写 `None`。
