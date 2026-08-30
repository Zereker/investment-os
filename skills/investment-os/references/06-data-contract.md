# 数据契约（Data Contract）

本文件是 Investment OS 可审计数据层的唯一权威：数据操作总则、数据源注册表、数据质量闸门与字段字典。未登记的数据不得影响真实资金决策。

---

## 第一部分：数据操作总则

运行时数据由已登记的专业来源分别提供，仓库不维护重复的中央证券数据库，也不保存任何数据快照。事实只在受信任的私有运行时或当前私有会话中使用；后续无法取得可信证据时必须重新读取，不得回退到仓库副本。

### Production 边界

运行时事实不创建政策。是否影响交易由 canonical `SKILL.md`、`00-constitution.md` 与编号流程文件决定。

---

## 第二部分：数据源注册表（Data Registry）

### 权威顺序

1. 账户状态、持仓、现金、成本、订单、成交：IBKR。
2. ETF 实时价格：IBKR；官方基金页面仅作核对。
3. 聚合网站、社交媒体、截图和未披露口径的数据：仅可进入 Research。

### 注册表

| 字段 | 主来源 | 备用来源 | 频率 | Production 状态 | 失败处理 |
|---|---|---|---|---|---|
| Net Liquidation | IBKR Account Summary | 无 | 每次巡检 | Green | 读取失败则日报不输出金额，不给 BUY/SELL |
| Cash / Settled Cash | IBKR Balances | 无 | 每次巡检 | Green | 同上 |
| Positions / Average Cost | IBKR Positions | 无 | 每次巡检 | Green | Positions 高于订单和历史成交记录 |
| Open Orders | IBKR Orders | 无 | 每次巡检 | Green | 读取失败则所有交易路径关闭 |
| External Contribution \(F\) | IBKR Activity / Cash Transactions | 无 | 每月 | Green | 只使用已到账外部净入金；提款与内部卖出所得排除 |
| 各标的实际权重与正缺口 | IBKR 市值 / Net Liquidation + 宪法目标权重 | 无 | 每次巡检 | Green（Derived） | 失败则配置计算关闭 |
| Routine Gap / Purchase \(G_0,D_{max},D\) | 实时 IBKR 数据 + 月度流程 | 无 | 每月 | Green（Derived） | \(D_{max}=\min(F,G_0)\) |
| SPYM 历史最高收盘与回撤 `DD` | IBKR 历史收盘 | State Street 官方净值序列 | 每次巡检 | Green | 由会话读取后传入脚本，脚本不自行联网取数；必须带收盘日期，超过 7 天或无日期则当日不评估分档，不影响其他路径 |
| Legacy / Out-of-Universe 持仓市值 | IBKR Positions | 无 | 每次巡检 | Green | 进入 NAV 对账；不产生目标、缺口或任何通道资金。遗漏会使对账失败并卡住全部交易路径 |
| VIX 日收盘 | IBKR 历史收盘 | CBOE 官网 | 每次巡检 | Green | 定义波动日（≥20）供限价单偏好；不进入任何资金闸门 |
| SPX PE-TTM 与月度历史 | multpl（GAAP as-reported） | 无 | 每次巡检 | Green | **只作披露**；口径必须随数值记录，不同口径不得混算分位 |
| CNN 恐慌贪婪 | CNN dataviz 接口 | 无 | 每次巡检 | Green | **只作披露**；直接用接口的 `rating`，不自行按数字套档 |
| SPYM Price | IBKR | State Street SPYM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| QQQM Price | IBKR | Invesco QQQM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| SOXX Price | IBKR | iShares SOXX 官方页 | 每次巡检 | Green | 标记价格时间戳 |

### 变更治理

- 数据源变更必须通过独立 PR。
- 不得因为当前市场信号更有利而更换口径。
- 同一字段出现来源冲突时，状态降为 Red。
- 数据缺失不是零值，也不得用旧值冒充当前值。

---

## 第三部分：数据质量闸门（Data Quality Gate）

数据质量决定「该字段能否参与哪一类决策」，不评价市场好坏。

### Green

同时满足：

- 来源在数据源注册表中登记；
- 来源为 IBKR 或基金管理人官方页面；
- 字段定义、口径和日期可识别；
- 数据未超过规定刷新周期；
- 没有已知来源冲突。

Green 数据可以进入其登记的 Production 计算。

### Yellow

出现以下任一情况：

- 使用已登记的备用源或代理源；
- 数据超过刷新周期但仍可审计；
- 官方页面可访问，但字段日期或定义不够完整；
- 账户不同接口存在可解释的轻微时点差异。

Yellow 数据可以展示；涉及真实资金时必须披露限制。

### Red

出现以下任一情况：

- 来源未登记、口径不明或无法复现；
- 两个来源给出实质冲突且无法解释；
- 数据缺失、解析失败或明显陈旧；
- 使用截图、社交媒体或聚合页面作为唯一依据；
- 把旧数据、代理值或估算值冒充当前真实值。

Red 数据不得进入依赖该字段的计算。**影响必须按字段局部化**：

- IBKR 账户、持仓或订单为 Red：全部交易路径关闭，结论 `DATA INCOMPLETE`。
- SPYM 历史最高收盘序列为 Red：当日不评估回撤部署分档，已执行档位记录不变。
- 市场背景任一字段为 Red 或不可达：该字段记「缺（原因）」，不阻断任何路径——它本就不是任何闸门的输入。

### 每次事实读取必须包含

- `observed_at`
- `source_as_of`
- 来源机构与官方 URL
- 字段值与官方标签
- 质量等级
- 代理源、缺失和冲突说明
- 受影响的交易路径

### 时效标准

| 数据类型 | Green 时效 |
|---|---|
| IBKR 账户、持仓、订单 | 本次巡检实时读取 |
| 市场价格 | 本次巡检实时读取，注明市场状态 |

---

## 第四部分：字段字典（Data Dictionary）

### 通用字段

- `observed_at`：本系统读取或记录数据的时间，ISO 8601。
- `source_as_of`：数据发布方标注的数据日期。不得用 `observed_at` 替代。
- `source_name`：发布数据的机构名称。
- `source_url`：官方页面地址。
- `quality`：`Green`、`Yellow` 或 `Red`。
- `notes`：代理源、延迟、解析失败或口径限制。

### 配置字段

> 目标权重与带宽本身以 `00-constitution.md` 为唯一权威；本节只定义字段口径与计算式，供实现与 CI 校验使用。两者冲突时以宪法为准。

- `position_weight`：标的市值 ÷ `net_liquidation_usd`。
- `position_target_weight`：宪法第一部分战略结构表中该标的的目标权重（现金 15%、SPYM 50%、QQQM 30%、SOXX 5%）。
- `position_gap_usd`：\(\max(\text{目标权重}\times V-\text{市值},0)\)。负值取 0，不产生卖出信号。
- `within_band`：该标的实际权重是否落在宪法带宽内（现金 10–20%、SPYM 45–55%、QQQM 25–35%）。SOXX 无对称带宽，记 `N/A`。
- `soxx_above_ceiling`：SOXX 实际权重是否超过宪法的 7.5% 披露上沿。只作披露，不阻断任何路径。
- `cash_absolute_floor_weight`：0%，任何情形下的硬下限。现金可以归零，不得为负。例行路径够不到它（`B ≤ S`、`D ≤ F`），只有回撤部署能把现金推到那里。

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
月度符号 \(G_0\)。在 \(F\) 到账后，按目标权重计算的三个可购买标的 Routine DCA 前正缺口合计。

#### routine_core_purchase_limit_usd / routine_core_purchase_usd
月度符号 \(D_{max}\) 与 \(D\)。\(D_{max}=\min(F,G_0)\) 是 Routine DCA 上限；\(D\le D_{max}\) 是实际买入额，只受正缺口、现金下限与执行检查约束。\(F-D\) 必须保留为现金，不得因计划额而强制买入。

#### strategic_excess_cash_usd / strategic_core_gap_after_usd / strategic_baseline_usd
分别对应 \(S\)、\(G\) 与 \(B\)。其中 \(S=\max(C-15\%\times V,0)\)，\(G\) 是执行 \(D\) 后的剩余正缺口，\(B=\min(S/R,G)\)。

#### open_order_status
IBKR Orders 返回的订单状态。存在 `NEW`、`SUBMITTED` 或 `PARTIALLY_FILLED` 时，Trade Gate 必须检查重复交易。

### 市场字段

#### spym_last_price_usd / qqqm_last_price_usd / soxx_last_price_usd
IBKR 返回的最新可用市场价格。必须同时记录读取时间和市场是否开盘。

#### drawdown_from_ath / drawdown_tier_state
`drawdown_from_ath` 是 SPYM 收盘价相对历史最高收盘价的回撤，以小数记录并注明收盘序列来源。`drawdown_tier_state` 记录当前回撤周期内四档的 `AVAILABLE / EXECUTED` 状态；SPYM 创历史新高收盘后全部重置为 `AVAILABLE`；最深档之后没有更深档位，该字段不新增取值。各档触发线、梯度定额与绝对下限以 `00-constitution.md` 回撤部署节的分档表为唯一权威。

### 缺失值规则

缺失字段记 `N/A`，不得写 `0`，不得估算，不得沿用旧值冒充当前值。影响按第三部分 Red 的局部化规则处理。
