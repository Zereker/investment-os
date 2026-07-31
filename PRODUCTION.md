# Investment OS v3.5.1 — Production Contract

本文件是当前生产系统的入口与执行契约。它不创造新的投资策略，只规定如何可靠地读取、验证和执行仓库中已经生效的规则。

## 1. 唯一事实来源

规则优先级保持不变：

1. `00-IPS/`
2. `01-Constitution/`
3. `02-Operating-System/`
4. `03-Transition/`
5. `05-Journal/`

发生冲突时，高优先级文件覆盖低优先级文件。聊天记录、临时分析、截图和 `Research/` 均不具有生产规则效力。当前 Alpha 分类与生命周期状态记录在 `04-Alpha/Position-Registry.md`；它不得覆盖 Constitution 的上限。

## 2. 生产冻结

v3.5期间：

- 允许修复数据读取、计算、文档歧义和流程遗漏等缺陷。
- 不允许在交易执行过程中临时增加指标、改变阈值或更换估值口径。
- 策略变更必须进入 `Research/`，经过独立研究、书面提案和明确批准后，才能作为新版本发布。
- 常规规则只在年度审核窗口审议；紧急修复仅限于防止明显错误或违反 IPS。

## 2.1 SOXX v3.4.2冻结规则

- SOXX是唯一Alpha载体，长期硬上限与最终治理阶段15%，当前阶段6%。
- 定义\(A_{basis}=\max(A_{actual},A_{stage})\)、\(U=\max(A_{stage}-A_{actual},0)\)；SPYM目标为\(57\%-A_{basis}\)，物理现金目标为\(15\%+U\)。
- 当前`A_execution_cap=3%`；执行上限按3%→4.5%→6%→10%→12.5%→15%逐档推进，且不得高于`A_stage`。10%/12.5%/15%还须逐级季度批准；风险护栏、现行指数方法证据、实时IBKR和Green穿透优先；本版本不产生订单。
- 每个PR必须通过`Policy consistency`检查；检查失败时不得合并为Production。
- 穿透Green证据必须符合`08-Data/LOOKTHROUGH_PACKET.md`并通过`validate_lookthrough_packet.py`；验证通过不改变Registry、不创建候选或授权订单。

## 3. 每日巡检契约

每日巡检必须按以下顺序执行：

1. 从 IBKR 读取 Account Summary。
2. 从 IBKR 读取 Balances。
3. 从 IBKR 读取 Positions；持仓接口是仓位数量的权威来源。
4. 从 IBKR 读取 Open Orders。
5. 检查数据时间、币种、合计差异和异常值。
6. 计算 Cash、Core、Alpha（含有真实资金的 Observation）和 Legacy 的市值与权重。
7. 为Alpha列示生命周期状态；SOXX当前为`Alpha / Frozen — DATA GATE`。
8. 检查融资、越界、未完成订单、重复订单和真正无法分类的异常持仓。
9. 仅对SPYM / QQQM / SOXX读取估值状态，并按`ETF-Valuation-Framework.md`输出新增资格；不读取ETF内部持仓来判断日常加减仓。
10. 仅依据当前生产规则输出事实、风险和动作。

若账户读取或核对失败，巡检必须标记为`DATA INCOMPLETE`，不得使用历史数据冒充实时数据，也不得给出新的BUY或SELL建议。估值数据失败只关闭战术加速`T`；Routine DCA `D`与既定战略基线`B`照常。完整格式见`02-Operating-System/Daily-Review.md`。

SOXX当前为`Alpha / Frozen — DATA GATE`：现有仓位可持有，禁止追加。只有现行指数方法证据完成、Registry先更新为`Approved / Hold`，并用实时账户与同一审核日/同`source_as_of`的Green穿透形成未过期`Add Candidate` Packet后，才可进入完整IC。

## 4. 周度与季度契约

周度复盘按 `02-Operating-System/Weekly-Review.md` 汇总本周运行质量、配置偏差、订单、数据质量和行为纪律。它只生成 `NO ACTION`、`MONTHLY INPUT`、`IC REVIEW` 或 `DATA FIX`，不得因为一周行情临时创造交易信号或修改阈值。

季度复盘按 `02-Operating-System/Quarterly-Workflow.md` 审核 Alpha Thesis、Observation 状态、相对 Policy Benchmark 的必要性和穿透集中度。超过软护栏只冻结相应新增风险或进入 IC 复核，不自动卖出。

## 5. 交易闸门

### 5.1 例行月度路径

以下操作可以使用 `02-Operating-System/Monthly-Workflow.md` 的例行路径，无需重复填写完整四视角 Packet：

- 每月固定新增投入；
- 按已发布公式计算的战略现金迁移基线；
- 资金只流向 SPYM / QQQM 的正缺口；
- 每只Core通过`ETF-Valuation-Framework.md`对应的资金权限；低质量或缺失估值不得关闭`D/B`；
- 金额、方向和交易后权重完全符合 Constitution、Transition Plan 和实时 Data Gate。

例行路径仍必须通过实时账户数据、目标缺口、现金下限、订单冲突和执行细节检查。任一条件不满足，升级为完整 IC 或 `HOLD / STOP`。

### 5.2 完整 Investment Committee 路径

任何战术加速、新 Alpha、Alpha 追加、Observation 升级、卖出、换仓、规则例外或偏离月度公式的真实资金建议，都必须先完成 `02-Operating-System/Decision-Checklist.md`，并由 CIO、Risk、Data、Execution 四个视角形成 Verdict。

#### 数据

- [ ] Account Summary 读取成功
- [ ] Balances 读取成功
- [ ] Positions 读取成功
- [ ] Open Orders 读取成功
- [ ] 标的价格和数量已确认
- [ ] 数据不存在未解释冲突

#### 规则

- [ ] 符合 IPS
- [ ] 符合 Constitution 的目标与上限
- [ ] 符合当前 Operating System
- [ ] 未使用 Research 中的实验性指标

#### 风险

- [ ] 无重复或冲突订单
- [ ] 交易后现金和仓位可接受
- [ ] 未引入未经审核的新标的
- [ ] 已陈述不交易的最强理由
- [ ] 已检查穿透集中度
- [ ] 已检查订单类型、价格、有效期和碎股影响
- [ ] 已记录明确的 `APPROVE / WAIT / REJECT / DATA INCOMPLETE` Verdict

任何一项未通过，默认结论为 `HOLD / STOP`，并明确列出失败项。Investment Committee 的批准只允许进入人工下单；账户所有者仍需在 IBKR 中亲手确认。

## 6. 数据权威顺序

- 仓位数量：IBKR Positions
- 活跃订单：IBKR Open Orders
- 现金和净值：IBKR Account Summary 与 Balances 交叉核对
- 成交记录：用于解释变化，不用于替代当前持仓
- Alpha 状态：`04-Alpha/Position-Registry.md`
- 市场、估值和 ETF 穿透数据：必须符合 `08-Data/DATA_REGISTRY.md`、`08-Data/DATA_DICTIONARY.md` 与 `08-Data/DATA_QUALITY.md`
- 三只ETF估值方法与新增动作：`02-Operating-System/ETF-Valuation-Framework.md`

外部金融数据在运行时从分别登记的专业来源读取，仓库不维护行情、ETF成分、issuer或GICS中央数据库。普通巡检不写仓库；真实决策才保存不可变证据Bundle。来源缺失或冲突时失败关闭，不得回退到陈旧中央副本冒充当前数据。

## 7. 输出标准

每日复盘只包含：

- Account Health
- Portfolio Allocation
- Open Orders
- Daily P&L 与持仓变化
- Risk Check
- Production Decision
- 下一观察条件
- SPYM / QQQM / SOXX估值等级、置信度与今日需要做什么

事实、推断和建议必须明确分开。无法验证的内容必须标记为未知。
