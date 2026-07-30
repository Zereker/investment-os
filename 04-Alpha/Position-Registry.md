# Alpha Position Registry

本文件是当前Alpha分类、治理阶段、执行上限和持久生命周期的唯一登记表。数量、市值和实际权重以IBKR Positions为准；短时效交易候选不得持久化为Registry生命周期。

## 当前登记

| 标的 | 分类 | 持久生命周期 | 长期上限 | 当前阶段 \(A_{stage}\) | 当前执行上限 \(A_{execution\_cap}\) | 当前授权 |
|---|---|---|---:|---:|---:|---|
| SOXX | Alpha；唯一半导体载体 | Frozen — DATA GATE | 15% | 6% | 3% | 仅持有；当前不得形成追加候选 |

## 阶段与执行上限治理

- 当前\(A_{stage}=6\%\)，当前\(A_{execution\_cap}=3\%\)。
- 治理阶段合法集合为6%、10%、12.5%、15%；执行上限合法顺序为3%→4.5%→6%→10%→12.5%→15%。
- 每次只允许推进一个执行档，必须先更新本表，随后另行形成候选和完成IC；同一次IC不得既跳档又执行交易。
- 3%→4.5%→6%是当前6%阶段内检查点；6%→10%→12.5%→15%还必须逐级通过季度阶段审核。
- 始终要求\(A_{execution\_cap}\le A_{stage}\)。交易后`A_actual`不得超过执行上限、当前阶段或长期15%中的任何一项。
- 若价格漂移使`A_actual`超过执行上限或阶段，冻结新增但不自动卖出。
- 阶段或执行上限不因价格、Data Gate通过或IC结论自动推进。
- 科技50%冻结线、半导体15%IC线、发行人护栏和数据完整性优先。
- 任何其他Alpha或半导体个股当前新增授权为0%。

## 持久生命周期与临时候选

1. 当前状态为`Frozen — DATA GATE`：允许持有，禁止追加。
2. 只有现行NYSE Semiconductor Index方法证据与长期准入治理完成后，才能把本表更新为`Approved / Hold`；该状态仍没有新增授权。
3. 每次潜在追加必须创建独立、短时效的`Add Candidate` IC Packet，而不是把`Add Candidate`写入本表。Packet必须记录`approved_as_of`、账户与价格`data_as_of`、三只ETF的`lookthrough_observed_at`和各自`source_as_of`、`expires_at`、`max_notional`及`max_post_trade_weight`。
4. 三只ETF必须在同一审核日读取最新官方持仓；`source_as_of`完全一致才为Green。相差不超过一个交易日为Yellow，超过一个交易日或缺失为Red；SOXX新增只接受Green。
5. Packet只可在美股常规交易时段内批准，最迟于当日常规收盘失效。Positions、Open Orders、Settled Cash、NAV、基金官方持仓版本或数据质量发生变化，或价格变化会使上限/护栏失守时，立即提前失效。
6. 只有Registry仍为`Approved / Hold`、Packet仍有效且完整IC取得`APPROVE`，才能进入账户所有者人工下单。成交、部分成交、撤单或到期后，候选立即关闭并重新读取账户。

## 当前冻结原因

截至v3.4.1发布，核心投资逻辑已记录，但现行NYSE Semiconductor Index完整方法证据、实时IBKR账户读取与SPYM/QQQM/SOXX同审核日且同`source_as_of`的Green穿透快照均未形成完整Production Packet。因此状态保持`Frozen / ADD FROZEN`；发布本身不授权交易。

分类生效日：2026-07-30。v3.4阶段政策生效日：2026-07-30。v3.4.1可靠性勘误生效日：2026-07-30。
