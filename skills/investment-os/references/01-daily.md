# 每日复盘与日报（Daily Review & Report）

本文件是每日流程的唯一权威。投资参数与阈值以 `00-constitution.md` 为准；冲突时以宪法为准。冷启动与回撤周期状态的重建见 `05-state.md`。

`HOLD` 是正常且完整的结果。成功的标准不是产生交易，而是产生一个完整、可解释、可复核的结论。

## A. 数据读取（Preconditions）

只读取当前判断路径实际需要的账户与市场能力，并分别记录来源和 `observed_at`。不可用能力表示为 `null`，不得伪装成 `0`、空对象或空数组；只有接口成功后，空订单或空现金活动才是事实。

关键输入缺失、过期、币种不明或冲突时，继续报告不受影响的已知事实，将受影响的路径标记为 `DATA INCOMPLETE`，停止该路径的新交易候选，并说明最小恢复条件。不得用旧快照填充「今日」状态。

## B. 一致性检查

- Net Liquidation 与各币种净值是否合理一致
- Cash 与 Settled Cash 是否存在重要差异
- Gross Position Value 与持仓市值合计是否接近
- Positions 与 Open Orders 是否存在数量冲突
- 是否出现零数量持仓、碎股、异常价格或重复合约
- Leverage 是否来自真实借款，还是仅表示投资比例
- 是否存在可绕过 Production universe 的常驻券商自动化；发现时只报告并阻断，不自动修改

## C. 判断与输出

按 `Observe → Understand → Decide → Monitor` 判断，不得把市场叙事、临时估值、新闻观点或未发布研究当作生产规则。

输出只使用 canonical `SKILL.md` 定义的 `Portfolio`、`Change`、`Decision`、`Reason`、`Next Trigger` 五个字段。没有动作时 `HOLD` 是完整结果；数据问题只阻断受影响的路径。日报不得给出可直接提交的订单参数或交易指令。

下一观察条件必须客观、具体、可验证，不得写「继续关注市场」。

## D. 事实与报告纪律

- 预测和推测必须明确标记，且不得作为生产动作授权依据。
- 清楚区分实时事实、计算结果、推断和建议。
- 历史快照必须标注日期。
- 研究指标只能放在独立的 Research Note，不得混入 Production Decision。
- 价格涨跌本身不产生 `SELL CANDIDATE`。
- 无操作是有效结果。

## E. Privacy and Retention

日报中的真实账户数据只存在于受信任的私有运行时或当前私有会话中。禁止：自动提交日报到公开仓库；把真实日报作为 fixture、截图、Issue 或 PR 附件；在调试日志中持久化账户数据；用真实账户数据制作示例。

需要测试时，只能使用明确标记、不可反推真实账户的 synthetic 数据。

## F. Human Boundary

`BUY CANDIDATE` 和 `SELL CANDIDATE` 不是订单。账户所有者必须在 IBKR 中重新确认：标的和方向；当前价格；订单类型与有效期；数量与现金缓冲；是否存在重复订单；交易后权重和现金。

Investment OS 永不替代该确认。
