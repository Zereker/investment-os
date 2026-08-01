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
| `A_stage` | Position Registry | 无 | 每次巡检 | Green | v4.0 起固定 6%（永久硬上限），不得从聊天或价格推导 |
| `A_execution_cap` | Position Registry | 无 | 每次巡检及任何SOXX IC前 | Green | 当前3%；只能按3%→4.5%→6%逐档更新，且不得高于6% |
| `A_basis` / `U` | Data Dictionary公式 | 无 | 每次巡检 | Green（Derived） | 失败则配置计算关闭 |
| Routine Core Gap / Purchase \(G_0,D_{max},D\) | 实时IBKR数据 + Monthly Workflow | 无 | 每月 | Green（Derived） | \(D_{max}=\min(F,G_0)\)；v4.0 起 `D` 不被估值等级削减 |
| SPYM 历史最高收盘与回撤 `DD` | IBKR 历史收盘 | State Street 官方净值序列 | 每次巡检 | Green | 驱动回撤部署分档；数据失败则当日不评估分档，不影响其他路径 |
| Benchmark hypothetical 15% USD Cash / modeled interest | 月初基准净值 + IBKR官方利率与计息规则 | 无 | 每日计息、月度重置/报告 | Green（Derived） | 月内不得每日重置15%现金本金；任一输入缺失则当期Policy Benchmark为N/A |
| Shadow Benchmarks SB-1 / SB-2 | SPYM / QQQM 官方含分红总收益 | IBKR 市场数据与分红记录 | 每月 | Green（Derived） | 仅报告；缺失记 N/A，不触发任何交易路径 |
| SPYM Price | IBKR | State Street SPYM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| QQQM Price | IBKR | Invesco QQQM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| SPYM Total Return | State Street SPYM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | Policy Benchmark 必须使用含分红同期总收益 |
| QQQM Total Return | Invesco QQQM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | 同上 |
| SOXX Price | IBKR | iShares SOXX 官方页 | 每次巡检 | Green | 用于持仓计量与估值监控，不授权追加 |
| SPYM Holdings / Sector | State Street SPYM 官方页 | 无 | 每季度核查及倾斜追加前 | Green | 缺失时季度核查`DATA INCOMPLETE`，倾斜追加冻结 |
| QQQM Holdings / Sector | Invesco QQQM 官方页 | 无 | 同上 | Green | 同上 |
| SOXX Holdings / Sector | iShares SOXX 官方页 | 无 | 同上 | Green | 缺失时 SOXX 保持禁止追加 |
| Look-through Concentration | IBKR 组合权重 + 官方行业/持仓表 + `LOOKTHROUGH_CHECK.md`手工核查 | `scripts/fetch_etf_data.py`（辅助计算） | 每季度及倾斜追加前 | Green（Derived） | 手工加权求和并存档；缺失或口径不明时倾斜追加冻结 |
| ETF Holdings（辅助采集） | SSGA官方xlsx（SPYM全量） | stockanalysis.com聚合页（QQQM/SOXX前25，Yellow） | 季度核查时 | Yellow | 聚合源仅作核查辅助与下界计算；Green质量须官方页面交叉核对；yfinance在受限网络不可用时不得反复重试 |
| SPYM Forward P/E | State Street SPYM官方页 | 同日SPY官方页，标记Proxy | 每周 | Green | 保存官方标签、`source_as_of`和定义 |
| QQQM Forward P/E | Invesco QQQM官方页 | 同日QQQ官方页（同一Nasdaq-100指数、同一P/E口径），标记Proxy | 每周 | Red（未稳定采集） | 等级为N/A；N/A 只关闭 `T`，不关闭 `D / B` |
| SOXX Forward P/E | iShares SOXX官方页或已登记Market Data & Estimates源 | 无 | 每周 | Red（来源待验证） | 不得用Trailing P/E产生CHEAP或追加结论 |
| 三只ETF Forward P/E历史序列与百分位 | 同一ETF或精确跟踪指数、同一Market Data & Estimates源和同一P/E定义 | 无 | 每月 | Red（来源待验证） | 最少5年/60个历史月末值，10年优先；失败时等级N/A，`D/B`照常、`T=0` |
| Forward EPS Growth / 3M Revision | 已登记Market Data & Estimates源 | 无 | 每周 | Red（来源待连接） | 缺失时不改善基础等级并降低置信度；SOXX不得判定CHEAP |
| US 10Y Treasury Yield | FRED DGS10 | 美国财政部官方序列 | 每周 | Green | 与估值`source_as_of`对齐；超过时效则确认项N/A |
| Earnings Yield Spread | `1 / Forward P/E − US10Y` | 无 | 每周 | Green（Derived） | 只作确认；不得单独制造CHEAP结论 |

## 变更治理

- 数据源变更必须通过独立 PR。
- 不得因为当前市场信号更有利而更换口径。
- 同一字段出现来源冲突时，状态降为 Red，停止依赖该字段的战术或倾斜决策。
- 数据缺失不是零值，也不得用旧值冒充当前值。
- 数据失败的影响必须局部化：估值失败只关闭 \(T\)，账户数据失败关闭全部交易路径，穿透核查失败只冻结自主倾斜新增，回撤序列失败只暂停当日分档评估。
- 宽泛行业/板块P/E、方法不透明聚合值或跨Trailing/Forward口径序列只能标记`PROXY CAUTION`并进入Research，不得输出正式四档或改变`D/B/T`（吸收自v3.5.1）。
