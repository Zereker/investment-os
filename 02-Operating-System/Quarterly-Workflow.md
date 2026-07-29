# 季度流程

季度审核只处理 Alpha / Observation 的必要性、穿透集中度和组合级风险，不重新设计 Core，也不因一次涨跌修改 Constitution。

## 输入

- 实时 IBKR Positions 与账户净值
- `04-Alpha/Position-Registry.md`
- 每只 Approved Alpha 的完整 Thesis
- Observation 的研究进度与证据缺口
- SPYM、QQQM 和全部 Alpha 的官方持仓 / 行业快照
- 组合与 IPS Policy Benchmark 的季度及滚动三年数据

## 每只 Alpha 必答

1. 当前生命周期是否准确？
2. 原始投资逻辑是否仍成立；若为 Observation，Thesis 哪些部分仍未完成？
3. 哪项证据最可能证明判断错误？
4. 未来三年的预期回报是否仍明显优于直接持有 SPYM / QQQM？
5. 个股的商业质量，或 ETF 的指数方法、集中度、费用、流动性和周期性，是否支持继续持有？
6. 与 SPYM、QQQM 和其他 Alpha 的穿透重复暴露是否有明确补偿？
7. 当前权重是否符合单只 6%、Alpha 合计 15%和最多 5 只硬上限？

## 生命周期输出

每只标的只给出一种状态：

- `Observation`：继续计入风险预算并允许持有，但追加冻结；完成 Thesis 与准入审查后才可申请升级。
- `Approved / Hold`：逻辑有效，权重合理。
- `Approved / Add Candidate`：逻辑有效且低于已批准目标；仍须在交易前取得完整 IC `APPROVE`。
- `Frozen`：继续持有，但不追加。
- `Exit Review`：触发 Constitution 卖出规则，先记录证据、税务和执行影响，再进入完整 IC。

Observation 身份本身不是退出触发器，也不能成为先买后补研究的常规通道。

## 组合级检查

- Alpha 相对其所替代的等额 SPYM，以及整体组合相对 Policy Benchmark 的季度及滚动三年表现。
- 最大回撤、税费、研究时间和复杂度成本。
- 信息技术穿透是否超过 45%预警或达到 50%新增科技 Alpha 冻结线。
- 半导体及设备是否达到 15% IC 复核线。
- 单一发行人是否超过 8%预警或达到 10%年度强制审核线。
- 官方穿透数据是否合格；缺失时冻结新的重叠 Alpha，而不是猜测。

若 Alpha 连续五年在风险、税费和时间成本后跑输 Policy Benchmark，年度审核应讨论降低 Alpha 上限。超过软护栏只限制新增风险或触发复核，不自动卖出。
