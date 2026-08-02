# Investment Daily Report Contract

## 1. Purpose

`Investment Daily Report` 是 Investment OS 的主要日常产品。它把可信的运行时数据映射到现行生产规则，帮助账户所有者理解当天发生了什么、哪些动作获得授权、哪些风险需要注意，以及下一观察条件是什么。

日报成功的标准不是产生交易，而是产生一个完整、可解释、可复核的结论。`HOLD` 是正常且完整的结果。

## 2. Preconditions

必须依次取得并验证：

1. IBKR Account Summary；
2. IBKR Balances；
3. IBKR Positions；
4. IBKR Open Orders；
5. SPYM、QQQM、SOXX 所需的当前市场价格；
6. SPYM 历史最高收盘与当前回撤序列；
7. 无法从价格推导的运行时状态，例如本回撤周期已执行档位。

任何关键输入缺失、过期、币种不明或相互冲突时：

- 报告仍应说明已知事实；
- `Account Health` 标记为 `DATA INCOMPLETE`；
- 停止产生新的 `BUY CANDIDATE` 或 `SELL CANDIDATE`；
- 明确列出缺失项和恢复条件。

## 3. Decision Pipeline

日报严格遵循：

```text
Observe → Understand → Decide → Monitor
```

不得把市场叙事、临时估值、新闻观点或 Research 中未发布的规则插入该流水线。

## 4. Required Output

### A. Executive Summary

最多五行，回答：

- 今日总状态；
- 是否存在需要立即关注的账户或订单问题；
- 是否存在规则授权的动作候选；
- 最重要的下一观察条件。

### B. Account Health

至少包含：

- 数据时间和时区；
- 四项 IBKR 输入是否成功；
- 净值、现金与持仓合计是否可核对；
- 是否存在负现金、融资、异常币种或无法解释差异；
- 总状态：`PASS / WARN / DATA INCOMPLETE`。

真实金额只在当前私有会话中显示，永不写入仓库。

### C. What Happened

只陈述事实：

- 主要标的当日价格变化；
- Daily P&L；
- 持仓数量变化；
- 现金变化；
- 新增、取消或成交订单；
- 与上一有效巡检相比的显著变化。

无法取得上一有效状态时，明确写 `N/A`，不得猜测变化原因。

### D. Portfolio Allocation

列出 Cash、SPYM、QQQM、SOXX、Legacy 和无法分类持仓：

- 当前权重；
- 动态目标或允许区间；
- 正缺口、超配或漂移状态；
- 对应规则含义。

事实权重与策略解释必须分开呈现。

### E. Open Orders

列出所有活跃订单并检查：

- 与今日候选是否重复；
- 是否方向冲突；
- 是否可能击穿现金边界；
- 是否过期、部分成交或无法解释；
- 是否需要先处理订单再考虑新动作。

### F. Risk Check

至少检查：

- SPYM 相对历史最高收盘回撤 `DD`；
- T1/T2/T3/T4 是否触发、是否已执行；
- 现金常态区间与危机授权下限；
- SOXX 实际权重、执行上限和永久硬上限；
- 未经授权的新标的；
- 集中度或穿透核查是否过期；
- 融资、负现金和订单冲突。

### G. Decision Eligibility

先按资金通道分类，再判断候选：

- 月度新增投入 `D`；
- 战略现金迁移 `B`；
- 回撤部署；
- SOXX 回补至目标；
- 完整 IC 路径。

每个候选必须说明：

1. 标的；
2. 授权资金通道；
3. 触发事实；
4. 适用规则；
5. 最大允许范围；
6. 阻止执行的条件；
7. 买入后需要重新核对的项目。

日报不得给出可直接提交的订单数量、限价或自动交易指令。

### H. Production Decision

只使用以下词表：

- `HOLD`：数据与规则正常，但没有新动作；
- `WAIT`：方向可能成立，但触发条件尚未满足；
- `BUY CANDIDATE`：现行规则授权进入人工确认；
- `SELL CANDIDATE`：现行规则授权进入完整人工审查；
- `REVIEW`：需要非例行人工或 IC 审查；
- `REJECT`：规则明确不允许；
- `DATA INCOMPLETE`：关键数据不足，停止新建议。

结论后必须有一段不超过五行的解释，不得只输出标签。

### I. Attention Items

按严重程度列出：

- 今天必须处理；
- 本周需要确认；
- 仅观察。

没有事项时明确写 `None`。

### J. Next Observation Conditions

必须给出具体、可验证的下一条件，例如：

- SPYM 达到下一回撤档位；
- 月度资金实际到账；
- 某标的出现正缺口；
- 现金回到常态区间；
- 未完成订单成交或取消；
- 当季穿透核查完成；
- 缺失数据恢复。

不得使用“继续关注市场”等不可验证表述。

## 5. Fact / Interpretation / Decision Separation

每项关键结论应按以下结构表达：

```text
Fact: 可验证数据或计算结果
Interpretation: 现行规则下的含义
Decision: 受控词表结论
Monitor: 下一观察条件
```

预测和推测必须明确标记，且不得作为生产动作授权依据。

## 6. Privacy and Retention

日报中的真实账户数据只存在于受信任的私有运行时或当前私有会话中。

禁止：

- 自动提交日报到公开仓库；
- 把真实日报作为 fixture、截图、Issue 或 PR 附件；
- 在调试日志中持久化账户数据；
- 用真实账户数据制作示例。

需要测试时，只能使用明确标记、不可反推真实账户的 synthetic 数据。

## 7. Human Boundary

`BUY CANDIDATE` 和 `SELL CANDIDATE` 不是订单。账户所有者必须在 IBKR 中重新确认：

- 标的和方向；
- 当前价格；
- 订单类型与有效期；
- 数量与现金缓冲；
- 是否存在重复订单；
- 交易后权重和现金。

Investment OS 永不替代该确认。
