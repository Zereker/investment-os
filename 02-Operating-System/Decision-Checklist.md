# 交易前决策清单（Investment Committee Packet）

任何战术加速、新 Alpha、Alpha 追加、Observation 升级、卖出、换仓、规则例外或偏离月度公式的真实资金操作，都必须在下单前完成本清单。不得在成交后补写理由。

完全符合 `Monthly-Workflow.md` 的固定投入与战略现金迁移基线走例行路径；一旦偏离公式、标的或上限，立即升级为本清单。

## 0. Data Gate

- [ ] IBKR Account Summary 读取成功
- [ ] IBKR Balances 读取成功
- [ ] IBKR Positions 读取成功
- [ ] IBKR Open Orders 读取成功
- [ ] 标的价格、币种、数量和时间戳已确认
- [ ] 账户接口之间不存在未解释冲突
- [ ] 依赖的市场、估值和穿透字段通过 `08-Data/DATA_QUALITY.md`
- [ ] SPYM / QQQM / SOXX估值仅按`ETF-Valuation-Framework.md`的同口径数据判定，未把绝对P/E横向比较当作贵便宜

任一项失败，结论只能是 `DATA INCOMPLETE / STOP`。

## 1. 交易提案

- 标的、分类、生命周期与方向：
- 数量 / 金额：
- 订单类型、限价、有效期：
- 交易后 Cash / QQQM / SPYM / Alpha / Legacy 权重：
- 交易后`A_actual`与`SPYM + SOXX + Stage Reserve`袖套权重：
- 本次操作解决的组合问题：
- 为什么现在必须行动，而不是继续持有或等待：
- Forward P/E、自身历史百分位、利率差、盈利增长/修正、最终等级与置信度：
- 本次新增是否符合`D / B / T`动作映射；若为卖出，确认估值贵不是唯一理由：
- 为什么直接持有/买入 SPYM 或 QQQM 不是更好的选择：

## 1.1 SOXX v3.4.1必填

- 交易前后`A_actual`、当前`A_stage`、当前`A_execution_cap`、`A_basis`与`U`：
- 确认执行上限只推进一档，且不是在本次IC中临时修改：
- 交易后SPYM动态目标和物理现金目标：
- 现行NYSE Semiconductor Index方法证据与核验日期：
- Registry是否仍为`Approved / Hold`：
- Add Candidate Packet的`approved_as_of`、账户/价格`data_as_of`、`expires_at`、`max_notional`、`max_post_trade_weight`：
- SPYM、QQQM、SOXX的`lookthrough_observed_at`、各自`source_as_of`与覆盖率；是否满足Green：
- 阶段、执行上限与科技50%、半导体15%、发行人10%边界：

## 2. Investment Committee 四视角审查

### CIO：组合与长期逻辑

- 是否让组合更接近 IPS 与动态目标配置？
- 能否用三句话说明三年以上的投资逻辑？
- 什么证据会证明判断错误？
- 若市场关闭五年，是否仍愿意持有？
- 若为 Observation 升级，完整 Thesis 是否已经存在？

### Risk：反方与组合损害

- 最强的不交易理由是什么？
- 最坏情景对总组合的美元和百分比影响是多少？
- 是否突破Cash、Alpha合计15%；SOXX是否超过当前阶段或长期15%，其他单一Alpha是否超过6%？
- 与 SPYM、QQQM 及现有 Alpha 的穿透重复暴露是多少？
- 是否触发科技 45% / 50%、半导体 15%、单一发行人 8% / 10%软护栏？
- 是否引入杠杆、流动性或永久性资本损害风险？

### Data：事实与可复现性

- 每个关键数据的来源、口径和时间戳是什么？
- 数据质量是 Green、Yellow 还是 Red？
- 是否把 Research 假设、截图、旧快照或代理值当成 Production 事实？
- 若删除某一项不确定数据，结论是否仍成立？

### Execution：订单与执行风险

- 是否存在重复、冲突或尚未完成的订单？
- 限价、数量、有效期和碎股处理是否明确？
- 税费、点差和机会成本是多少？
- 下单后是否仍保留现金下限、下一期基线和意外情况所需流动性？

## 3. Hard Stops

以下任一项成立，默认拒绝或等待：

- 理由只有价格、新闻、害怕错过、回本愿望或“想做点什么”。
- 使用了尚未发布的 Research 指标或规则。
- 新Alpha会使一般单只超过6%、持仓超过5只或Alpha合计超过15%；SOXX交易后超过Registry当前执行上限、当前阶段或长期15%。
- Observation没有完成Thesis与升级批准却申请追加；Registry不是`Approved / Hold`，或缺少仍有效的独立`Add Candidate` Packet就申请追加。
- `A_execution_cap`跳档、在本次IC中临时提高，或高于`A_stage`。
- Candidate已到`expires_at`/当日收盘，或Positions、Open Orders、Settled Cash、NAV、价格、持仓源版本/质量已变化。
- 三只ETF并非同一审核日读取最新官方持仓，或`source_as_of`不一致而未达到Green。
- 新科技 Alpha 会让科技穿透达到或超过 50%，且没有年度规则批准。
- 需要借款，或在没有 Transition Plan 依据时突破现金约束。
- 标的不在现行 Core / Alpha / Legacy 分类中，且未完成准入研究。
- 没有写出可证伪条件、最强反方观点或交易后权重。
- Data Gate 未通过。
- 仅因`EXPENSIVE / VERY EXPENSIVE`申请卖出，或用Trailing P/E把SOXX判定为便宜。
- 无法证明这笔操作优于 `HOLD`。

## 4. Verdict 与执行

只允许以下结论：

- `APPROVE`：全部闸门通过，可以进入人工下单。
- `WAIT`：逻辑可能成立，但触发条件、数据、生命周期或价格尚未满足。
- `REJECT`：违反现行规则或风险回报不足。
- `DATA INCOMPLETE`：数据不足，禁止新 BUY / SELL。

最终下单由账户所有者在 IBKR 中亲手确认。非例行决定必须先写入 `Decision-Log.md` 或 `05-Journal/Investment-Journal.md`；每日复盘或 Investment Committee 的结论都不等于自动下单授权。
