# Reliability Bug Log

本日志记录会影响真实账户决策可靠性的缺陷。每个缺陷都必须包含：事件、影响、根因、修复和防复发控制。

## BUG-001：用成交记录推导当前仓位

- 日期：2026-07
- 事件：未先读取 IBKR Positions，尝试通过历史交易重建持仓。
- 影响：可能遗漏旧持仓、碎股、公司行动或非同步成交，导致仓位判断错误。
- 根因：没有固定数据权威顺序。
- 修复：将 IBKR Positions 定义为当前仓位数量的唯一权威来源；成交记录仅用于解释变化。
- 防复发：每日巡检和交易闸门必须先读取 Positions。
- 状态：Closed

## BUG-002：在生产交易过程中临时修改规则

- 日期：2026-07-29
- 事件：在已经依据回撤执行加仓后，又临时引入不同 PE 口径和新的评分解释。
- 影响：规则不可重复，可能诱发追认交易、反复调仓和决策漂移。
- 根因：Production 与 Research 未隔离；缺少规则冻结。
- 修复：增加 `PRODUCTION.md` 与 `Research/`；研究结论未经版本发布不得影响真实交易。
- 防复发：交易闸门必须确认未使用实验性规则；策略变更只通过正式版本升级。
- 状态：Closed

## BUG-003：每日巡检未主动调用已连接的 IBKR

- 日期：2026-07-29
- 事件：错误地声称无法获取 IBKR 数据，而没有先调用已连接的数据源。
- 影响：使用历史快照代替实时状态，可能遗漏成交、订单和仓位变化。
- 根因：没有强制化的巡检调用顺序。
- 修复：每日巡检第一阶段固定读取 Account Summary、Balances、Positions、Open Orders。
- 防复发：任一数据调用未完成时，报告必须标记 `DATA INCOMPLETE`，不得给出交易建议。
- 状态：Closed

## BUG-004：未在建议前完成反方审查

- 日期：2026-07
- 事件：部分建议先给结论，再补充不交易或数据冲突理由。
- 影响：容易产生确认偏误，忽略重复订单、估值口径和仓位约束。
- 根因：缺少交易前强制审查清单。
- 修复：在交易闸门中加入“最强反对理由”和订单细节检查。
- 防复发：任何未通过项均默认 `HOLD / STOP`。
- 状态：Closed

## BUG-005：Core 标的命名与运行入口不一致

- 日期：2026-07-30
- 事件：Constitution 已使用 SPYM / QQQM，但 Decision Checklist 和 Alpha Framework 仍残留 SPY / QQQ；周度流程与 Investment Committee 入口也未从 Production 明确链接。
- 影响：可能在真实资金审查时选错交易载体，或跳过已经确认的运行控制。
- 根因：v3.2 迁移完成了策略文件，但没有做跨文件一致性验收。
- 修复：统一现行 Core 名称为 SPYM / QQQM；将 Decision Checklist 升级为 Investment Committee Packet；增加 Weekly Review 并从 Production 与 README 链接。
- 防复发：每次版本发布检查 Core 名称、目标权重、数据源、运行入口和 Release Note 的跨文件一致性。
- 状态：Closed

## 新缺陷模板

```markdown
## BUG-XXX：标题

- 日期：YYYY-MM-DD
- 事件：
- 影响：
- 根因：
- 修复：
- 防复发：
- 状态：Open / Monitoring / Closed
```
