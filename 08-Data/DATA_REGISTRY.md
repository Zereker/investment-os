# Data Registry

本文件登记 Investment OS Production 允许使用的数据源。未登记的数据不得影响真实资金决策。

## 权威顺序

1. 账户状态、持仓、现金、成本、订单、成交：IBKR。
2. ETF 实时价格：IBKR；官方基金页面仅作核对。
3. ETF/指数估值：基金管理人官方页面，且必须保留口径和 `source_as_of`。
4. 聚合网站、社交媒体、截图和未披露口径的数据：仅可进入 Research。

## 注册表

| 字段 | 主来源 | 备用来源 | 频率 | Production 状态 | 失败处理 |
|---|---|---|---|---|---|
| Net Liquidation | IBKR Account Summary | 无 | 每次巡检 | Green | 读取失败则日报不输出金额，不给 BUY/SELL |
| Cash / Settled Cash | IBKR Balances | 无 | 每次巡检 | Green | 同上 |
| Positions / Average Cost | IBKR Positions | 无 | 每次巡检 | Green | Positions 高于订单和历史成交记录 |
| Open Orders | IBKR Orders | 无 | 每次巡检 | Green | 读取失败则 Trade Gate 关闭 |
| SPYM Price | IBKR | State Street SPYM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| QQQM Price | IBKR | Invesco QQQM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| S&P 500 Price/Earnings | State Street SPYM 官方页 | State Street SPY 官方页 | 每周 | Green | 保存官方 `source_as_of` 和计算标签 |
| S&P 500 FY1 P/E | State Street SPYM 官方页 | State Street SPY 官方页 | 每周 | Green | 保存官方 `source_as_of` 和计算定义 |
| Nasdaq-100 Price/Earnings | Invesco QQQM 官方页 | 同日 Invesco QQQ 官方页，标记 Proxy | 每周 | Red（未稳定采集） | 不进入 Deployment Score |
| Nasdaq-100 Forward P/E | Invesco QQQM 官方页 | 同日 Invesco QQQ 官方页，标记 Proxy | 每周 | Red（未稳定采集） | 不进入 Deployment Score |
| PE 历史百分位 | 暂无合格源 | 无 | — | Red | 禁止在 Production 使用 |

## 变更治理

- 数据源变更必须通过独立 PR。
- 不得因为当前市场信号更有利而更换口径。
- 同一字段出现来源冲突时，状态降为 Red，停止依赖该字段的交易决策。
- 数据缺失不是零值，也不得用旧值冒充当前值。
