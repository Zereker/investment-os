# 月度流程

月度流程把权威 Broker Runtime 转化为结构化月度决策。它不接受旧报告、人工贴数或估算替代当前状态，也不因公式可计算就自动形成执行权限。

## 1. Required Runtime Inputs

月度任务需要：

- Account Summary；
- Balances；
- Positions；
- Open Orders；
- 当前市场输入与回撤状态；
- 当前板块倾斜登记状态；
- 本月已到账外部净入金 `F` 的权威来源；
- 当季穿透核查状态（仅在相关路径需要时）。

所有输入必须来自同一受信任运行时窗口，并通过 Broker Runtime 的来源、能力、新鲜度、币种和一致性检查。

## 2. Mandatory Pre-Calculation Gates

任何部署公式运行前必须依次通过：

1. **Capability Gate**：任务所需能力必须可用；
2. **Freshness Gate**：快照和市场输入在允许时间窗口内；
3. **Account Reconciliation**：NAV 与现金加持仓市值在允许容差内；
4. **Open Orders Gate**：权威订单状态必须明确为 `clear`；
5. **Contribution Gate**：本月实际外部净入金 `F` 已由权威来源确认；
6. **Drawdown State Gate**：回撤值使用小数、档位状态和已执行集合可验证；
7. **Policy Gate**：现行 Constitution、Transition 和倾斜状态可读取且无冲突。

任一项失败：

```text
DATA INCOMPLETE / HOLD
```

并停止新的月度候选。

## 3. Contribution `F`

`F` 只表示本月已到账的实际外部净入金，且 `F ≥ 0`。计划金额、提款、未到账资金或余额变化推断不得作为 `F`。

- 缺失 `F` 不得静默按零处理；
- 无入金月份也必须由权威来源明确确认 `0`；
- 当前 Adapter 若不支持 `cash_transactions`，必须声明 capability unavailable；
- 在 Production 正式批准其他权威路径前，不允许用人工数字、截图或旧报告替代。

因此，当 `cash_transactions` 能力不可用时，Routine DCA 通道必须保持 `DATA INCOMPLETE`。

## 4. Open Orders

月度流程必须读取权威 Open Orders，并判断重复、方向冲突、现金占用和未完成状态。

确定性 CLI 使用：

```text
--open-orders-status clear|conflicting|unknown
```

默认 `unknown`。只有显式且权威确认 `clear` 才能继续形成月度候选；`unknown` 或 `conflicting` 均失败关闭。

## 5. Account Reconciliation

统一调用 `scripts/account_reconciliation.py`，验证：

```text
NAV ≈ Cash + Σ Position Market Values
```

对账失败必须在任何资金公式之前停止。调用者自报 `reconciliation.status = PASS` 不能覆盖真实数字冲突。

## 6. Deterministic Calculation Order

通过所有前置闸门后，按现行 Constitution 与 Deployment Framework 执行：

1. 计算当前配置、动态目标、正缺口和板块倾斜状态；
2. 判断相关回补路径是否满足全部限制；
3. 以权威 `F` 计算 Routine DCA；
4. 在 Routine DCA 后计算战略现金迁移；
5. 根据 SPYM 回撤与本周期已执行档位判断回撤部署；
6. 生成结构化结果、阻塞项和下一观察条件；
7. 仅在需要实际 Broker 操作时进入 Execution Runtime。

`D`、战略迁移、回撤部署和回补的具体公式与阈值由 Constitution、Deployment Framework 和 `scripts/monthly_execution.py` 当前实现共同约束。本文不复制易变参数。

## 7. Routine Path Checks

所有例行月度候选必须同时满足：

- Broker Runtime 所需能力完整；
- 账户物理对账通过；
- `F` 权威且期间、币种明确；
- Open Orders 状态为 `clear`；
- 只涉及 Production 允许的标的和通道；
- 金额完全由已发布公式产生；
- 交易后现金与仓位不突破现行边界；
- 不使用融资；
- 不推进需要完整 IC 的风险预算；
- 订单类型、数量、价格和有效期在执行前可规范化。

任一项不满足时，结论为 `DATA INCOMPLETE`、`HOLD / STOP`，或升级完整 IC；不得部分绕过。

## 8. Decision and Execution Boundary

月度脚本输出的是候选与上限，不是 Broker 授权。

实际执行必须经过 `execution-runtime`：

- 当前会话所有者明确授权；
- 授权绑定一个完整单次操作摘要；
- capability 可用；
- 只提交一次；
- 权威 read-back；
- 验证实际 Broker 状态与授权操作一致。

候选、公式结果、IC Verdict 或历史批准均不能替代该执行授权。

## 9. Output

月度输出至少包含：

- Rule Source 与 Runtime Source；
- capability 与数据门状态；
- Account Reconciliation；
- Open Orders；
- 当前配置与正缺口；
- 各资金通道结果；
- Blocking Issues；
- Production Decision；
- Execution Authority；
- Next Observation Conditions。

真实账户数据只在当前私有会话展示，不落盘、不提交公开仓库。

## 10. Canonical Command

```bash
python3 scripts/monthly_execution.py \
  --nav <NetLiq> \
  --cash <TotalCash> \
  --spym <MarketValue> \
  --qqqm <MarketValue> \
  --soxx <MarketValue> \
  --contribution <AuthoritativeF> \
  --dd <DecimalDrawdown> \
  --tiers-executed <none|T1|T1,T2...> \
  --open-orders-status clear
```

只有当当季穿透核查有效且相关路径需要时才传 `--lookthrough-current`。

输入缺失、单位错误、账户不对账、订单状态未知或冲突时，CLI 必须非零退出并输出 `DATA INCOMPLETE`。

## 11. Completion Conditions

月度流程只有在以下条件满足时才算完成：

- 所有前置数据门有明确结论；
- 机器计算与现行规则一致；
- 阻塞项没有被文案隐藏；
- 候选与执行权限明确分离；
- 无操作时输出完整 `HOLD`；
- 若执行，已完成 read-back verification；
- 真实账户状态未写入仓库。


## 12. 回补与提高倾斜

`--lookthrough-current` 只证明相关当季核查有效，不创造风险预算。**回补至目标**必须保持现行执行上限不变；任何推进执行上限或扩大预算的行为都属于**提高倾斜**，必须进入完整 IC。
