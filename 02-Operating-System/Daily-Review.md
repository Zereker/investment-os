# Daily Review Workflow

每日复盘的目标是客观记录账户状态、发现异常并执行现行规则，而不是临时创造新策略。

## A. 数据读取

依次读取并记录时间戳：

1. IBKR Account Summary
2. IBKR Balances
3. IBKR Positions
4. IBKR Open Orders
5. SPYM / QQQM / SOXX 最近仍在时效内的估值快照

若前四项任一接口失败，账户报告状态为 `DATA INCOMPLETE`。不得用上次快照填充“今日”账户数据。估值快照缺失只关闭相应估值动作，不得冒充当前估值。

## B. 一致性检查

- Net Liquidation 与各币种净值是否合理一致
- Cash 与 Settled Cash 是否存在重要差异
- Gross Position Value 与持仓市值合计是否接近
- Positions 与 Open Orders 是否存在数量冲突
- 是否出现零数量持仓、碎股、异常价格或重复合约
- Leverage 是否来自真实借款，还是仅表示投资比例

## C. 标准输出

### 1. Account Health

- Net Liquidation
- Cash / Settled Cash
- Gross Position Value
- Invested Ratio
- Cash Ratio
- Available Funds
- Margin Loan 状态

### 2. Portfolio Allocation

按以下分类汇总：

- Cash
- Core ETF：SPYM、QQQM
- Alpha：同时列示`Research | Observation | Approved / Hold | Frozen | Exit Review`；临时`Add Candidate`单列并显示有效期
- Restricted / Legacy

同时列出各持仓数量、市值、组合占比、成本和未实现盈亏。Alpha 权重 \(A\) 包含全部实盘 Observation。

SOXX按`Alpha / Frozen — DATA GATE`列示。每日同时报告`A_actual`、`A_stage`、`A_execution_cap`、`A_basis=max(A_actual,A_stage)`与`U=max(A_stage-A_actual,0)`；阶段储备属于现金用途标签，不得重复计入。

### 3. Open Orders

逐笔列出：

- 标的与方向
- 数量、已成交、剩余
- 订单类型、价格、有效期
- 状态与风险说明

没有订单时明确写 `None`。

### 4. Daily Changes

- 当日盈亏
- 新成交
- 仓位数量变化
- 现金变化

无法从接口确认时不得推测原因。

### 5. Risk Check

至少检查：

- 融资借款
- Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套
- Alpha合计15%硬上限；SOXX检查当前执行上限3%、当前阶段6%与长期15%，其他单一Alpha仍执行6%一般上限
- Observation 是否出现未经批准的追加
- 未完成或重复订单
- 碎股与零数量残留
- 真正未经登记的新标的
- 数据冲突

穿透集中度在季度及任何新增 Alpha 前完整计算；日报只在已有合格快照时标记已知越线，不用旧数据制造交易信号。

### 5.1 Three-ETF Valuation Monitor

只监控 SPYM、QQQM、SOXX，并按 `ETF-Valuation-Framework.md` 列示：

- 当前价格、Forward P/E、各自历史百分位；
- 盈利收益率减美国10年期国债收益率；
- Forward EPS增长与三个月预测修正；
- `CHEAP / FAIR / EXPENSIVE / VERY EXPENSIVE / N/A`、置信度与`source_as_of`；
- 当前仓位、动态目标、正缺口以及 `ADD / HOLD / PAUSE / REVIEW`。

回撤只辅助执行时点，不与估值相加。SOXX 必须显示周期调整和 `Frozen — DATA GATE` 状态；估值不得绕过 Alpha 治理。

### 6. Production Decision

只允许以下结论：

- `HOLD`：无生产规则触发，或`Observation / Frozen`仅按既定状态持有
- `REVIEW`：存在异常，需要人工确认，但不直接交易
- `BUY CANDIDATE`：现行规则和估值新增资格同时触发，仍需相应月度路径或完整 Trade Gate
- `SELL CANDIDATE`：现行卖出规则触发，仍需完整 Trade Gate

每日复盘本身不等于下单授权。

### 7. Next Watch

只记录下一次需要观察的客观条件，不新增阈值或指标。

## D. 报告纪律

- 清楚区分实时事实、计算结果、推断和建议。
- 历史快照必须标注日期。
- 研究指标只能放在独立的 Research Note，不得混入 Production Decision。
- 估值贵本身不产生 `SELL CANDIDATE`。
- 无操作是有效结果。
