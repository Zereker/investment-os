# Data Dictionary

## 通用字段

- `observed_at`：本系统读取或记录数据的时间，ISO 8601。
- `source_as_of`：数据发布方标注的数据日期。不得用 `observed_at` 替代。
- `source_name`：发布数据的机构名称。
- `source_url`：官方页面地址。
- `quality`：`Green`、`Yellow` 或 `Red`。
- `notes`：代理源、延迟、解析失败或口径限制。

## v3.4.1配置字段

- `alpha_actual_weight`：\(A_{actual}=\text{SOXX市值}/V\)。
- `alpha_stage_cap`：\(A_{stage}\)，由Position Registry发布，当前6%；合法集合为6%、10%、12.5%、15%。
- `alpha_execution_cap`：\(A_{execution\_cap}\)，当前3%；是下一笔SOXX交易后的最大允许实际权重，合法顺序为3%→4.5%→6%→10%→12.5%→15%，必须满足\(A_{execution\_cap}\le A_{stage}\)。
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
月度符号\(D_{max}\)与\(D\)。\(D_{max}=\min(F,G_0)\)是估值过滤前的Routine DCA上限；\(D\le D_{max}\)是按每只Core的最终估值等级应用新增资格后的实际买入额。\(F-D\)必须保留为现金，不得因默认2,000美元计划额而强制买入。

### strategic_excess_cash_usd / strategic_core_gap_after_usd / strategic_baseline_usd
分别对应 \(S\)、\(G\) 与 \(B\)。其中 \(S=\max(C-(15\%+U)\times V,0)\)，\(G\) 是执行 \(D\) 后 Core 剩余正缺口，\(B=\min(S/R,G)\)。

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

### forward_pe_percentile
当前Forward P/E在同一ETF或其精确跟踪指数、同一P/E定义和同一来源历史序列中的百分位。历史窗口优先10年；最低为连续5年、60个互不重复的历史月末观察值。当前值不得放入历史分布，不得混接Trailing P/E或不同供应商定义。

### forward_eps_growth / forward_eps_revision_3m
未来12个月EPS增长率，以及相同预测口径在过去三个月的变化率。`forward_eps_growth > 0`且`forward_eps_revision_3m ≥ 0`才构成盈利支持；缺失不能假定为零或正值。

### us10y_yield / earnings_yield_spread
`us10y_yield`使用FRED DGS10或已登记美国财政部官方序列。`earnings_yield_spread = 1 / forward_pe − us10y_yield`，两项均以小数计算并保留`source_as_of`。该利差只确认相对无风险收益的补偿，不单独定义贵便宜。

### valuation_tier / valuation_confidence
`valuation_tier`只允许`CHEAP / FAIR / EXPENSIVE / VERY EXPENSIVE / N/A`。只有同一ETF或精确指数、同一P/E口径、可复现且至少60个月的生产级历史序列，才可按`<20 / 20–70 / 70–90 / ≥90`生成正式基础等级。官方当前值但无合格历史只能描述；板块代理、跨口径序列或方法不透明值只能标记`PROXY CAUTION`。盈利和利率确认只能维持或保守上调一级，不能把等级改得更便宜。`valuation_confidence`记录`HIGH / LOW / MIXED / DATA INCOMPLETE`。

### valuation_action
只允许`ADD / HOLD / PAUSE / REVIEW`。它按最终等级、正缺口、现金、订单和生命周期共同生成；估值等级本身不得生成卖出。

## Policy Benchmark 字段

### benchmark_month_start_nav_usd / benchmark_cash_principal_usd / benchmark_accrued_interest_usd / benchmark_cash_sleeve_value_usd

政策基准的现金袖套拆成：

- \(P_{B,d}\)：已经入账、可按IBKR规则计息的假设USD现金本金；
- \(A_{B,d}\)：尚未入账的假设应计利息；
- \(C_{B,d}=P_{B,d}+A_{B,d}\)：现金袖套总价值。应计利息计入基准NAV，但在正式入账前不得进入计息本金。

每个自然月首个估值时点只重置一次政策权重。月初再平衡转移额记为\(R_{B,m,0}\)，只调整已入账本金，使：

\[
P_{B,m,0}+A_{B,m,0}=15\%\times V_{B,m,0}
\]

月内不因SPYM / QQQM每日涨跌重新设定现金权重。若存在上月尚未入账应计利息，月初重置时必须保留该资产并相应调整\(P_{B,m,0}\)，不得把它再次确认为收益。

### benchmark_interest_posting_usd / benchmark_eligible_cash_usd

\(J_{B,d}\)是按模型在当日正式入账的上一自然月应计利息；除IBKR规定的次月第三个工作日外为0。入账先做科目转换：

\[
P^*_{B,d}=P_{B,d-1}+R_{B,d}+J_{B,d},\qquad
A^*_{B,d}=A_{B,d-1}-J_{B,d}
\]

其中\(R_{B,d}\)只允许出现在月初政策再平衡；月内为0。\(J_{B,d}\)必须等于被转出的同一批模型应计利息，转换本身不产生收益。USD前10,000美元不计息：

\[
E_{B,d}=\max(P^*_{B,d}-10000,0)
\]

### ibkr_usd_full_rate / ibkr_nav_scale

\(r_{full,d}\)为当日适用账户计划的官方USD信用利率；\(k_d=\min(V_{B,d}/100000,1)\)。账户计划、币种、Segment、门槛、实际工作日日历和日计息基数必须按当日官方规则记录。

### benchmark_cash_interest_usd / benchmark_cash_period_return

USD通常按360天；当日利息只基于已入账本金，不能基于昨日未入账应计利息：

\[
i_{B,d}=E_{B,d}\times r_{full,d}\times k_d/360
\]

\[
P_{B,d}=P^*_{B,d},\qquad
A_{B,d}=A^*_{B,d}+i_{B,d}
\]

因此日计提不会立即复利；只有上一月利息在规定入账日转为\(P\)后，才参与后续日计息。月度现金袖套收益为：

\[
I_{B,m}=\sum_{d\in m} i_{B,d},\qquad
r^{model}_{cash,m}=I_{B,m}/C_{B,m,0}
\]

任一日输入、工作日日历或利率档位缺失则当月为N/A，不得使用实际账户利息、单位收益率或0%替代。外部现金流不进入基准收益分子；组合比较使用时间加权收益，基准只在下一个月首个估值时点重新设为15% / 57% / 28%。

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

### lookthrough_observed_at / lookthrough_source_as_of / lookthrough_freshness

三只ETF必须在同一审核日采集，`lookthrough_observed_at`记录实际读取时点；每只基金使用该时点可取得的最新官方持仓，`lookthrough_source_as_of`保留发布方日期。三者`source_as_of`完全相同才可为Green；最大差异不超过一个交易日只能为Yellow，超过一个交易日、缺失或并非最新官方版本为Red。SOXX新增要求Green；Yellow或Red只能得到`WAIT / DATA INCOMPLETE`。

### issuer_coverage_ratio / classification_coverage_ratio / unclassified_lookthrough_weight
覆盖率分母为总非现金投资权重；分子分别为具有有效 `issuer_group_id`、以及具有有效统一行业分类的穿透贡献。未覆盖贡献记录为 `unclassified_lookthrough_weight`，不得归一化或静默丢弃。若某护栏的已知下界未越线，但“已知值 + 未分类暴露”可能越线，则相关新增 Alpha / Observation 结论必须为 `WAIT / DATA INCOMPLETE`。

## 缺失值规则

- Markdown 快照使用 `N/A`，不得写 `0`。
- 缺失、Red或`PROXY CAUTION`估值字段不得猜测等级；SPYM/QQQM的Routine DCA `D`与既定战略基线`B`照常，`T=0`。只有生产级`VERY EXPENSIVE`可延缓`B`，且不得关闭`D`。SOXX继续受Alpha/Data Gate约束。
- 缺失或 Red 穿透字段不得被当作零暴露；按覆盖率与上下界规则冻结可能增加相关集中度的新增风险。
- 旧快照可用于审计，不可冒充当前估值或穿透暴露。
