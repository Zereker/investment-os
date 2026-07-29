# Data Dictionary

## 通用字段

- `observed_at`：本系统读取或记录数据的时间，ISO 8601。
- `source_as_of`：数据发布方标注的数据日期。不得用 `observed_at` 替代。
- `source_name`：发布数据的机构名称。
- `source_url`：官方页面地址。
- `quality`：`Green`、`Yellow` 或 `Red`。
- `notes`：代理源、延迟、解析失败或口径限制。

## 账户字段

### net_liquidation_usd
IBKR 的 Net Liquidation Value，单位 USD。用于账户净值和权重计算。

### total_cash_usd
IBKR 的 Total Cash Value。不得以 Buying Power 替代现金。

### position_market_value_usd
IBKR Positions 返回的单项市值。持仓真相以 Positions 为准。

### open_order_status
IBKR Orders 返回的订单状态。存在 `NEW`、`SUBMITTED` 或 `PARTIALLY_FILLED` 时，Trade Gate 必须检查重复交易。

## 市场与估值字段

### spym_last_price_usd / qqqm_last_price_usd
IBKR 返回的最新可用市场价格。必须同时记录读取时间和市场是否开盘。

### sp500_pe
State Street SPYM 官方页 `Index Characteristics` 中的 `Price/Earnings`。保留官方标签，不擅自改称 TTM PE，除非来源明确如此定义。

### sp500_pe_fy1
State Street SPYM 官方页 `Price/Earnings Ratio FY1`：按持仓加权调和平均计算的当前价格除以未来一年预测 EPS；预测数据由官方页面披露的数据供应商提供。

### nasdaq100_pe
Invesco QQQM 官方页的 `Price/Earnings Ratio`，要求页面可稳定提取数值、日期和 Weighted Harmonic Average 口径。未满足时为缺失，不得估算。

### nasdaq100_forward_pe
Invesco QQQM 官方页的 `Forward Price/Earnings Ratio`。使用 QQQ 作为代理时，必须为同一日期、同一指数并标记 `proxy=true`。

### pe_percentile_10y
同一指数、同一 PE 定义、同一数据源的 10 年历史百分位。当前没有合格生产数据源，状态固定为 Red。

## 缺失值规则

- Markdown 快照使用 `N/A`，不得写 `0`。
- 缺失或 Red 字段不得参与 Deployment Score。
- 旧快照可用于审计，不可冒充当前估值。
