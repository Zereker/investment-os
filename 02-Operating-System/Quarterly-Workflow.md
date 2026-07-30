# 季度流程

季度审核处理 SOXX Thesis、阶段资格、穿透集中度和组合级风险。

## 输入

- 实时 IBKR Positions 与净值
- Position Registry 与 SOXX Thesis
- SPYM、QQQM、SOXX 同日最新官方持仓
- 发行人、行业、半导体、覆盖率与未分类暴露
- SOXX 相对等额 SPYM 及组合相对 Policy Benchmark 的表现

## 必答

1. Thesis 与可证伪条件是否仍成立？
2. ETF 的指数方法、费用、流动性、集中度和周期性是否仍可接受？
3. `A_actual` 是否低于当前 `A_stage`？
4. 当前阶段内的追加是否通过完整 IC？
5. 是否有充分证据把 `A_stage` 从6%推进到10%、12.5%或15%？
6. 科技50%、半导体15%、发行人10%和未分类暴露是否阻止推进？
7. 最坏情景及与 QQQM/SPYM 的相关损失是否可接受？

## 输出

- `Approved / Hold`
- `Approved / Add Candidate`：仍须逐笔完整IC
- `Frozen`
- `Exit Review`
- `Stage Advance Proposal`

阶段推进必须在交易前更新 Position Registry 和 Decision Log。价格上涨或下跌不构成推进依据。

## 风险优先级

- 科技达到50%且新增会提高科技暴露：冻结。
- 半导体达到15%：每次新增强制IC。
- 单一发行人达到10%且新增会提高该发行人：冻结。
- 数据或覆盖率不足：`DATA INCOMPLETE`。

以上护栏优先于15%长期目标；超线不自动卖出。
