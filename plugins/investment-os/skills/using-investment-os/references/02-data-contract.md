# 数据契约（Data Contract）

本文件是 Investment OS 可审计数据层的唯一权威：数据操作总则、数据源注册表、数据质量闸门、字段字典与季度穿透手工核查程序。未登记的数据不得影响真实资金决策。

---

## 第一部分：数据操作总则

### 结构

- 第二部分 数据源注册表：允许进入 Production 的来源和失败处理。
- 第四部分 字段字典：字段定义、口径与缺失值规则。
- 第三部分 数据质量闸门：Green / Yellow / Red 数据质量闸门。
- 第五部分 穿透核查程序：季度穿透手工核查程序与记录模板（v4.0 起取代 Bundle 验证器）。
- `records/lookthrough-YYYY-MM-DD.md`：按观察日期保存不可变的季度核查记录。

运行时数据由已登记的专业来源分别提供，仓库不维护重复的中央证券数据库。普通数据变化不更新项目；只有估值快照与季度核查记录按只增不改原则存档。

### 每周估值快照流程

1. 打开已登记的基金管理人官方页面。
2. 记录 `observed_at`、官方 `source_as_of`、字段标签和值。
3. 按数据质量闸门评级。
4. 缺失字段写 `N/A`，不得估算或沿用旧值。
5. 通过 PR 写入快照；历史快照不覆盖，只新增。

### 季度穿透核查

按本文件第五部分手工完成，记录保存为 `records/` 下的日期前缀参考文件。核查结论只限制自主倾斜新增或触发复核，不自动改变注册表、不授权交易。

### Production 边界

快照只提供事实数据。是否影响交易由 `product-contract.md`、`00-constitution.md` 和 `01-operating-manual.md` 决定。数据文件不得自行增加或改变交易规则。

---

## 第二部分：数据源注册表（Data Registry）

### 权威顺序

1. 账户状态、持仓、现金、成本、订单、成交：IBKR。
2. ETF 实时价格：IBKR；官方基金页面仅作核对。
3. ETF 穿透持仓与行业表：基金管理人官方页面，且必须保留口径和 `source_as_of`。
4. 聚合网站、社交媒体、截图和未披露口径的数据：仅可进入 Research。

### 注册表

| 字段 | 主来源 | 备用来源 | 频率 | Production 状态 | 失败处理 |
|---|---|---|---|---|---|
| Net Liquidation | IBKR Account Summary | 无 | 每次巡检 | Green | 读取失败则日报不输出金额，不给 BUY/SELL |
| Cash / Settled Cash | IBKR Balances | 无 | 每次巡检 | Green | 同上 |
| Positions / Average Cost | IBKR Positions | 无 | 每次巡检 | Green | Positions 高于订单和历史成交记录 |
| Open Orders | IBKR Orders | 无 | 每次巡检 | Green | 读取失败则所有交易路径关闭 |
| External Contribution \(F\) | IBKR Activity / Cash Transactions | 无 | 每月 | Green | 只使用已到账外部净入金；提款与内部卖出所得排除 |
| `A_actual` | IBKR SOXX市值 / Net Liquidation | 无 | 每次巡检 | Green（Derived） | 失败则SOXX与动态目标关闭 |
| `A_stage` | 登记表（`00-constitution.md`） | 无 | 每次巡检 | Green | v4.0 起固定 6%（永久硬上限），不得从聊天或价格推导 |
| `A_execution_cap` | 登记表（`00-constitution.md`） | 无 | 每次巡检及任何SOXX IC前 | Green | 当前3%；只能按3%→4.5%→6%逐档更新，且不得高于6% |
| `A_basis` / `U` | 字段字典公式（本文件第四部分） | 无 | 每次巡检 | Green（Derived） | 失败则配置计算关闭 |
| Routine Core Gap / Purchase \(G_0,D_{max},D\) | 实时IBKR数据 + 月度流程 | 无 | 每月 | Green（Derived） | \(D_{max}=\min(F,G_0)\) |
| SPYM 历史最高收盘与回撤 `DD` | IBKR 历史收盘 | State Street 官方净值序列 | 每次巡检 | Green | 驱动回撤部署分档；数据失败则当日不评估分档，不影响其他路径 |
| Benchmark hypothetical 15% USD Cash / modeled interest | 月初基准净值 + IBKR当月官方利率、门槛与NAV比例规则 | 无 | 每月 | Green（Derived） | v4.1 起按月计息（日频递推已退役）；月内不得重置15%现金本金、利息不在月内复利；任一输入缺失则当期Policy Benchmark为N/A |
| Shadow Benchmarks SB-1 / SB-2 | SPYM / QQQM 官方含分红总收益 | IBKR 市场数据与分红记录 | 每月 | Green（Derived） | 仅报告；缺失记 N/A，不触发任何交易路径 |
| SPYM Price | IBKR | State Street SPYM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| QQQM Price | IBKR | Invesco QQQM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| SPYM Total Return | State Street SPYM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | Policy Benchmark 必须使用含分红同期总收益 |
| QQQM Total Return | Invesco QQQM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | 同上 |
| SOXX Price | IBKR | iShares SOXX 官方页 | 每次巡检 | Green | 用于持仓计量，不授权追加 |
| SPYM Holdings / Sector | State Street SPYM 官方页 | 无 | 每季度核查及倾斜追加前 | Green | 缺失时季度核查`DATA INCOMPLETE`，倾斜追加冻结 |
| QQQM Holdings / Sector | Invesco QQQM 官方页 | 无 | 同上 | Green | 同上 |
| SOXX Holdings / Sector | iShares SOXX 官方页 | 无 | 同上 | Green | 缺失时 SOXX 保持禁止追加 |
| Look-through Concentration | IBKR 组合权重 + 官方行业/持仓表 + 本文件第五部分手工核查 | `skills/routing-investment-research/scripts/fetch_etf_data.py`（辅助计算） | 每季度及倾斜追加前 | Green（Derived） | 手工加权求和并存档；缺失或口径不明时倾斜追加冻结 |
| ETF Holdings（辅助采集） | SSGA官方xlsx（SPYM全量） | stockanalysis.com聚合页（QQQM/SOXX前25，Yellow） | 季度核查时 | Yellow | 聚合源仅作核查辅助与下界计算；Green质量须官方页面交叉核对；yfinance在受限网络不可用时不得反复重试 |

### 变更治理

- 数据源变更必须通过独立 PR。
- 不得因为当前市场信号更有利而更换口径。
- 同一字段出现来源冲突时，状态降为 Red，停止依赖该字段的倾斜决策。
- 数据缺失不是零值，也不得用旧值冒充当前值。
- 数据失败的影响必须局部化：账户数据失败关闭全部交易路径，穿透核查失败只冻结自主倾斜新增，回撤序列失败只暂停当日分档评估。

---

## 第三部分：数据质量闸门（Data Quality Gate）

数据质量决定“该字段能否参与哪一类决策”，不评价市场好坏。

### Green

同时满足：

- 来源在数据源注册表中登记；
- 来源为 IBKR 或基金管理人官方页面；
- 字段定义、口径和日期可识别；
- 数据未超过规定刷新周期；
- 没有已知来源冲突。
- 穿透核查数值逐项来自管理人官方行业/持仓表，并在核查记录中保存来源 URL 与 `source_as_of`；缺少官方分类时记 `N/A`，不得自行补写。

Green 数据可以进入其登记的 Production 计算。

### Yellow

出现以下任一情况：

- 使用已登记的备用源或代理源；
- 数据超过刷新周期但仍可审计；
- 官方页面可访问，但字段日期或定义不够完整；
- 账户不同接口存在可解释的轻微时点差异。

Yellow 数据可以展示；涉及真实资金时必须披露限制。不得单独触发任何自主倾斜交易。

### Red

出现以下任一情况：

- 来源未登记、口径不明或无法复现；
- 两个来源给出实质冲突且无法解释；
- 数据缺失、解析失败或明显陈旧；
- 使用截图、社交媒体或聚合页面作为唯一依据；
- 把旧数据、代理值或估算值冒充当前真实值。

Red 数据不得进入依赖该字段的计算。影响按字段局部化：

- IBKR 账户、持仓或订单为 Red：全部交易路径关闭，结论 `DATA INCOMPLETE`。
- ETF穿透核查数据为Red：SOXX与任何自主倾斜保持禁止追加；已有仓位不自动卖出；SPYM / QQQM 例行路径不受阻断。
- SPYM历史最高收盘序列为Red：当日不评估回撤部署分档，已执行档位记录不变。
- Policy Benchmark现金模型的当月利率、门槛或月初净值为Red：当期Benchmark为`N/A / DATA INCOMPLETE`，不得静默使用0%。

### 每次快照必须包含

- `observed_at`
- `source_as_of`
- 来源机构与官方 URL
- 字段值与官方标签
- 质量等级
- 代理源、缺失和冲突说明
- 受影响的交易路径
- 穿透计算的发行人 / 分类覆盖率、未分类权重，以及护栏上下界（如适用）
- 季度穿透核查的来源 URL、`source_as_of` 与近似处理说明（如适用）

### 时效标准

| 数据类型 | Green 时效 |
|---|---|
| IBKR 账户、持仓、订单 | 本次巡检实时读取 |
| 市场价格 | 本次巡检实时读取，注明市场状态 |
| ETF 持仓 / 行业穿透 | 管理人最新公布版本，并记录 `source_as_of`；SOXX新增须存在当季有效的穿透手工核查记录 |

---

## 第四部分：字段字典（Data Dictionary）

### 通用字段

- `observed_at`：本系统读取或记录数据的时间，ISO 8601。
- `source_as_of`：数据发布方标注的数据日期。不得用 `observed_at` 替代。
- `source_name`：发布数据的机构名称。
- `source_url`：官方页面地址。
- `quality`：`Green`、`Yellow` 或 `Red`。
- `notes`：代理源、延迟、解析失败或口径限制。

### v4.0配置字段

> 阈值本身以 `00-constitution.md` 为唯一权威；本节定义字段口径与计算式，供实现与 CI 校验使用。两者冲突时以宪法为准。

- `alpha_actual_weight`：\(A_{actual}=\text{SOXX市值}/V\)。
- `alpha_stage_cap`：\(A_{stage}\)，由登记表发布；v4.0 起固定为6%（永久硬上限）。
- `alpha_execution_cap`：\(A_{execution\_cap}\)，当前3%；是下一笔SOXX交易后的最大允许实际权重，合法顺序为3%→4.5%→6%，必须满足\(A_{execution\_cap}\le A_{stage}\)。
- `alpha_allocation_basis`：\(A_{basis}=\max(A_{actual},A_{stage})\)。
- `soxx_stage_reserve_weight`：\(U=\max(A_{stage}-A_{actual},0)\)，是现金用途标签，不得重复计入。
- `physical_cash_target_weight`：\(15\%+U\)，下限为\(12\%+U\)。
- SPYM目标：\(57\%-A_{basis}\)。

### 账户与月度执行字段

#### net_liquidation_usd
IBKR 的 Net Liquidation Value，单位 USD。用于账户净值和权重计算。

#### total_cash_usd
IBKR 的 Total Cash Value。不得以 Buying Power 替代现金。

#### position_market_value_usd
IBKR Positions 返回的单项市值。持仓真相以 Positions 为准。

#### external_contribution_usd
月度符号 \(F\)。本月已到账的实际外部净入金，且 \(F\ge0\)。提款、内部资产出售所得和未到账计划额不得计入。

#### routine_core_gap_before_usd
月度符号 \(G_0\)。在 \(F\) 到账后，按 QQQM 28% 与 SPYM \(57\%-A_{basis}\) 动态目标计算的 Routine DCA 前正缺口合计。

#### routine_core_purchase_limit_usd / routine_core_purchase_usd
月度符号\(D_{max}\)与\(D\)。\(D_{max}=\min(F,G_0)\)是Routine DCA上限；\(D\le D_{max}\)是实际买入额，只受正缺口、现金下限与执行检查约束。\(F-D\)必须保留为现金，不得因计划额而强制买入。

#### strategic_excess_cash_usd / strategic_core_gap_after_usd / strategic_baseline_usd
分别对应 \(S\)、\(G\) 与 \(B\)。其中 \(S=\max(C-(15\%+U)\times V,0)\)，\(G\) 是执行 \(D\) 后 Core 剩余正缺口，\(B=\min(S/R,G)\)。

#### open_order_status
IBKR Orders 返回的订单状态。存在 `NEW`、`SUBMITTED` 或 `PARTIALLY_FILLED` 时，Trade Gate 必须检查重复交易。

### 市场字段

#### spym_last_price_usd / qqqm_last_price_usd
IBKR 返回的最新可用市场价格。必须同时记录读取时间和市场是否开盘。

#### drawdown_from_ath / drawdown_tier_state
`drawdown_from_ath`是SPYM收盘价相对历史最高收盘价的回撤，以小数记录并注明收盘序列来源。`drawdown_tier_state`记录当前回撤周期内 T1(≥10%) / T2(≥15%) / T3(≥20%) / T4(≥25%) 四档的`AVAILABLE / EXECUTED`状态；SPYM创历史新高收盘后全部重置为`AVAILABLE`。各档临时现金下限依次为 13.5 / 10.5 / 6 / 0 %（均叠加`U`），梯度步进 1.5 / 3 / 4.5 / 6 pp。T4 之后没有更深的档位：`DD`超过25%时该字段不新增取值，现金已归零，弹药已尽。

### Policy Benchmark 字段

> v4.1 起本模型为月频（依据见 [source repository research](https://github.com/Zereker/investment-os/blob/master/Research/2026-08-01-benchmark-cash-model-simplification.md)）。日频递推、已入账本金/未入账应计拆分与入账日科目转换已退役：它们服务的是一个只报告用的月度数字，却要求逐日利率序列，使该字段结构性恒为 `N/A`。

#### benchmark_month_start_nav_usd / benchmark_cash_sleeve_value_usd

每个自然月首个计价时点重置一次政策权重：

\[
C_{B,m,0}=15\%\times V_{B,m,0}
\]

\(C_{B,m,0}\) 同时是当月的计息本金基数。月内不因SPYM / QQQM涨跌重新设定现金权重。上月已计提但尚未入账的利息作为资产计入 \(V\)，因而经由下一次月初重置进入本金；它不得在当月内参与计息，也不得被重复确认为收益。

#### ibkr_usd_full_rate / ibkr_nav_scale / benchmark_eligible_cash_usd

- \(r_{B,m}\)：当月适用账户计划的官方USD信用利率；月内变动时按自然日天数加权。
- \(k_{B,m}=\min(V_{B,m,0}/100000,1)\)：NAV比例缩放。
- 免息门槛按IBKR当期公开官方规则取值（公式中记为10000），门槛以下部分不计息。

账户计划、币种、Segment、门槛与日计息基数必须按当期官方规则记录并保留 `source_as_of`。

#### benchmark_cash_interest_usd / benchmark_cash_period_return

USD按360天基数，\(N_m\)为当月自然日数：

\[
I_{B,m}=\max(C_{B,m,0}-10000,0)\times r_{B,m}\times k_{B,m}\times \frac{N_m}{360}
\]

\[
r^{model}_{cash,m}=I_{B,m}/C_{B,m,0}
\]

本金固定为月初值，因此利息不在月内复利。利率档位、门槛规则或月初净值缺失时当月为N/A，不得使用实际账户利息、单位收益率、上月值或0%替代。外部现金流不进入基准收益分子；组合比较使用时间加权收益，基准只在下一个月首个计价时点重新设为15% / 57% / 28%。

#### spym_total_return / qqqm_total_return
同一计量期间、含分红的基金总收益 \(r_{SPYM,t}\) 与 \(r_{QQQM,t}\)。价格收益不得冒充总收益。

#### policy_benchmark_period_return
按月重置权重后计算：
\[
R_{B,t}=15\%\times r^{model}_{cash,t}+57\%\times r_{SPYM,t}+28\%\times r_{QQQM,t}
\]
外部现金流按时间加权收益规则处理，不进入收益分子。

### ETF 穿透与集中度字段

#### portfolio_position_weight
账户持仓 \(p\) 的权重 \(w_p=\text{position_market_value_usd}_p/\text{net_liquidation_usd}\)。现金不属于发行人、行业或半导体暴露。

#### fund_holding_weight
ETF \(p\) 官方持仓快照中证券 \(i\) 的权重 \(h_{p,i}\)，以小数记录。不得把已披露权重重新归一到 100%；现金、衍生品和未分类残余必须保留。

#### issuer_group_id
经济发行人的聚合口径。不同股类（如 GOOGL / GOOG）在季度核查中归并到同一经济发行人并注明归并说明。没有把握时分开列示并标注。

#### normalized_sector / normalized_industry
用于跨基金聚合的版本化分类。保留管理人原始标签，并把其映射到统一标签；信息技术使用 `Information Technology`，半导体使用 `Semiconductors & Semiconductor Equipment`。冲突映射必须降级质量并披露。

#### lookthrough_exposure_contribution
- 直接公司证券：\(x_i=w_i\)。
- 已登记 ETF 的底层证券：\(x_{p,i}=w_p\times h_{p,i}\)。
- ETF 外壳与其已穿透底层不得同时计入；嵌套基金若未继续穿透，归入未分类残余。

#### issuer_lookthrough_weight
\[
W_{issuer,j}=\sum_{i:\ issuer\_group\_id(i)=j}x_i
\]
用于单一发行人 8% / 10%护栏，并合并直接持仓、SPYM、QQQM、SOXX 与其他已登记 ETF 的同一发行人暴露。

#### sector_lookthrough_weight / technology_lookthrough_weight
\[
W_{sector,s}=\sum_{i:\ normalized\_sector(i)=s}x_i
\]
`technology_lookthrough_weight` 是 \(s=\text{Information Technology}\) 的结果，用于 45% / 50%护栏。

#### semiconductor_lookthrough_weight
\[
W_{semi}=\sum_{i:\ normalized\_industry(i)=\text{Semiconductors \& Semiconductor Equipment}}x_i
\]
用于 15%半导体护栏。

#### lookthrough_observed_at / lookthrough_source_as_of

三只ETF必须在同一核查日读取各自最新官方版本，`lookthrough_observed_at`记录实际读取时点，`lookthrough_source_as_of`保留各发布方日期。任一来源缺失、口径不明或并非最新官方版本时，本次核查总结论为`DATA INCOMPLETE`，自主倾斜追加冻结。

#### unclassified_lookthrough_weight
季度核查中无法按官方行业表分类的穿透贡献（含 QQQM 尾部近似、直接持仓残余等），必须显式列示，不得归一化或静默丢弃。若某护栏的已知值未越线，但“已知值 + 未分类暴露”可能越线，涉及自主倾斜新增的结论必须为 `WAIT / DATA INCOMPLETE`。

### 缺失值规则

- Markdown 快照使用 `N/A`，不得写 `0`。
- 缺失或 Red 穿透字段不得被当作零暴露；冻结自主倾斜新增，不阻断 Core 例行路径。
- 旧快照可用于审计，不可冒充当前价格或穿透暴露。

---

## 第五部分：季度穿透手工核查（Look-through Manual Check）

v4.0 起本核查表取代 Look-through Evidence Bundle 验证器。目标用时 15 分钟。它计算组合合并穿透暴露并对照宪法护栏；通过或失败都不自动改变注册表、不授权交易。

### 频率与时效

- 每季度一次；任何 SOXX / 自主倾斜追加 IC 前必须存在当季有效核查。
- 三只 ETF 的行业/持仓数据须在同一核查日读取各自最新官方版本，记录各自 `source_as_of`。

### 自动化辅助（推荐先跑）

```bash
python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario current            # 目标权重
python3 skills/routing-investment-research/scripts/fetch_etf_data.py --weights spym=…,qqqm=…,soxx=…,cash=…   # 实际权重
python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario current --markdown # 生成快照粘贴块
```

脚本自动完成:SPYM 官方全量持仓(SSGA xlsx,Green)、QQQM/SOXX 前25(聚合源,Yellow)、半导体合并下界+尾部上界、发行人合并与护栏对照。**IT 行业合并值仍须按第 2 步官方行业表手工加权**;需要 Green 质量时用官方页面交叉核对 QQQM/SOXX 数值。脚本失败或数字异常时,回退到下方全手工步骤。

### 步骤

1. 从 IBKR 读取当前 NAV 与 SPYM / QQQM / SOXX / 现金 / 其他持仓市值，计算各袖套权重 `w`。
2. 打开三家管理人官方页面，记录：
   - 各基金信息技术行业权重 `IT_f`（SSGA / Invesco / iShares 官方行业表）；
   - 各基金半导体及设备行业权重 `Semi_f`（SOXX 可按 ~100% 处理并注明）；
   - 各基金前 10 大持仓及权重。
3. 计算合并暴露：
   - `IT_combined = Σ w_f × IT_f`（另加直接持仓中属于 IT 的权重）；
   - `Semi_combined = Σ w_f × Semi_f`（同上）；
   - 对前 10 大发行人：`W_issuer = Σ w_f × h_{f,issuer}`（GOOGL/GOOG 等多股类合并为同一发行人）。
4. 对照护栏：IT 45% WARN / 50% 冻结自主倾斜新增；半导体 15% 倾斜新增须 IC；单一发行人 8% WARN / 10% 冻结。
5. 把下方记录模板保存为 `records/lookthrough-YYYY-MM-DD.md`，通过 PR 提交；历史记录只增不改。

### 记录模板

```markdown
# Look-through Check — YYYY-MM-DD

- observed_at:
- 组合权重 w（来自实时 IBKR）：cash / SPYM / QQQM / SOXX / other =
- SPYM：source_url / source_as_of / IT% / Semi% / 前10大
- QQQM：source_url / source_as_of / IT% / Semi% / 前10大
- SOXX：source_url / source_as_of / Semi%≈100% 说明 / 前10大
- IT_combined =        ｜ 护栏结论：
- Semi_combined =      ｜ 护栏结论：
- Top issuers combined（≥4% 全列）｜ 护栏结论：
- 未分类/近似处理说明（QQQM 尾部、直接持仓等）：
- 总结论：`PASS / WARN / FREEZE-TILT / DATA INCOMPLETE`
```

### 失败处理

- 任一官方页面不可得或口径不明：该字段记 `N/A`，总结论 `DATA INCOMPLETE`，自主倾斜追加冻结；SPYM / QQQM 例行路径不受阻断。
- 数字不得估算、不得沿用上季数值冒充本季。
- 核查发现越线只限制自主倾斜新增或触发复核，不自动卖出。
