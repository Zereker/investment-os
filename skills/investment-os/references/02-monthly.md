# 月度流程与部署框架（Monthly Workflow & Deployment Framework）

本文件是月度流程与三条资金通道的唯一权威。投资参数与阈值以 `00-constitution.md` 为准；冲突时以宪法为准。冷启动与回撤周期状态的重建见 `05-state.md`。

三条通道都只买正缺口，三个可购买标的同等对待。

---

## 第一部分：月度流程

### 1. Required Runtime Inputs

Account Summary；Balances；Positions；Open Orders；当前市场输入与回撤状态；本月已到账外部净入金 `F` 的权威来源。

所有输入必须来自同一受信任运行时窗口，并通过 Broker Runtime 的来源、能力、新鲜度、币种和一致性检查。

### 2. Mandatory Pre-Calculation Gates

任何部署公式运行前必须依次通过：

1. **Capability Gate**：任务所需能力必须可用；
2. **Freshness Gate**：快照和市场输入在允许时间窗口内；
3. **Account Reconciliation**：NAV 与现金加持仓市值在允许容差内；
4. **Open Orders Gate**：权威订单状态必须明确为 `clear`；
5. **Contribution Gate**：本月实际外部净入金 `F` 已由权威来源确认；
6. **Drawdown State Gate**：回撤值使用小数、档位状态和已执行集合可验证；
7. **Policy Gate**：现行宪法可读取且无冲突。

任一项失败：`DATA INCOMPLETE / HOLD`，并停止新的月度候选。

### 3. Contribution `F`

`F` 只表示本月已到账的实际外部净入金，且 `F ≥ 0`。计划金额、提款、未到账资金或余额变化推断不得作为 `F`。

- 缺失 `F` 不得静默按零处理；
- 无入金月份也必须由权威来源明确确认 `0`；
- 当前 Adapter 若不支持 `cash_transactions`，必须声明 capability unavailable，Routine DCA 通道保持 `DATA INCOMPLETE`；
- 不允许用人工数字、截图或旧报告替代。

### 4. Open Orders

必须读取权威 Open Orders，判断重复、方向冲突、现金占用和未完成状态。确定性 CLI 使用 `--open-orders-status clear|conflicting|unknown`，默认 `unknown`。只有显式且权威确认 `clear` 才能继续；`unknown` 或 `conflicting` 均失败关闭。

### 5. Account Reconciliation

统一调用 `skills/investment-os/scripts/account_reconciliation.py`，验证 `NAV ≈ Cash + Σ Position Market Values`。对账失败必须在任何资金公式之前停止。调用者自报 `reconciliation.status = PASS` 不能覆盖真实数字冲突。

### 6. Deterministic Calculation Order

通过所有前置闸门后：

1. 计算三个标的的当前权重、目标与正缺口；
2. 以权威 `F` 计算 Routine DCA；
3. 在 Routine DCA 后计算战略现金迁移；
4. 根据 SPYM 回撤与本周期已执行档位判断回撤部署；
5. 生成结构化结果、阻塞项和下一观察条件；
6. 仅在需要实际 Broker 操作时进入 Execution Runtime。

具体公式与阈值由 `00-constitution.md`、本文件第二部分和 `skills/investment-os/scripts/monthly_execution.py` 当前实现共同约束。

### 7. Routine Path Checks

前置闸门见第 2 节。计算完成后另须逐项确认：只涉及 Production 允许的标的和通道；金额完全由已发布公式产生；交易后现金与仓位不突破现行边界；不使用融资；订单类型、数量、价格和有效期在执行前可规范化。

任一项不满足时，结论为 `DATA INCOMPLETE`、`HOLD / STOP`，或升级完整 IC（`04-committee.md`）；不得部分绕过。

### 8. Decision and Execution Boundary

月度脚本输出的是候选与上限，不是 Broker 授权。实际执行必须满足 canonical `SKILL.md` 的单次操作授权和 read-back 要求；候选、公式结果、IC Verdict 或历史批准均不能替代该执行授权。

### 9. Output

至少包含：Rule Source 与 Runtime Source；capability 与数据门状态；Account Reconciliation；Open Orders；三个标的的当前权重、目标与正缺口；各资金通道结果；Blocking Issues；Production Decision；Execution Authority；Next Observation Conditions。

真实账户数据只在当前私有会话展示，不落盘、不提交公开仓库。

### 10. Canonical Command

```bash
python3 skills/investment-os/scripts/monthly_execution.py \
  --nav <NetLiq> --cash <TotalCash> \
  --spym <MarketValue> --qqqm <MarketValue> --soxx <MarketValue> \
  --legacy <Legacy 持仓合计> \
  --contribution <AuthoritativeF> \
  --dd <DecimalDrawdown> --dd-as-of <收盘日期> \
  --tiers-executed <none|T1|T1,T2...> \
  --open-orders-status clear
```

输入缺失、单位错误、账户不对账、订单状态未知或冲突时，CLI 必须非零退出并输出 `DATA INCOMPLETE`。

`--legacy` 是 Legacy / Out-of-Universe 持仓的市值合计。它**必须**传（有就传，没有留 0）——Legacy 也是持仓，漏掉它对账等式就不成立，账户会被永久卡住。它只进对账与披露，不产生目标、缺口或任何通道资金。

`--dd` 由会话从 IBKR 收盘序列取得后传入，脚本自身不联网；必须同时传 `--dd-as-of`，否则无法确认新鲜度，本月不评估分档。

### 11. Completion Conditions

所有前置数据门有明确结论；阻塞项没有被文案隐藏；候选与执行权限明确分离；若执行，已完成 read-back verification；真实账户状态未写入仓库。

---

## 第二部分：部署框架

### 1. 战略现金迁移基线

在每个固定月度执行日，用实时账户数据定义：

- \(F\)：本月已到账的实际外部净入金，且 \(F\ge0\)；提款或未到账计划额不得计入（计划数额不入库）；
- \(V\)：\(F\) 到账后、交易前的账户净值；
- \(C_0\)：包含 \(F\)、全部例行订单前的投资组合现金；
- \(G_0\)：按宪法目标权重计算的三个可购买标的 Routine DCA 前正缺口合计；
- \(D_{max}=\min(F,G_0)\)：Routine DCA 上限；\(D\le D_{max}\) 是实际买入额，只受正缺口、现金下限与执行检查约束；
- \(C=C_0-D\)：执行 Routine DCA 后的预计现金；
- \(G\)：分配 \(D\) 后的剩余正缺口合计；
- \(R=3\)：战略剩余的固定迁移期数——每月部署剩余的三分之一，不倒计时、不记账，剩余额逐月几何衰减，任何一个月都不会塌缩成一次性下注；
- \(S=\max(C-15\%\times V,0)\)：扣除结构性现金后的战略剩余。

当月战略迁移基线：

\[
B=\min\left(\frac{S}{R},G\right)
\]

每月用最新数据重算，不沿用旧金额。基线必须同时满足：交易后物理现金不为负（不使用融资）；资金只进入正缺口；Data Gate、订单冲突和执行检查通过。现金水位本身不需要额外闸门——`B ≤ S` 与 `D ≤ F` 已在结构上保证例行路径不会把现金推到 15% 目标之下（见 `00-constitution.md`「现金的两条线」）。

`B` 由上式完全决定，没有任何可以暂停它的判断性闸门。

### 2. 回撤部署

档位、触发线、梯度定额与绝对下限以 `00-constitution.md` 分档表为唯一权威。

1. 每日巡检记录 SPYM 收盘价相对历史最高收盘价的回撤 `DD` 与当前回撤周期状态。
2. 本次部署额 = \(\min\bigl(\sum_{j\in K} w_j\times V,\ \max(C,0),\ \text{正缺口合计}\bigr)\)，其中 \(K\) 是本次新触发且本周期未执行的档集合，\(w_j\) 是该档的梯度定额。
3. 每档在同一回撤周期内最多执行一次；SPYM 创出新的历史最高收盘价后周期重置，所有档位恢复可用。
4. 单日可同时满足多档，按由浅到深顺序逐档执行，仍受「每档一次」限制。
5. 部署只进入正缺口，优先缺口更大者；分批限价执行。
6. 检查项：实时四项 IBKR 数据、无融资、无重复/冲突订单、订单细节明确。部署只由 `DD` 达档触发，不引入任何其他判断项。
7. 下单量必须为整股，且**含佣金在内**交易后现金不得为负；若下单会使现金为负，减量至现金 ≥ 0。现金归零后的后续费用、汇兑或分红时点差由所有者以外部入金补足，**不得转为融资借款**。
8. 每次执行在当前私有会话报告 `DD`、档位、部署额、订单细节、交易后权重与现金；账户与成交事实以券商记录为准，不写入仓库。
9. 现金此后仅以外部新增资金逐月重建至 15%；不得为重建现金卖出持仓，也不得因此暂停 Routine DCA。
10. `DD` 超过最深档后没有可解锁的档位，正确输出是「弹药已尽，无动作」——不是寻找规则例外，也不是借款加仓。

到档执行、不到档不执行。继续下跌不追加档外部署，反弹不撤销既定档位纪律。

**首次真实触发时**，除按上述步骤执行外，还必须在当前私有会话核验 `05-state.md` 的档位重建过程本身是否给出了正确档位——该步骤依赖 IBKR 成交、现金与警报指针，无法离线验证。

**与再平衡的分工**：某只标的单独回撤而 SPYM 未达档时，正确结论是「由再平衡吸收」，不得因单一标的跌幅另行创造部署理由——那属于规则例外，须走完整 IC。

### 3. 价格的职责

当前价格用于计算市值、仓位、缺口和订单数量；历史最高收盘回撤驱动回撤部署分档，并辅助限价与分批时点。系统不持有任何估值判断，没有任何资金通道以估值等级为条件。

### 4. 资金方向

按宪法目标权重分别计算 SPYM / QQQM / SOXX 的正缺口。\(D\)、\(B\) 与回撤部署优先流向正缺口更大的标的；可按缺口比例分配或只买缺口最大的 1–2 项。三个标的同等对待。

### 5. 执行约束

- 下跌本身不是买入理由；回撤部署的理由是「到档」。
- 不预测最低点，不得把多档合并成一笔判断性下注。
- 弹药在 `DD` 25% 处按设计打光。此后继续下跌时不得临时创造新档、不得借款。
- **波动日**（VIX 最后收盘 ≥ 20）优先限价单；市价单仅在流动性充足、点差极小且即时成交确有必要时使用。VIX 只影响订单类型，不改变买不买、买多少——那些仍完全由公式决定。VIX 取不到时按波动日处理（限价单更保守）。
- 每次例行执行在当前私有会话报告 \(F,V,C_0,G_0,D,C,R,S,G,B\) 和交易后权重。
- 每次回撤部署额外报告 `DD`、档位与周期状态；成交事实由券商保留。
- 买入后不因短期反弹追单，也不因继续下跌立即推翻原规则。

### 6. 月度输出格式（聊天输出，不写回仓库）

| 指标 | SPYM | QQQM | SOXX |
|---|---:|---:|---:|
| 当前价格 | 待读取 | 待读取 | 待读取 |
| 当前权重 / 目标 | 待计算 | 待计算 | 待计算 |
| 是否位于带宽内 | 待计算 | 待计算 | 不适用 |
| 正缺口 | 待计算 | 待计算 | 待计算 |
| 基线分配 | 待计算 | 待计算 | 待计算 |

月度输出同样附 `01-daily.md` 的市场背景块（同一脚本、同一围栏：只作披露，不进入任何闸门）。

另需披露：SPYM 历史最高收盘回撤 `DD` 与各档状态、\(F,V,C_0,G_0,D,C,R,S,G,B\)、回撤部署记录、现金比例与是否位于带宽内、融资借款、未完成订单，以及 Legacy / Out-of-Universe 持仓状态。

账户数字只在聊天输出，永不落盘；仓库中不保存填好数值的副本。
