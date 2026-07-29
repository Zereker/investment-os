# Daily Review Workflow

每日复盘的目标是客观记录账户状态、发现异常并执行现行规则，而不是临时创造新策略。

## A. 数据读取

依次读取并记录时间戳：

1. IBKR Account Summary
2. IBKR Balances
3. IBKR Positions
4. IBKR Open Orders

若任一接口失败，报告状态为 `DATA INCOMPLETE`。不得用上次快照填充“今日”数据。

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
- Alpha
- Restricted / Legacy

同时列出各持仓数量、市值、组合占比、成本和未实现盈亏。

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
- 仓位上限和 Alpha 上限
- 未完成或重复订单
- 碎股与零数量残留
- 未经审核的新标的
- 数据冲突

### 6. Production Decision

只允许以下结论：

- `HOLD`：无生产规则触发，或信息不足
- `REVIEW`：存在异常，需要人工确认，但不直接交易
- `BUY CANDIDATE`：现行规则触发，仍需完整 Trade Gate
- `SELL CANDIDATE`：现行规则触发，仍需完整 Trade Gate

每日复盘本身不等于下单授权。

### 7. Next Watch

只记录下一次需要观察的客观条件，不新增阈值或指标。

## D. 报告纪律

- 清楚区分实时事实、计算结果、推断和建议。
- 历史快照必须标注日期。
- 研究指标只能放在独立的 Research Note，不得混入 Production Decision。
- 无操作是有效结果。
