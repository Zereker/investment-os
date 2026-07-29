# Investment OS v3.2 LTS — Production Contract

本文件是当前生产系统的入口与执行契约。它不创造新的投资策略，只规定如何可靠地读取、验证和执行仓库中已经生效的规则。

## 1. 唯一事实来源

规则优先级保持不变：

1. `00-IPS/`
2. `01-Constitution/`
3. `02-Operating-System/`
4. `03-Transition/`
5. `05-Journal/`

发生冲突时，高优先级文件覆盖低优先级文件。聊天记录、临时分析、截图和 `Research/` 均不具有生产规则效力。

## 2. 生产冻结

v3.2 LTS 期间：

- 允许修复数据读取、计算、文档歧义和流程遗漏等缺陷。
- 不允许在交易执行过程中临时增加指标、改变阈值或更换估值口径。
- 策略变更必须进入 `Research/`，经过独立研究、书面提案和明确批准后，才能作为新版本发布。
- 常规规则只在年度审核窗口审议；紧急修复仅限于防止明显错误或违反 IPS。

## 3. 每日巡检契约

每日巡检必须按以下顺序执行：

1. 从 IBKR 读取 Account Summary。
2. 从 IBKR 读取 Balances。
3. 从 IBKR 读取 Positions；持仓接口是仓位数量的权威来源。
4. 从 IBKR 读取 Open Orders。
5. 检查数据时间、币种、合计差异和异常值。
6. 计算现金、Core、Alpha、Legacy 的市值与权重。
7. 检查融资、越界、未完成订单、重复订单和异常持仓。
8. 仅依据当前生产规则输出事实、风险和动作。

若第 1–5 步任一失败，巡检必须标记为 `DATA INCOMPLETE`，不得使用历史数据冒充实时数据，也不得给出新的 BUY 或 SELL 建议。完整格式见 `02-Operating-System/Daily-Review.md`。

## 4. 周度复盘契约

周度复盘按 `02-Operating-System/Weekly-Review.md` 汇总本周运行质量、配置偏差、订单、数据质量和行为纪律。它只生成 `NO ACTION`、`MONTHLY INPUT`、`IC REVIEW` 或 `DATA FIX`，不得因为一周行情临时创造交易信号或修改阈值。

## 5. 交易闸门

任何真实资金交易建议必须先完成 `02-Operating-System/Decision-Checklist.md`，并由 CIO、Risk、Data、Execution 四个视角形成 Investment Committee Verdict。

### 数据

- [ ] Account Summary 读取成功
- [ ] Balances 读取成功
- [ ] Positions 读取成功
- [ ] Open Orders 读取成功
- [ ] 标的价格和数量已确认
- [ ] 数据不存在未解释冲突

### 规则

- [ ] 符合 IPS
- [ ] 符合 Constitution 的目标与上限
- [ ] 符合当前 Operating System
- [ ] 未使用 Research 中的实验性指标

### 风险

- [ ] 无重复或冲突订单
- [ ] 交易后现金和仓位可接受
- [ ] 未引入未经审核的新标的
- [ ] 已陈述不交易的最强理由
- [ ] 已检查订单类型、价格、有效期和碎股影响
- [ ] 已记录明确的 `APPROVE / WAIT / REJECT / DATA INCOMPLETE` Verdict

任何一项未通过，默认结论为 `HOLD / STOP`，并明确列出失败项。Investment Committee 的批准只允许进入人工下单；账户所有者仍需在 IBKR 中亲手确认。

## 6. 数据权威顺序

- 仓位数量：IBKR Positions
- 活跃订单：IBKR Open Orders
- 现金和净值：IBKR Account Summary 与 Balances 交叉核对
- 成交记录：用于解释变化，不用于替代当前持仓
- 市场与估值数据：必须符合 `08-Data/DATA_REGISTRY.md` 与 `08-Data/DATA_QUALITY.md`

## 7. 输出标准

每日复盘只包含：

- Account Health
- Portfolio Allocation
- Open Orders
- Daily P&L 与持仓变化
- Risk Check
- Production Decision
- 下一观察条件

事实、推断和建议必须明确分开。无法验证的内容必须标记为未知。
