# Satellite / Sector Tilt Framework（原 Alpha Framework）

v4.0 起本目录治理的对象改称**自主板块倾斜（Sector Tilt / Satellite）**。SOXX 是一只被动行业 ETF：持有它是有硬上限的行业/周期 beta，不是 alpha。旧「Alpha」一词在历史文件中保留，不再用于现行规则。目录名 `04-Alpha/` 保持不变以维持链接稳定。

## 边界

- 合计硬上限：总组合 6%（v4.0 起与 SOXX 上限合并；10%/12.5%/15% 历史阶段作废）。
- 持仓数：最多 1 只（SOXX）；任何新增载体必须先通过年度审核修改本规则。
- 不使用杠杆，不用短线技术信号建立长期仓位。
- 已批准但未完成的 SOXX 额度按 `U` 保留为现金用途标签。
- 当前分类与状态的唯一登记表为 `04-Alpha/Position-Registry.md`。

## SOXX 唯一载体

SOXX 是唯一自主倾斜载体；永久硬上限 6%，当前 `A_execution_cap=3%`。执行上限只能按 3%→4.5%→6% 逐档推进且每次一档。任何半导体个股（MU、TSM 等）与 SOXX 共用同一 6% 预算；其当前新增授权为 0%。

封顶依据（2026-07 实测）：SOXX=6% 时组合合并半导体暴露已约 24%、SOXX=15% 时约 32%，后者在系统自身护栏下不可达。证据见 `Research/2026-07-31-v4-Evidence-and-Proposal.md`。

## 追加标准

SOXX 追加必须同时满足：

- 完成季度手工穿透核查（`08-Data/LOOKTHROUGH_CHECK.md`），且核查记录在当季有效；
- 半导体护栏已触发的事实在 IC 中显式确认（当前 Core 结构性半导体暴露约 18%）；
- 追加后 `A_actual` 不超过当前执行档；
- 与 QQQM / SPYM 的重复暴露有明确书面补偿理由；
- 实时四项 IBKR 数据读取成功、无冲突订单；
- 在下单前完成 `02-Operating-System/Decision-Checklist.md` 并获得 `APPROVE` Verdict。

不再要求机器验证的 Look-through Evidence Bundle；季度核查表 + 完整 IC 是现行闸门。

## 持仓生命周期

1. `Research`：仅研究、没有真实资金，不计入\(A\)。
2. `Hold`：允许按当前仓位持有，没有新增授权。
3. `Frozen`：允许持有、禁止追加（数据、护栏或研究条件不足）。
4. `Exit Review`：满足卖出规则，进入完整IC；状态本身不等于卖出授权。

生命周期与 `A_execution_cap` 变化必须先更新 Position Registry。任何状态不因价格、研究完成或数据可得自动改变。

## 穿透集中度

执行 Constitution 的穿透集中度护栏（护栏约束自主倾斜新增，不阻断 Core 例行路径）。季度手工核查计算合并暴露并存档；核查缺失时 SOXX 保持禁止追加，不自动卖出。

## 评价

SOXX 必须与等额同期 SPYM 及 IPS 的 Policy Benchmark 比较。至少使用滚动三年数据，并纳入回撤、税费、时间成本与集中度；单年跑赢不证明可复制能力。若连续五年在成本后跑输，年度审核应讨论清退本倾斜并简化系统。
