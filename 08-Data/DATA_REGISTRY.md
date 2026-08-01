# Data Registry

本文件登记 Investment OS Production 允许使用的数据源。未登记的数据不得影响真实资金决策。

## 权威顺序

1. 账户状态、持仓、现金、成本、订单、成交：IBKR。
2. ETF 实时价格：IBKR；官方基金页面仅作核对。
3. ETF 穿透持仓与行业表：基金管理人官方页面，且必须保留口径和 `source_as_of`。
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
| Routine Core Gap / Purchase \(G_0,D_{max},D\) | 实时IBKR数据 + Monthly Workflow | 无 | 每月 | Green（Derived） | \(D_{max}=\min(F,G_0)\) |
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
| Look-through Concentration | IBKR 组合权重 + 官方行业/持仓表 + `LOOKTHROUGH_CHECK.md`手工核查 | `scripts/fetch_etf_data.py`（辅助计算） | 每季度及倾斜追加前 | Green（Derived） | 手工加权求和并存档；缺失或口径不明时倾斜追加冻结 |
| ETF Holdings（辅助采集） | SSGA官方xlsx（SPYM全量） | stockanalysis.com聚合页（QQQM/SOXX前25，Yellow） | 季度核查时 | Yellow | 聚合源仅作核查辅助与下界计算；Green质量须官方页面交叉核对；yfinance在受限网络不可用时不得反复重试 |

## 变更治理

- 数据源变更必须通过独立 PR。
- 不得因为当前市场信号更有利而更换口径。
- 同一字段出现来源冲突时，状态降为 Red，停止依赖该字段的倾斜决策。
- 数据缺失不是零值，也不得用旧值冒充当前值。
- 数据失败的影响必须局部化：账户数据失败关闭全部交易路径，穿透核查失败只冻结自主倾斜新增，回撤序列失败只暂停当日分档评估。
