# Daily Review Workflow

每日复盘的目标是客观记录账户状态、发现异常并执行现行规则，而不是临时创造新策略。

## A. 数据读取

依次读取并记录时间戳：

1. IBKR Account Summary
2. IBKR Balances
3. IBKR Positions
4. IBKR Open Orders
5. IBKR 当前启用的 SPYM 回撤警报

若任一账户接口失败，账户报告状态为 `DATA INCOMPLETE`。不得用上次快照填充“今日”账户数据。

## B. 一致性检查

- Net Liquidation 与各币种净值是否合理一致
- Cash 与 Settled Cash 是否存在重要差异
- Gross Position Value 与持仓市值合计是否接近
- Positions 与 Open Orders 是否存在数量冲突
- 是否出现零数量持仓、碎股、异常价格或重复合约
- Leverage 是否来自真实借款，还是仅表示投资比例
- 回撤警报数量、标的、字段、运算符、档位和价格是否与当前周期状态一致

### B.1 回撤警报指针不变量

每日必须从当前历史最高收盘和本周期已执行档位重建 `expected alert pointer`，不得把券商警报本身当成已执行状态的唯一证据。

1. 从足够长的 SPYM 日线窗口确认当前历史最高收盘；窗口不足以排除更早高点时继续向前扩展。
2. 按 `State-Reconstruction.md` 的三信号程序重建本周期已执行档位。
3. 使用 `python3 skills/validating-drawdown-state/scripts/alert_pointer_check.py`，比较重建出的 expected pointer 与 IBKR actual alert。
4. 未耗尽阶梯时，账户内必须恰好有一个启用警报，且满足：
   - 标的是 SPYM；
   - 字段是 `LAST`；
   - 运算符是小于等于；
   - 档位是下一个可用档；
   - 价格等于该档触发线乘以当前 ATH，允许最小报价单位误差。
5. 新 ATH 收盘意味着新周期开始：全部档位恢复可用，expected pointer 必须退回首档并按新 ATH 重算价格。
6. 阶梯全部执行后，不应存在新的启用回撤警报。

任何不一致均视为状态同步缺陷：

- `Account Health = WARN`；
- `drawdown deployment state = DATA INCOMPLETE`；
- 停止新的回撤部署候选；
- 其他独立例行资金路径是否继续，仍按其自身 Data Gate 判断；
- 报告 expected、actual、差异与人工修复条件，但不得由 agent 自动修改券商警报。

## C. 标准输出

### 1. Account Health

- Net Liquidation
- Cash / Settled Cash
- Gross Position Value
- Invested Ratio
- Cash Ratio
- Available Funds
- Margin Loan 状态
- Drawdown Alert Pointer：`PASS / WARN / DATA INCOMPLETE`

### 2. Portfolio Allocation

按以下分类汇总：

- Cash
- Core ETF：SPYM、QQQM
- 板块倾斜：SOXX，列示生命周期`Hold | Frozen | Exit Review`
- Restricted / Legacy

同时列出各持仓数量、市值、组合占比、成本和未实现盈亏。

SOXX按 Position Registry 当前生命周期列示。每日同时报告 `A_actual`、`A_stage`、`A_execution_cap`、`A_basis`、`U`（定义与阈值见 Constitution）、SPYM 相对历史最高收盘回撤 `DD` 与回撤档位状态；阶段储备属于现金用途标签，不得重复计入。

### 3. Open Orders

逐笔列出：

- 标的与方向
- 数量、已成交、剩余
- 订单类型、价格、有效期
- 状态与风险说明

没有订单时明确写 `None`。

### 4. Daily Changes

- 当日盈亏
- 新成交
- 仓位数量变化
- 现金变化

无法从接口确认时不得推测原因。

### 5. Risk Check

至少检查：

- 融资借款
- Cash、QQQM、`SPYM + SOXX + Stage Reserve`袖套
- SOXX检查当前执行上限3%与6%永久硬上限；漂移超限时确认冻结状态
- 回撤部署档位是否达标触发（`DD≥10/15/20/25%`，释放 1.5/3/4.5/6pp，四档中本周期未执行者）；`DD` 超过 25% 后无档位可解锁，输出「弹药已尽，无动作」
- 回撤警报指针是否与 expected pointer 一致；新 ATH 后是否明确退回首档
- 未完成或重复订单
- 碎股与零数量残留
- 真正未经登记的新标的
- 数据冲突

穿透集中度在季度及任何新增 Alpha 前完整计算；日报只在已有合格快照时标记已知越线，不用旧数据制造交易信号。

### 5.1 三只 ETF 价格与缺口

只监控 SPYM、QQQM、SOXX，列示当前价格、`observed_at`、当前仓位、动态目标与正缺口。SOXX 另列 Registry 当前生命周期。

v4.2 起系统不持有估值判断：价格只用于计量、执行与回撤定档，不产生贵/便宜结论，也不生成任何新增资格。

### 6. Production Decision

只允许以下结论：

- `HOLD`：无生产规则触发，或`Observation / Frozen`仅按既定状态持有
- `REVIEW`：存在异常，需要人工确认，但不直接交易
- `BUY CANDIDATE`：现行规则触发，仍需相应月度路径或完整 Trade Gate
- `SELL CANDIDATE`：现行卖出规则触发，仍需完整 Trade Gate
- `DATA INCOMPLETE`：关键账户状态或回撤部署状态无法可靠重建

每日复盘本身不等于下单授权。

### 7. Next Watch

只记录下一次需要观察的客观条件，不新增阈值或指标。警报指针异常时，下一观察条件必须包含：IBKR 中唯一启用警报与 expected pointer 完全一致。

## D. 报告纪律

- 清楚区分实时事实、计算结果、推断和建议。
- 历史快照必须标注日期。
- 研究指标只能放在独立的 Research Note，不得混入 Production Decision。
- 价格涨跌本身不产生 `SELL CANDIDATE`。
- 无操作是有效结果。
- agent 只报告警报修复要求，不自动创建、修改或删除 IBKR 警报。
