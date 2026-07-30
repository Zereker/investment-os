# Alpha Framework

v3.4将Alpha总硬上限保持在15%，但Production只授权SOXX作为唯一战略Alpha载体；15%是长期上限与最终治理阶段，不是立即买入目标。`Observation`仍保留为一般生命周期状态。

## 边界

- 合计硬上限：总组合 15%。
- 持仓数：最多 5 只。
- 一般单只硬上限：6%；SOXX适用15%长期硬上限与当前6%阶段例外，后续阶段须逐级批准。
- 有真实资金的 Observation 按全部市值计入合计上限、持仓数和单只上限。
- 不使用杠杆，不用短线技术信号建立长期仓位。
- 一般未授权Alpha额度留在SPYM；已批准但未完成的SOXX当前阶段差额按`U`保留为现金用途标签。
- 当前分类与状态的唯一登记表为 `04-Alpha/Position-Registry.md`。

## v3.4 SOXX唯一载体

SOXX是唯一Production Alpha；长期硬上限与最终治理阶段15%，当前`A_stage=6%`，当前`A_execution_cap=3%`。执行上限只能按3%→4.5%→6%→10%→12.5%→15%逐档推进且不得高于阶段；10%/12.5%/15%还须逐级季度批准。其他Alpha新增授权为0%；半导体个股与SOXX共用同一预算。

## 准入与追加标准

新建或追加 Alpha 必须同时满足：

- 能清楚解释长期商业优势、行业结构或价值创造机制。
- 有三年以上的投资逻辑与可证伪条件。
- 预期回报明显优于直接持有 SPYM / QQQM。
- 最坏情景对总组合的影响可接受。
- 研究信息足够，不属于主题跟随或能力圈外交易。
- 与现有 QQQM 和其他 Alpha 的重复暴露有明确补偿。
- 穿透集中度数据通过 Data Gate。
- 在下单前完成 `02-Operating-System/Decision-Checklist.md` 并获得 `APPROVE` Verdict。

## 持仓生命周期

1. `Research`：仅研究、没有真实资金，不计入\(A\)。
2. `Observation`：已有小额真实仓位但Thesis或准入尚未完成；全额计入\(A\)，默认允许持有、冻结追加。
3. `Approved / Hold`：Thesis与长期准入完整，允许按当前仓位持有，但没有新增授权。
4. `Frozen`：逻辑尚可但研究证据、数据、权重或集中度条件不足，允许持有、禁止追加。
5. `Exit Review`：满足卖出规则，进入完整IC；状态本身不等于卖出授权。

`Add Candidate`是短时效交易Packet状态，不是Position Registry的持久生命周期。SOXX当前顺序固定为：`Frozen → Approved / Hold → 有时效Add Candidate Packet → IC APPROVE → 账户所有者人工下单 → Approved / Hold或Frozen`。Packet必须绑定账户/价格/穿透时间戳、过期时间、最大金额和交易后权重；当日收盘或依赖状态变化即失效。任何一步不得跳过；Data Gate通过本身不会自动改变Registry、执行上限或授权交易。

生命周期、`A_stage`和`A_execution_cap`变化必须先更新Position Registry。`Observation`不自动升级为`Approved`，也不因治理文件尚未完成而自动卖出。

## 穿透集中度

执行 Constitution 的穿透集中度护栏。新增 Alpha 必须使用最新合格的基金官方持仓和行业数据；软护栏限制新增风险，不自动卖出，也不单独阻断例行 SPYM / QQQM Core 维护。

## 评价

Alpha 必须同时和 SPYM、QQQM 及 IPS 的 Policy Benchmark 比较。至少使用滚动三年数据，并纳入回撤、税费、时间成本与集中度；单年跑赢不证明可复制能力。
