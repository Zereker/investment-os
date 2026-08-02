# Data Dictionary

## 通用字段

- `observed_at`：本系统读取或记录数据的时间，ISO 8601。
- `source_as_of`：数据发布方标注的数据日期。不得用 `observed_at` 替代。
- `source_name`：发布数据的机构名称。
- `source_url`：官方页面地址。
- `quality`：`Green`、`Yellow` 或 `Red`。
- `notes`：代理源、延迟、解析失败或口径限制。

## v4.0配置字段

> 阈值本身以 `01-target-allocation.md` 为唯一权威；本节定义字段口径与计算式，供实现与 CI 校验使用。两者冲突时以 Constitution 为准。

- `alpha_actual_weight`：\(A_{actual}=\text{SOXX市值}/V\)。
- `alpha_stage_cap`：\(A_{stage}\)，由Position Registry发布；v4.0 起固定为6%（永久硬上限）。
- `alpha_execution_cap`：\(A_{execution\_cap}\)，当前3%；是下一笔SOXX交易后的最大允许实际权重，合法顺序为3%→4.5%→6%，必须满足\(A_{execution\_cap}\le A_{stage}\)。
- `alpha_allocation_basis`：\(A_{basis}=\max(A_{actual},A_{stage})\)。
- `soxx_stage_reserve_weight`：\(U=\max(A_{stage}-A_{actual},0)\)，是现金用途标签，不得重复计入。
- `physical_cash_target_weight`：\(15\%+U\)，下限为\(12\%+U\)。
- SPYM目标：\(57\%-A_{basis}\)。

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
月度符号 \(G_0\)。在 \(F\) 到账后，按 QQQM 28% 与 SPYM \(57\%-A_{basis}\) 动态目标计算的 Routine DCA 前正缺口合计。

### routine_core_purchase_limit_usd / routine_core_purchase_usd
月度符号\(D_{max}\)与\(D\)。\(D_{max}=\min(F,G_0)\)是Routine DCA上限；\(D\le D_{max}\)是实际买入额，只受正缺口、现金下限与执行检查约束。\(F-D\)必须保留为现金，不得因计划额而强制买入。

### strategic_excess_cash_usd / strategic_core_gap_after_usd / strategic_baseline_usd
分别对应 \(S\)、\(G\) 与 \(B\)。其中 \(S=\max(C-(15\%+U)\times V,0)\)，\(G\) 是执行 \(D\) 后 Core 剩余正缺口，\(B=\min(S/R,G)\)。

### open_order_status
IBKR Orders 返回的订单状态。存在 `NEW`、`SUBMITTED` 或 `PARTIALLY_FILLED` 时，Trade Gate 必须检查重复交易。

## 市场字段

### spym_last_price_usd / qqqm_last_price_usd
IBKR 返回的最新可用市场价格。必须同时记录读取时间和市场是否开盘。

### drawdown_from_ath / drawdown_tier_state
`drawdown_from_ath`是SPYM收盘价相对历史最高收盘价的回撤，以小数记录并注明收盘序列来源。`drawdown_tier_state`记录当前回撤周期内 T1(≥10%) / T2(≥15%) / T3(≥20%) / T4(≥25%) 四档的`AVAILABLE / EXECUTED`状态；SPYM创历史新高收盘后全部重置为`AVAILABLE`。各档临时现金下限依次为 13.5 / 10.5 / 6 / 0 %（均叠加`U`），梯度步进 1.5 / 3 / 4.5 / 6 pp。T4 之后没有更深的档位：`DD`超过25%时该字段不新增取值，现金已归零，弹药已尽。

## Policy Benchmark 字段

> v4.1 起本模型为月频（依据见 [source repository research](https://github.com/Zereker/investment-os/blob/master/Research/2026-08-01-benchmark-cash-model-simplification.md)）。日频递推、已入账本金/未入账应计拆分与入账日科目转换已退役：它们服务的是一个只报告用的月度数字，却要求逐日利率序列，使该字段结构性恒为 `N/A`。

### benchmark_month_start_nav_usd / benchmark_cash_sleeve_value_usd

每个自然月首个计价时点重置一次政策权重：

\[
C_{B,m,0}=15\%\times V_{B,m,0}
\]

\(C_{B,m,0}\) 同时是当月的计息本金基数。月内不因SPYM / QQQM涨跌重新设定现金权重。上月已计提但尚未入账的利息作为资产计入 \(V\)，因而经由下一次月初重置进入本金；它不得在当月内参与计息，也不得被重复确认为收益。

### ibkr_usd_full_rate / ibkr_nav_scale / benchmark_eligible_cash_usd

- \(r_{B,m}\)：当月适用账户计划的官方USD信用利率；月内变动时按自然日天数加权。
- \(k_{B,m}=\min(V_{B,m,0}/100000,1)\)：NAV比例缩放。
- 免息门槛按IBKR当期公开官方规则取值（公式中记为10000），门槛以下部分不计息。

账户计划、币种、Segment、门槛与日计息基数必须按当期官方规则记录并保留 `source_as_of`。

### benchmark_cash_interest_usd / benchmark_cash_period_return

USD按360天基数，\(N_m\)为当月自然日数：

\[
I_{B,m}=\max(C_{B,m,0}-10000,0)\times r_{B,m}\times k_{B,m}\times \frac{N_m}{360}
\]

\[
r^{model}_{cash,m}=I_{B,m}/C_{B,m,0}
\]

本金固定为月初值，因此利息不在月内复利。利率档位、门槛规则或月初净值缺失时当月为N/A，不得使用实际账户利息、单位收益率、上月值或0%替代。外部现金流不进入基准收益分子；组合比较使用时间加权收益，基准只在下一个月首个计价时点重新设为15% / 57% / 28%。

### spym_total_return / qqqm_total_return
同一计量期间、含分红的基金总收益 \(r_{SPYM,t}\) 与 \(r_{QQQM,t}\)。价格收益不得冒充总收益。

### policy_benchmark_period_return
按月重置权重后计算：
\[
R_{B,t}=15\%\times r^{model}_{cash,t}+57\%\times r_{SPYM,t}+28\%\times r_{QQQM,t}
\]
外部现金流按时间加权收益规则处理，不进入收益分子。

## ETF 穿透与集中度字段

### portfolio_position_weight
账户持仓 \(p\) 的权重 \(w_p=\text{position_market_value_usd}_p/\text{net_liquidation_usd}\)。现金不属于发行人、行业或半导体暴露。

### fund_holding_weight
ETF \(p\) 官方持仓快照中证券 \(i\) 的权重 \(h_{p,i}\)，以小数记录。不得把已披露权重重新归一到 100%；现金、衍生品和未分类残余必须保留。

### issuer_group_id
经济发行人的聚合口径。不同股类（如 GOOGL / GOOG）在季度核查中归并到同一经济发行人并注明归并说明。没有把握时分开列示并标注。

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

### lookthrough_observed_at / lookthrough_source_as_of

三只ETF必须在同一核查日读取各自最新官方版本，`lookthrough_observed_at`记录实际读取时点，`lookthrough_source_as_of`保留各发布方日期。任一来源缺失、口径不明或并非最新官方版本时，本次核查总结论为`DATA INCOMPLETE`，自主倾斜追加冻结。

### unclassified_lookthrough_weight
季度核查中无法按官方行业表分类的穿透贡献（含 QQQM 尾部近似、直接持仓残余等），必须显式列示，不得归一化或静默丢弃。若某护栏的已知值未越线，但“已知值 + 未分类暴露”可能越线，涉及自主倾斜新增的结论必须为 `WAIT / DATA INCOMPLETE`。

## 缺失值规则

- Markdown 快照使用 `N/A`，不得写 `0`。
- 缺失或 Red 穿透字段不得被当作零暴露；冻结自主倾斜新增，不阻断 Core 例行路径。
- 旧快照可用于审计，不可冒充当前价格或穿透暴露。
