# Data Dictionary

## 通用字段

- `observed_at`：本系统读取或记录数据的时间，ISO 8601。
- `source_as_of`：数据发布方标注的数据日期。不得用 `observed_at` 替代。
- `source_name`：发布数据的机构名称。
- `source_url`：官方页面地址。
- `quality`：`Green`、`Yellow` 或 `Red`。
- `notes`：代理源、延迟、解析失败或口径限制。

## 账户与月度执行字段

### net_liquidation_usd
IBKR 的 Net Liquidation Value，单位 USD。用于账户净值和权重计算。

### total_cash_usd
IBKR 的 Total Cash Value。不得以 Buying Power 替代现金。

### position_market_value_usd
IBKR Positions 返回的单项市值。持仓真相以 Positions 为准。

### external_contribution_usd
月度符号 \(F\)。本月已到账的实际外部净入金，且 \(F\ge0\)。提款、内部资产出售所得和未到账计划额不得计入。

### routine_core_gap_before_usd
月度符号 \(G_0\)。在 \(F\) 到账后，按 QQQM 28% 与 SPYM \(57\%-A\) 动态目标计算的 Routine DCA 前正缺口合计。

### routine_core_purchase_usd
月度符号 \(D\)。定义为 \(D=\min(F,G_0)\)。\(F-D\) 必须保留为现金，不得因默认 2,000 美元计划额而强制买入。

### strategic_excess_cash_usd / strategic_core_gap_after_usd / strategic_baseline_usd
分别对应 \(S\)、\(G\) 与 \(B\)。其中 \(S=\max(C-15\%\times V,0)\)，\(G\) 是执行 \(D\) 后 Core 剩余正缺口，\(B=\min(S/R,G)\)。

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
同一指数、同一 PE 定义、同一数据源的 10 年历史百分位。当前没有合格生产数据源，状态固定为 Red，不得进入 Tactical Opportunity Score；其缺失只令 \(T=0\)。

## Policy Benchmark 字段

### usd_cash_interest_usd
月度符号 \(I_t\)。IBKR 在同一计量期间实际计提的 USD 现金利息，单位 USD。外部入金、证券收益和已实现盈亏不得混入。

### usd_eligible_cash_twa_usd
月度符号 \(\bar C^{eligible}_t\)。同一期间合格 USD 现金余额的期限加权平均值；必须与 \(I_t\) 使用相同计息口径和日期范围。

### usd_cash_period_return
\[
r_{cash,t}=\frac{I_t}{\bar C^{eligible}_t}
\]
只有分子、分母和期间均可复现且分母大于 0 时才计算。实际利息美元不得直接作为 Policy Benchmark 的现金收益；输入不合格时按 0%计并披露限制。

### spym_total_return / qqqm_total_return
同一计量期间、含分红的基金总收益 \(r_{SPYM,t}\) 与 \(r_{QQQM,t}\)。价格收益不得冒充总收益。

### policy_benchmark_period_return
按月重置权重后计算：
\[
R_{B,t}=15\%\times r_{cash,t}+57\%\times r_{SPYM,t}+28\%\times r_{QQQM,t}
\]
外部现金流按时间加权收益规则处理，不进入收益分子。

## ETF 穿透与集中度字段

### portfolio_position_weight
账户持仓 \(p\) 的权重 \(w_p=\text{position_market_value_usd}_p/\text{net_liquidation_usd}\)。现金不属于发行人、行业或半导体暴露。

### fund_holding_weight
ETF \(p\) 官方持仓快照中证券 \(i\) 的权重 \(h_{p,i}\)，以小数记录。不得把已披露权重重新归一到 100%；现金、衍生品和未分类残余必须保留。

### issuer_group_id
经济发行人的稳定聚合键。不同股类归并到同一经济发行人；映射必须保存原始证券标识、映射依据与 `source_as_of`。没有可审计映射时不得猜测。

### normalized_sector / normalized_industry
用于跨基金聚合的版本化分类。保留管理人原始标签，并把其映射到统一标签；信息技术使用 `Information Technology`，半导体使用 `Semiconductors & Semiconductor Equipment`。冲突映射必须降级质量并披露。

### lookthrough_exposure_contribution
- 直接公司证券：\(x_i=w_i\)。
- 已登记 ETF 的底层证券：\(x_{p,i}=w_p\times h_{p,i}\)。
- ETF 外壳与其已穿透底层不得同时计入；嵌套基金若未继续穿透，归入未分类残余。

### issuer_lookthrough_weight
\[
W_{issuer,j}=\sum_{i:\ issuer\_group\_id(i)=j}x_i
\]
用于单一发行人 8% / 10%护栏，并合并直接持仓、SPYM、QQQM、SOXX 与其他已登记 ETF 的同一发行人暴露。

### sector_lookthrough_weight / technology_lookthrough_weight
\[
W_{sector,s}=\sum_{i:\ normalized\_sector(i)=s}x_i
\]
`technology_lookthrough_weight` 是 \(s=\text{Information Technology}\) 的结果，用于 45% / 50%护栏。

### semiconductor_lookthrough_weight
\[
W_{semi}=\sum_{i:\ normalized\_industry(i)=\text{Semiconductors \& Semiconductor Equipment}}x_i
\]
用于 15%半导体护栏。

### issuer_coverage_ratio / classification_coverage_ratio / unclassified_lookthrough_weight
覆盖率分母为总非现金投资权重；分子分别为具有有效 `issuer_group_id`、以及具有有效统一行业分类的穿透贡献。未覆盖贡献记录为 `unclassified_lookthrough_weight`，不得归一化或静默丢弃。若某护栏的已知下界未越线，但“已知值 + 未分类暴露”可能越线，则相关新增 Alpha / Observation 结论必须为 `WAIT / DATA INCOMPLETE`。

## 缺失值规则

- Markdown 快照使用 `N/A`，不得写 `0`。
- 缺失或 Red 估值字段不得进入 Tactical Opportunity Score，只关闭战术加速 \(T\)。
- 缺失或 Red 穿透字段不得被当作零暴露；按覆盖率与上下界规则冻结可能增加相关集中度的新增风险。
- 旧快照可用于审计，不可冒充当前估值或穿透暴露。
