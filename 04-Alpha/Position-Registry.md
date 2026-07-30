# Alpha Position Registry

本文件是当前 Alpha 分类、阶段和生命周期的唯一登记表。数量、市值和实际权重以 IBKR Positions 为准。

## 当前登记

| 标的 | 分类 | 生命周期 | 长期上限 | 当前阶段 | 当前授权 |
|---|---|---|---:|---:|---|
| SOXX | Alpha；唯一半导体载体 | Frozen — DATA GATE | 15% | 6% | 仅持有；当前不得作为追加候选 |

## 阶段治理

- 3%与4.5%为当前6%阶段内的执行检查点，不改变 `A_stage=6%`。
- 超过6%前，每笔追加仍须完整IC。
- 6%→10%→12.5%→15%必须逐级通过季度审核，并在任何交易前更新本表。
- 阶段推进不因价格触发自动发生。
- 科技50%冻结线、半导体15%IC线、发行人护栏和数据完整性优先。
- 任何其他Alpha或半导体个股当前新增授权为0%。

## 生命周期与交易顺序

1. 当前状态为`Frozen — DATA GATE`：允许持有，禁止追加。
2. 只有现行NYSE Semiconductor Index方法证据、实时IBKR与同日穿透均通过，且治理复核同意形成真实候选后，才能先更新本表为`Approved / Add Candidate`。
3. `Approved / Add Candidate`仍不授权交易；必须另行完成完整IC并取得`APPROVE`。
4. IC批准只允许进入账户所有者人工下单；执行后按实际状态更新为`Approved / Hold`或重新`Frozen`。

## 当前冻结原因

截至v3.4.1发布，核心投资逻辑已记录，但现行NYSE Semiconductor Index完整方法证据、实时IBKR账户读取与SPYM/QQQM/SOXX同日穿透快照均未形成完整Production Packet。因此状态保持`Frozen / ADD FROZEN`；发布本身不授权交易。

分类生效日：2026-07-30。v3.4阶段政策生效日：2026-07-30。v3.4.1生命周期勘误生效日：2026-07-30。
