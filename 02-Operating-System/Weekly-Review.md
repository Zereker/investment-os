# Weekly Review Workflow

周度复盘确认系统运行质量，不创造交易信号。

## 输入

- 本周Daily Review
- 复盘时重新读取的IBKR四项实时数据
- 最新有效的同日ETF穿透快照
- Position Registry与Transition Dashboard

## 检查

- Cash、SPYM、QQQM、SOXX、Legacy及订单完整性
- `A_actual`、`A_stage`、`A_basis`、`U`计算
- Dashboard是否正确区分`F`与`D`
- 阶段储备是否被错误部署到Core或重复计入
- SOXX是否仍符合当前阶段、Thesis和数据状态
- 科技、半导体、发行人、覆盖率与未分类暴露
- Policy Benchmark现金模型输入是否完整

## 输出

只允许：

- `NO ACTION`
- `MONTHLY INPUT`
- `IC REVIEW`
- `DATA FIX`

SOXX处于`Approved / Frozen — DATA GATE`本身不产生买入候选。只有实时数据、同日穿透和完整IC均通过，才可进入人工交易流程。
