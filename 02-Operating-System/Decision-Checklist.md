# 交易前决策清单（Investment Committee Packet）

战术加速、SOXX 追加、阶段推进、卖出、换仓或规则例外，必须在下单前完成本清单。月度公式化 Core 操作走例行路径。

## 0. Data Gate

- [ ] IBKR Account Summary、Balances、Positions、Open Orders 均实时读取成功
- [ ] 标的价格、币种、数量、时间戳和订单冲突已确认
- [ ] SPYM、QQQM、SOXX 使用同日最新官方持仓
- [ ] 发行人、科技、半导体、覆盖率和未分类暴露通过数据质量闸门

任一项失败，SOXX 结论只能为 `DATA INCOMPLETE / STOP`。

## 1. 交易提案

- 标的、方向、金额、订单类型、限价和有效期：
- 交易前后 `A_actual`：
- 当前 `A_stage`、交易后是否仍不超过该阶段：
- `A_basis`、`U`、SPYM动态目标和现金用途：
- 交易后 Cash / QQQM / SPYM / SOXX / Legacy 权重：
- 为什么现在行动优于 HOLD：
- 为什么等额 SPYM / QQQM 不是更好选择：

## 2. 四视角审查

### CIO

- SOXX Thesis 是否仍成立？
- 本次操作是否只推进已批准阶段，而非隐含批准下一阶段？
- 三年以上预期优势及可证伪条件是什么？

### Risk

- 最坏情景对总组合的直接损失是多少？
- 是否超过 SOXX 当前阶段、15%长期硬上限或 Alpha合计15%？
- 是否触发科技45%/50%、半导体15%、发行人8%/10%？
- QQQM、SPYM 与 SOXX 的相关下跌会不会放大组合损失？
- 最强的不交易理由是什么？

### Data

- 每项关键数据的来源、口径和 `source_as_of` 是什么？
- 是否把 Research、旧快照、截图或缺失值当成 Production 事实？
- “已知暴露 + 未分类暴露”是否可能越线？

### Execution

- 是否存在重复或冲突订单？
- 下单后物理现金是否至少为 `12%+U_post`？
- 阶段储备是否只按批准交易减少，没有被重复计入？
- 税费、点差、碎股和机会成本是否明确？

## 3. Hard Stops

- 数据门未通过。
- 交易后 SOXX 超过当前 `A_stage` 或15%硬上限。
- 科技穿透达到50%且本次会进一步增加科技暴露。
- 未分类暴露使任一冻结线可能被触发。
- 仅以价格、新闻、回本或害怕错过为理由。
- 需要借款。
- 无法证明优于 HOLD。

半导体穿透达到15%不是自动拒绝，但强制进行本 IC；其余 Hard Stop 仍然有效。

## 4. Verdict

只允许 `APPROVE`、`WAIT`、`REJECT`、`DATA INCOMPLETE`。`APPROVE` 只允许进入人工下单；不构成自动订单。
