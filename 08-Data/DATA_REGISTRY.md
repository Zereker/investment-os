# Data Registry

未登记数据不得影响真实资金决策。

| 字段 | 主来源 | 频率 | 失败处理 |
|---|---|---|---|
| Net Liquidation / Cash / Positions / Orders | IBKR对应实时接口 | 每次巡检 | 关闭全部交易路径 |
| External Contribution `F` | IBKR Activity / Cash Transactions | 每月 | 只使用已到账外部净入金 |
| `A_actual` | IBKR SOXX市值÷Net Liquidation | 每次巡检 | SOXX与动态目标关闭 |
| `A_stage` | Position Registry | 每次巡检 | 配置计算关闭 |
| `A_basis`,`U` | Data Dictionary公式 | 每次巡检 | 配置计算关闭 |
| SPYM / QQQM / SOXX Price | IBKR | 每次巡检 | 不得给相关交易提案 |
| SPYM Holdings / Sector | State Street官方 | 每季度及SOXX追加前 | SOXX `ADD FROZEN` |
| QQQM Holdings / Sector | Invesco官方 | 同上 | 同上 |
| SOXX Holdings / Sector | iShares官方 | 同上 | 同上 |
| Issuer / Sector / Industry Map | 官方标识+审计映射 | 同上 | 冲突不得猜测 |
| Look-through Concentration | IBKR权重+同日官方持仓 | 同上 | 缺数据为`DATA INCOMPLETE`；数据完整但超限为`POLICY GATE FAIL` |
| Benchmark hypothetical cash | 基准净值×15% | 每日/月度 | Benchmark为N/A |
| IBKR USD credit rate/tier | IBKR官方利率页与计息说明 | 每日或变更时 | Benchmark为N/A |
| SPYM / QQQM Total Return | 管理人官方绩效与分红 | 每月 | Benchmark为N/A |

Policy Benchmark现金模型官方来源：

- https://www.interactivebrokers.com/en/accounts/fees/pricing-interest-rates.php
- https://investors.interactivebrokers.com/en/pricing/pricing-calculations-int.php

实际账户利息只能用于实际组合归因，不得作为15%假设现金袖套的收益率代理。

数据失败必须局部化；穿透失败只关闭相关Alpha追加，不自动卖出现有仓位。
