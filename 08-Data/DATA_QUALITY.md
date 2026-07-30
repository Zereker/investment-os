# Data Quality Gate

## Green

来源已登记、字段定义和日期明确、在刷新周期内且无冲突。SOXX追加要求IBKR四项账户数据实时Green，并要求SPYM/QQQM/SOXX同日最新官方持仓及映射Green。

## Yellow

备用源、轻微过期或口径限制。可以展示，不得单独触发SOXX交易或阶段推进。

## Red

缺失、解析失败、口径不明、来源冲突、截图/聚合页作为唯一来源，或旧数据冒充当前数据。

- IBKR账户Red：关闭全部交易路径。
- 穿透Red：SOXX `ADD FROZEN`。
- Policy Benchmark现金模型任一日Red：当期基准`N/A / DATA INCOMPLETE`，不得静默使用0%。
- 估值Red：Core战术加速T=0，不阻塞合格D与B。

## SOXX快照最低要求

- `observed_at`与各基金`source_as_of`
- 实时账户净值和SOXX权重
- SPYM、QQQM、SOXX官方持仓
- 发行人/行业映射版本
- 科技、半导体、单一发行人、覆盖率、未分类权重
- 护栏上下界与交易后模拟

未满足最低要求，不得把Research中的估算穿透升级为Production事实。
