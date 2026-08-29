# 每日复盘与日报（Daily Review & Report）

本文件是每日流程的唯一权威。投资参数与阈值以 `00-constitution.md` 为准；冲突时以宪法为准。冷启动与回撤周期状态的重建见 `05-state.md`。

`HOLD` 是正常且完整的结果。成功的标准不是产生交易，而是产生一个完整、可解释、可复核的结论。

## A. 数据读取（Preconditions）

只读取当前判断路径实际需要的账户与市场能力，并分别记录来源和 `observed_at`。不可用能力表示为 `null`，不得伪装成 `0`、空对象或空数组；只有接口成功后，空订单、空警报或空现金活动才是事实。

关键输入缺失、过期、币种不明或冲突时，继续报告不受影响的已知事实，将受影响的路径标记为 `DATA INCOMPLETE`，停止该路径的新交易候选，并说明最小恢复条件。不得用旧快照填充「今日」状态。

## B. 一致性检查

- Net Liquidation 与各币种净值是否合理一致
- Cash 与 Settled Cash 是否存在重要差异
- Gross Position Value 与持仓市值合计是否接近
- Positions 与 Open Orders 是否存在数量冲突
- 是否出现零数量持仓、碎股、异常价格或重复合约
- Leverage 是否来自真实借款，还是仅表示投资比例
- 回撤警报数量、标的、字段、运算符、档位和价格是否与当前周期状态一致
- 是否存在可绕过 Production universe 的常驻券商自动化；发现时只报告并阻断，不自动修改

### B.1 回撤警报指针每日核对

指针的完整不变量见 `05-state.md`，本节只规定每日动作：

1. 按 `05-state.md` 重建当前历史最高收盘与本周期已执行档位；
2. 运行 `python3 skills/investment-os/scripts/alert_pointer_check.py`，比较重建出的 expected pointer 与 IBKR actual alert；
3. 不得把券商警报本身当成已执行状态的证据。

任何不一致：`Account Health = WARN`、`drawdown deployment state = DATA INCOMPLETE`、停止新的回撤部署候选；其他例行资金路径按其自身 Data Gate 判断。报告 expected、actual、差异与人工修复条件，不得由 agent 自动修改券商警报。

## C. 判断与输出

按 `Observe → Understand → Decide → Monitor` 判断，不得把市场叙事、临时估值、新闻观点或未发布研究当作生产规则。

输出只使用 canonical `SKILL.md` 定义的 `Portfolio`、`Change`、`Decision`、`Reason`、`Next Trigger` 五个字段。没有动作时 `HOLD` 是完整结果；数据问题只阻断受影响的路径。日报不得给出可直接提交的订单参数或交易指令。

下一观察条件必须客观、具体、可验证，不得写「继续关注市场」。警报指针异常时，恢复条件是 IBKR 中唯一启用警报与 expected pointer 完全一致。

### C.1 市场背景块

五个字段之后附一块市场背景：

```bash
python3 skills/investment-os/scripts/market_context.py \
  --spym-series <日收盘 JSON> --vix-close <收盘> --vix-as-of <日期>
```

脚本自己取数并缩减（CNN 接口约 177KB，只取其中一个对象），取不到就打印「缺（原因）」。

**这一块只作披露。** 它的任何字段都不得出现在 `Decision` 或 `Reason` 里，也不得作为改变结论的理由 —— 没有任何资金通道、缺口或档位以它为条件（宪法决策原则 7）。唯一的例外是 VIX 对订单类型的影响，见 `02-monthly.md` 执行约束。

PE 必须连同口径一起报（如 `29.72（GAAP，multpl）`）；不同口径的数不得比较，也不得混算分位。

## D. 事实与报告纪律

- 预测和推测必须明确标记，且不得作为生产动作授权依据。
- 清楚区分实时事实、计算结果、推断和建议。
- 历史快照必须标注日期。
- 研究指标只能放在独立的 Research Note，不得混入 Production Decision。
- 价格涨跌本身不产生 `SELL CANDIDATE`。
- 无操作是有效结果。
- agent 只报告警报修复要求，不自动创建、修改或删除 IBKR 警报。

## E. Privacy and Retention

日报中的真实账户数据只存在于受信任的私有运行时或当前私有会话中。禁止：自动提交日报到公开仓库；把真实日报作为 fixture、截图、Issue 或 PR 附件；在调试日志中持久化账户数据；用真实账户数据制作示例。

需要测试时，只能使用明确标记、不可反推真实账户的 synthetic 数据。

## F. Human Boundary

`BUY CANDIDATE` 和 `SELL CANDIDATE` 不是订单。账户所有者必须在 IBKR 中重新确认：标的和方向；当前价格；订单类型与有效期；数量与现金缓冲；是否存在重复订单；交易后权重和现金。

Investment OS 永不替代该确认。
