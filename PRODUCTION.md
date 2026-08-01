# Investment OS v4.3 — Production Contract

本文件是当前生产系统的入口与执行契约。它不创造新的投资策略，只规定如何可靠地读取、验证和执行仓库中已经生效的规则。

## 1. 唯一事实来源

规则优先级保持不变：

1. `00-IPS/`
2. `01-Constitution/`
3. `02-Operating-System/`
4. `03-Transition/`
5. `05-Journal/`

发生冲突时，高优先级文件覆盖低优先级文件。聊天记录、临时分析、截图和 `Research/` 均不具有生产规则效力。当前板块倾斜分类与生命周期状态记录在 `04-Alpha/Position-Registry.md`；它不得覆盖 Constitution 的上限。

## 2. 生产冻结

v4.x 期间：

- 允许修复数据读取、计算、文档歧义和流程遗漏等缺陷。
- 不允许在交易执行过程中临时增加指标、改变阈值或更换口径。
- 策略变更必须进入 `Research/`，经过独立研究、书面提案和明确批准后，才能作为新版本发布。
- 常规规则只在年度审核窗口审议；紧急修复仅限于防止明显错误或违反 IPS。

## 2.1 SOXX v4.0规则

- SOXX是唯一自主板块倾斜载体（行业beta，不按alpha命名）；永久硬上限6%，`A_stage=6%`固定。
- 定义\(A_{basis}=\max(A_{actual},A_{stage})\)、\(U=\max(A_{stage}-A_{actual},0)\)；SPYM目标为\(57\%-A_{basis}\)，物理现金目标为\(15\%+U\)。
- 当前`A_execution_cap=3%`；执行上限按3%→4.5%→6%逐档推进，且不得高于6%。10%/12.5%/15%历史治理阶段已作废（依据见`Research/2026-07-31-v4-Evidence-and-Proposal.md`）。
- 追加闸门：当季`08-Data/LOOKTHROUGH_CHECK.md`手工核查有效 + 实时账户读取 + 完整IC（当日有效）+ 人工下单。
- 每个PR必须通过`Policy consistency`检查；检查失败时不得合并为Production。

## 3. 每日巡检契约

每日巡检必须按以下顺序执行：

1. 从 IBKR 读取 Account Summary。
2. 从 IBKR 读取 Balances。
3. 从 IBKR 读取 Positions；持仓接口是仓位数量的权威来源。
4. 从 IBKR 读取 Open Orders。
5. 检查数据时间、币种、合计差异和异常值。
6. 计算 Cash、Core、SOXX 和 Legacy 的市值与权重。
7. 记录 SPYM 相对历史最高收盘的回撤 `DD` 与回撤档位状态；达档且本周期未执行时按 Deployment Framework 输出部署动作。
8. 检查融资、越界、未完成订单、重复订单和真正无法分类的异常持仓。
9. 读取SPYM / QQQM / SOXX价格与正缺口；系统不产生估值判断。
10. 仅依据当前生产规则输出事实、风险和动作。

若账户读取或核对失败，巡检必须标记为`DATA INCOMPLETE`，不得使用历史数据冒充实时数据，也不得给出新的BUY或SELL建议。回撤序列失败只暂停当日档位评估。完整格式见`02-Operating-System/Daily-Review.md`。

## 4. 周度与季度契约

周度复盘按 `02-Operating-System/Weekly-Review.md` 汇总本周运行质量、配置偏差、订单、数据质量和行为纪律。它只生成 `NO ACTION`、`MONTHLY INPUT`、`IC REVIEW` 或 `DATA FIX`，不得因为一周行情临时创造交易信号或修改阈值。

季度复盘按 `02-Operating-System/Quarterly-Workflow.md` 执行：先完成 `08-Data/LOOKTHROUGH_CHECK.md` 手工穿透核查并存档，再审核 SOXX 倾斜的必要性、相对 Policy Benchmark 与影子基准的表现和护栏状态。超过护栏只冻结相应新增风险或进入 IC 复核，不自动卖出。

## 5. 交易闸门

### 5.1 例行月度路径

以下操作可以使用 `02-Operating-System/Monthly-Workflow.md` 的例行路径，无需重复填写完整四视角 Packet：

- 每月固定新增投入 \(D=\min(F,G_0)\)；
- 按已发布公式计算的战略现金迁移基线 \(B\)；
- 按 Constitution 分档执行的回撤部署；
- 资金只流向 SPYM / QQQM 的正缺口；
- 金额、方向和交易后权重完全符合 Constitution、Transition Plan 和实时 Data Gate。

例行路径仍必须通过实时账户数据、目标缺口、现金下限、订单冲突和执行细节检查。任一条件不满足，升级为完整 IC 或 `HOLD / STOP`。

### 5.2 完整 Investment Committee 路径

任何 SOXX 追加、新板块倾斜、卖出、换仓、规则例外或偏离月度公式的真实资金建议，都必须先完成 `02-Operating-System/Decision-Checklist.md`，并由 CIO、Risk、Data、Execution 四个视角形成 Verdict。

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
- [ ] 已引用当季穿透核查记录
- [ ] 已检查订单类型、价格、有效期和碎股影响
- [ ] 已记录明确的 `APPROVE / WAIT / REJECT / DATA INCOMPLETE` Verdict

任何一项未通过，默认结论为 `HOLD / STOP`，并明确列出失败项。Investment Committee 的批准只允许进入人工下单；账户所有者仍需在 IBKR 中亲手确认。

## 6. 数据权威顺序

- 仓位数量：IBKR Positions
- 活跃订单：IBKR Open Orders
- 现金和净值：IBKR Account Summary 与 Balances 交叉核对
- 成交记录：用于解释变化，不用于替代当前持仓
- 板块倾斜状态：`04-Alpha/Position-Registry.md`
- 市场数据：必须符合 `08-Data/DATA_REGISTRY.md`、`08-Data/DATA_DICTIONARY.md` 与 `08-Data/DATA_QUALITY.md`
- 穿透集中度：`08-Data/LOOKTHROUGH_CHECK.md` 季度手工核查记录
- 回撤部署：Constitution 回撤部署条款 + `02-Operating-System/Deployment-Framework.md`

外部金融数据在运行时从分别登记的专业来源读取，仓库不维护行情、ETF成分、issuer或GICS中央数据库。普通巡检不写仓库；季度核查记录按只增不改原则存档。来源缺失或冲突时失败关闭，不得回退到陈旧副本冒充当前数据。

## 7. 输出标准

每日复盘只包含：

- Account Health
- Portfolio Allocation
- Open Orders
- Daily P&L 与持仓变化
- Risk Check（含 `DD` 与回撤档位状态）
- Production Decision
- 下一观察条件

事实、推断和建议必须明确分开。无法验证的内容必须标记为未知。
