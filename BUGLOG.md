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
- 事件：首次修复后仍在 Transition Plan、Quarterly Workflow、Alpha Research、Journal 与旧 Assistant 模板残留现行 SPY / QQQ 或冲突输出；v3.2 LTS 的一致性验收过早关闭。
- 影响：可能在真实资金审查时选错交易载体，或使用非权威输出状态。
- 根因：只检查已知文件，没有进行全仓角色化扫描并区分历史 / 代理引用与现行执行引用。
- 修复：v3.3 统一现行交易载体为 SPYM / QQQM；旧 Assistant 模板降级为权威流程链接；历史 Release、Decision Log 和数据代理语境保留并显式标注。
- 防复发：每次发布扫描裸 SPY / QQQ，并对历史、数据代理、防切换说明建立白名单；核对全部入口和模板。
- 状态：Closed

## BUG-006：Alpha 配置数学回归

- 日期：2026-07-30
- 事件：Constitution 同时规定 Alpha 10%–15%、固定 SPYM 42%，又允许 Alpha 不填满。
- 影响：Alpha 为 0 时无法得到合计 100%的合法目标，可能诱发强制填满或错误再平衡。
- 根因：v3.2 固定表格覆盖了 v3.1 已确定的机会预算语义。
- 修复：Alpha 改为 \(A\in[0,15\%]\)，`SPYM + Alpha = 57%`，`SPYM = 57%−A`。
- 防复发：发布测试必须覆盖 \(A=0\%、5\%、15\%\) 并验证合计 100%。
- 状态：Closed

## BUG-007：估值数据死锁战略转型

- 日期：2026-07-30
- 事件：历史超额现金全部依赖 PE 历史百分位，但该字段在 Data Registry 中为 Red。
- 影响：系统会安全地长期不部署现金，与 2026–2028 转型目标冲突。
- 根因：战略迁移和战术择机共用同一评分闸门，Liquidity 同时被当成买入信号。
- 修复：拆分固定投入、战略基线 \(B\) 和战术加速 \(T\)；估值 Red 只令 \(T=0\)，Liquidity 只限制金额。
- 防复发：数据失败必须标明受影响路径，不允许局部 Red 关闭无关的例行流程。
- 状态：Closed

## BUG-008：Observation 与当前 Alpha 名单缺失

- 日期：2026-07-30
- 事件：SOXX 已是实际观察仓，但 Production 没有 Observation 生命周期，Alpha Framework 仍列已过时的 MU / TSM / GOOG 候选。
- 影响：SOXX 会被误判为 Legacy / 异常，或绕过 Alpha 风险预算；旧候选可能误导未来资金。
- 根因：没有独立的 Alpha 状态登记表，聊天确认未进入生产规则。
- 修复：建立 Position Registry；SOXX 登记为 `Alpha / Observation / HOLD / ADD FROZEN`；删除旧候选基线。
- 防复发：IBKR 出现未登记非 Core 持仓时先 REVIEW；所有生命周期变更同步更新 Registry。
- 状态：Closed

## BUG-009：例行月度路径与完整 IC 冲突

- 日期：2026-07-30
- 事件：Production 要求所有真实资金交易走完整 IC，而 Checklist 又允许固定月度流程走简化检查。
- 影响：同一笔 DCA 可能被同时视为允许与禁止，无法稳定执行。
- 根因：没有按 Routine、Strategic、Tactical / Alpha 划分资金通道。
- 修复：固定投入与公式化战略基线走月度 Data / Execution Gate；战术加速、全部 Alpha 动作、卖出与例外走完整 IC。
- 防复发：每次发布交叉校验 Production、Monthly Workflow 和 Decision Checklist 的交易范围。
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
