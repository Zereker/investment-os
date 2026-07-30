# Data Dictionary

## 通用

- `observed_at`：读取时间，ISO8601
- `source_as_of`：发布方数据日期
- `source_name`、`source_url`
- `quality`：Green / Yellow / Red
- `notes`

## v3.4配置字段

### alpha_actual_weight

`A_actual=SOXX实时市值/net_liquidation_usd`。v3.4其他Alpha新增授权为0；若账户出现其他Alpha，仍计入15%总硬上限并触发REVIEW。

### alpha_stage_cap

`A_stage`，由Position Registry发布。当前为6%。不得从聊天、价格或计划表推导。

### alpha_allocation_basis

`A_basis=max(A_actual,A_stage)`，用于SPYM目标：

\[
W_{SPYM,target}=57\%-A_{basis}
\]

### soxx_stage_reserve_weight

\[
U=\max(A_{stage}-A_{actual},0)
\]

阶段储备是物理现金的用途标签，不得作为额外资产重复求和。

### physical_cash_target_weight

`15%+U`；允许区间为`12%+U`至`18%+U`。

## 月度执行字段

- `F`：已到账外部净入金。
- `G0`：按QQQM 28%和SPYM动态目标计算的Routine前Core正缺口。
- `D=min(F,G0)`：实际Core买入；`F-D`留在现金。
- `C=C0-D`。
- `G`：执行D后Core剩余正缺口。
- `S=max(C-(15%+U)×V,0)`。
- `B=min(S/R,G)`。

## Policy Benchmark现金字段

### benchmark_nav_usd / benchmark_cash_balance_usd

每日假设基准净值 `V_B,d`；假设现金余额：

\[
C_{B,d}=15\%\times V_{B,d}
\]

### ibkr_usd_full_rate / ibkr_nav_scale

`r_full,d`为当日适用账户计划的IBKR官方USD信用利率。NAV低于100,000美元时：

\[
k_d=\min(V_{B,d}/100000,1)
\]

### benchmark_eligible_cash_usd

按IBKR当前公开规则，USD前10,000美元不计息：

\[
E_{B,d}=\max(C_{B,d}-10000,0)
\]

若账户计划、币种、Segment或门槛不同，必须按当日官方规则重算并记录。

### benchmark_cash_interest_usd / benchmark_cash_period_return

USD通常按360天：

\[
I_{B,t}=\sum_d E_{B,d}\times r_{full,d}\times k_d/360
\]

\[
r^{model}_{cash,t}=I_{B,t}/\bar C_{B,t}
\]

其中分母为同期假设现金的期限加权平均值。任一输入缺失时结果为`N/A`，不得以实际账户利息或0%替代。

## ETF穿透

- `portfolio_position_weight=w_p`
- `fund_holding_weight=h_{p,i}`
- ETF底层贡献 `x_{p,i}=w_p×h_{p,i}`
- 直接持仓贡献 `x_i=w_i`
- `issuer_group_id`合并同一经济发行人
- `technology_lookthrough_weight`汇总Information Technology
- `semiconductor_lookthrough_weight`汇总Semiconductors & Semiconductor Equipment
- `unclassified_lookthrough_weight`保留未分类贡献

若“已知暴露+未分类暴露”可能越过护栏，相关SOXX结论必须为`WAIT / DATA INCOMPLETE`。

缺失值使用`N/A`，不得写0或重新归一。
