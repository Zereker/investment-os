# Daily Review Workflow

每日复盘记录事实，不创造策略或订单。

## 数据

依次实时读取IBKR Account Summary、Balances、Positions、Open Orders。任一失败即`DATA INCOMPLETE`，不得使用旧快照填充。

## 配置输出

- Cash
- SPYM、QQQM
- SOXX：`Alpha / Approved / Frozen — DATA GATE`
- Legacy
- `A_actual`、`A_stage`、`A_basis`、`U`
- 物理现金目标`15%+U`
- SPYM目标`57%-A_basis`

阶段储备是现金用途标签，不得与现金重复求和。

## 风险检查

- 融资、订单冲突、异常数量
- SOXX是否超过当前6%阶段或15%硬上限
- 是否出现未经IC批准的SOXX追加
- 已有合格快照时检查科技、半导体和发行人护栏

没有当前穿透快照不在日报中猜测；它只使SOXX继续`ADD FROZEN`。

## Production Decision

只允许`HOLD`、`REVIEW`、`BUY CANDIDATE`、`SELL CANDIDATE`。候选仍须相应交易闸门；日报不等于下单授权。
