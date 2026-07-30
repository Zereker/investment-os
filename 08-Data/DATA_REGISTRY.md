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
| Routine Core Gap / Purchase \(G_0,D\) | 实时 IBKR 数据 + Monthly Workflow | 无 | 每月 | Green（Derived） | \(D=\min(F,G_0)\)；\(F-D\) 留在现金 |
| Benchmark hypothetical 15% USD Cash / modeled interest | 月初基准净值 + IBKR官方利率与计息规则 | 无 | 每日计息、月度重置/报告 | Green（Derived） | 月内不得每日重置15%现金本金；任一输入缺失则当期Policy Benchmark为N/A |
| SPYM Price | IBKR | State Street SPYM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| QQQM Price | IBKR | Invesco QQQM 官方页 | 每次巡检 | Green | 标记价格时间戳 |
| SPYM Total Return | State Street SPYM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | Policy Benchmark 必须使用含分红同期总收益 |
| QQQM Total Return | Invesco QQQM 官方绩效 / 分红数据 | IBKR 市场数据与分红记录 | 每月 | Green | 同上 |
| SOXX Price | IBKR | iShares SOXX 官方页 | 每次巡检 | Green | 只用于持仓计量，不授权追加 |
| SPYM Holdings / Sector | State Street SPYM 官方页 | 无 | 每季度及新增 Alpha 前 | Green | 缺失时冻结依赖穿透数据的新 Alpha |
| QQQM Holdings / Sector | Invesco QQQM 官方页 | 无 | 每季度及新增 Alpha 前 | Green | 同上 |
| SOXX Holdings / Sector | iShares SOXX 官方页 | 无 | 每季度及追加前 | Green | 缺失时 SOXX 保持 ADD FROZEN |
| SOXX / NYSE Semiconductor Index Methodology | ICE Index Platform + iShares现行Prospectus | 无 | 每季度及方法变更时 | Red（证据待补齐） | 完整现行方法未形成可审计记录前，SOXX Research保持Incomplete、Registry保持Frozen |
| Issuer Group / Sector / Industry Map | 管理人官方持仓标识与分类 | 已审计的版本化映射 | 每季度及新增 Alpha 前 | Green（Derived） | 保留原标签、统一标签、映射依据与日期；冲突不得猜测 |
| Look-through Concentration | IBKR 组合权重 + 官方 ETF 持仓 + Look-through Evidence Bundle v1.1验证器 | 无 | 每季度及新增 Alpha 前 | Green（Derived） | 保存原始文件与Packet SHA-256；从完整底层行重算发行人、科技、半导体、覆盖率与未分类权重；验证失败或可能越线则 WAIT / DATA INCOMPLETE |
| S&P 500 Price/Earnings | State Street SPYM 官方页 | State Street SPY 官方页 | 每周 | Green | 保存官方 `source_as_of` 和计算标签 |
| S&P 500 FY1 P/E | State Street SPYM 官方页 | State Street SPY 官方页 | 每周 | Green | 保存官方 `source_as_of` 和计算定义 |
| Nasdaq-100 Price/Earnings | Invesco QQQM 官方页 | 同日 Invesco QQQ 官方页，标记 Proxy | 每周 | Red（未稳定采集） | 不进入 Tactical Opportunity Score |
| Nasdaq-100 Forward P/E | Invesco QQQM 官方页 | 同日 Invesco QQQ 官方页，标记 Proxy | 每周 | Red（未稳定采集） | 不进入 Tactical Opportunity Score |
| PE 历史百分位 | 暂无合格源 | 无 | — | Red | 战术加速 \(T=0\)；不阻塞 DCA 与战略基线 \(B\) |

## 变更治理

- 数据源变更必须通过独立 PR。
- 不得因为当前市场信号更有利而更换口径。
- 同一字段出现来源冲突时，状态降为 Red，停止依赖该字段的战术或 Alpha 决策。
- 数据缺失不是零值，也不得用旧值冒充当前值。
- 数据失败的影响必须局部化：估值失败关闭 \(T\)，账户数据失败关闭全部交易路径，穿透数据失败关闭新的重叠 Alpha。
