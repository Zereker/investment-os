# Data Registry

本文件登记 Investment OS Production 允许使用的数据源。未登记的数据不得影响真实资金决策。

## 权威顺序

1. 账户状态、持仓、现金、成本、订单、成交：IBKR。
2. ETF 实时价格：IBKR；官方基金页面仅作核对。
3. ETF / 指数估值及穿透持仓：基金管理人官方页面，且必须保留口径和 `source_as_of`。
4. 聚合网站、社交媒体、截图和未披露口径的数据：仅可进入 Research。

## 注册表

| 字段 | 主来源 | 备用来源 | 频率 | Production 状态 | 失败处理 |
|---|---|---|---|---|---|
| Net Liquidation | IBKR Account Summary | 无 | 每次巡检 | Green | 读取失败则日报不输出金额，不给 BUY/SELL |
| Cash / Settled Cash | IBKR Balances | 无 | 每次巡检 | Green | 同上 |
| Positions / Average Cost | IBKR Positions | 无 | 每次巡检 | Green | Positions 高于订单和历史成交记录 |
| Open Orders | IBKR Orders | 无 | 每次巡检 | Green | 读取失败则所有交易路径关闭 |
| External Contribution \(F\) | IBKR Activity / Cash Transactions | 无 | 每月 | Green | 只使用已到账外部净入金；提款与内部卖出所得排除 |
| `A_actual` | IBKR SOXX市值 / Net Liquidation | 无 | 每次巡检 | Green（Derived） | 失败则SOXX与动态目标关闭 |
| `A_stage` | Position Registry | 无 | 每次巡检 | Green | 当前6%；合法阶段6% / 10% / 12.5% / 15%，不得从聊天或价格推导 |
| `A_execution_cap` | Position Registry | 无 | 每次巡检及任何SOXX IC前 | Green | 当前3%；只能按3%→4.5%→6%→10%→12.5%→15%逐档更新，且不得高于`A_stage` |
| `A_basis` / `U` | Data Dictionary公式 | 无 | 每次巡检 | Green（Derived） | 失败则配置计算关闭 |
| Routine Core Gap / Purchase \(G_0,D_{max},D\) | 实时IBKR数据 + Monthly Workflow + ETF Valuation Framework | 无 | 每月 | Green（Derived） | \(D_{max}=\min(F,G_0)\)，估值过滤后\(D\le D_{max}\)；\(F-D\)留在现金 |
| Benchmark hypothetical 15% USD Cash / modeled interest | 月初基准净值 + IBKR官方利率与计息规则 | 无 | 每日计息、月度重置/报告 | Green（Derived） | 月内不得每日重置15%现金本金；任一输入缺失则当期Policy Benchmark为N/A |
| SPYM Price | IBKR | State Street SPYM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| QQQM Price | IBKR | Invesco QQQM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| SPYM Total Return | State Street SPYM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | Policy Benchmark 必须使用含分红同期总收益 |
| QQQM Total Return | Invesco QQQM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | 同上 |
| SOXX Price | IBKR | iShares SOXX 官方页 | 每次巡检 | Green | 用于持仓计量与估值监控，不授权追加 |
| SPYM Holdings / Sector | State Street SPYM 官方页 | 无 | 每季度及新增 Alpha 前 | Green | 缺失时冻结依赖穿透数据的新 Alpha |
| QQQM Holdings / Sector | Invesco QQQM 官方页 | 无 | 每季度及新增 Alpha 前 | Green | 同上 |
| SOXX Holdings / Sector | iShares SOXX 官方页 | 无 | 每季度及追加前 | Green | 缺失时 SOXX 保持 ADD FROZEN |
| SOXX / NYSE Semiconductor Index Methodology | ICE Index Platform + iShares现行Prospectus | 无 | 每季度及方法变更时 | Red（证据待补齐） | 完整现行方法未形成可审计记录前，SOXX Research保持Incomplete、Registry保持Frozen |
| Security Identity / Issuer Group | SEC / GLEIF / 证券主数据插件 + 管理人官方稳定标识 | 已登记的第二身份源 | 运行时；决策留证 | Green（Derived） | 跨CUSIP / ISIN / SEDOL / ticker统一到canonical security与CIK / LEI；记录来源与`as_of`；缺失或冲突则DATA INCOMPLETE |
| Sector / Industry Map | 权威GICS数据插件 + 管理人原始分类 | 已登记的第二分类源 | 运行时；决策留证 | Green（Derived） | 原始分类缺失时必须有独立权威来源；记录来源与`as_of`；缺失、冲突或无法验证则DATA INCOMPLETE |
| Look-through Concentration | IBKR 组合权重 + 官方 ETF 持仓 + Look-through Evidence Bundle v1.5验证器 | 无 | 每季度及新增 Alpha 前 | Green（Derived） | 运行时组合多源数据；仅在真实决策时保存原始文件、身份/分类快照与Packet SHA-256；从完整底层行重算发行人、科技、半导体、覆盖率与未分类权重 |
| SPYM Forward P/E | State Street SPYM官方页 | 同日SPY官方页，标记Proxy | 每周 | Green | 保存官方标签、`source_as_of`和定义 |
| QQQM Forward P/E | Invesco QQQM官方页 | 同日QQQ官方页（同一Nasdaq-100指数、同一P/E口径），标记Proxy | 每周 | Red（未稳定采集） | 只描述当前值；无合格历史时不输出正式等级，不改变`D/B`，`T=0` |
| SOXX Forward P/E | iShares SOXX官方页或已登记Market Data & Estimates源 | 无 | 每周 | Red（来源待验证） | 不得用Trailing P/E产生CHEAP或追加结论 |
| 三只ETF Forward P/E历史序列与百分位 | 同一ETF或精确跟踪指数、同一Market Data & Estimates源和同一P/E定义 | 无 | 每月 | Red（来源待验证） | 最少5年/60个历史月末值，10年优先；失败时`VALUATION UNAVAILABLE`，`D/B`照常、`T=0` |
| Forward EPS Growth / 3M Revision | 已登记Market Data & Estimates源 | 无 | 每周 | Red（来源待连接） | 缺失时不改善基础等级并降低置信度；SOXX不得判定CHEAP |
| US 10Y Treasury Yield | FRED DGS10 | 美国财政部官方序列 | 每周 | Green | 与估值`source_as_of`对齐；超过时效则确认项N/A |
| Earnings Yield Spread | `1 / Forward P/E − US10Y` | 无 | 每周 | Green（Derived） | 只作确认；不得单独制造CHEAP结论 |

## 变更治理

- 数据源变更必须通过独立 PR。
- 不得因为当前市场信号更有利而更换口径。
- 同一字段出现来源冲突时，状态降为 Red，停止依赖该字段的战术或 Alpha 决策。
- 数据缺失不是零值，也不得用旧值冒充当前值。
- 数据失败的影响必须局部化：估值失败只关闭 \(T\)，不关闭Routine DCA \(D\)或既定战略基线 \(B\)；账户数据失败关闭全部交易路径，穿透数据失败关闭新的重叠 Alpha。
- 宽泛行业/板块P/E、方法不透明聚合值或跨Trailing/Forward口径序列只能标记`PROXY CAUTION`并进入Research，不得输出正式四档或改变`D/B/T`。
