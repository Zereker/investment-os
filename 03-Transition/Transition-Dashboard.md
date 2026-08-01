# Transition Dashboard

> 本文件是月度执行模板，不保存伪装成“当前”的历史账户快照。每次执行前必须重新读取 IBKR；旧数值可从 Git 历史追溯。

## 政策参数

- Cash 目标：15%（常态12%–18%；回撤档生效时下限按 Constitution 临时调整）
- QQQM 目标：28%（25%–31%）
- SOXX永久硬上限6%（`A_stage=6%`固定），当前`A_execution_cap=3%`
- `A_basis=max(A_actual,A_stage)`；`U=max(A_stage-A_actual,0)`
- SPYM目标：`57%-A_basis`
- 物理现金目标：`15%+U`
- 其他板块倾斜新增授权0%
- 每月固定新增投入（数额不入库，实际以 IBKR 到账为准）
- 战略基线计划完成月：2028-12

## 本月实时状态

- 数据日期与市场状态：待更新
- 最新账户净值 \(V\)：待更新
- 全部例行订单前现金 \(C_0\)：待更新
- 本月已到账外部净入金 \(F\)：待更新
- Routine DCA前Core正缺口 \(G_0\)：待更新
- 本月Routine DCA \(D=\min(F,G_0)\)：待更新
- Routine DCA 后预计现金 \(C=C_0-D\)：待更新
- SOXX实际权重`A_actual`、`A_basis`与阶段储备`U`：待更新
- SPYM历史最高收盘回撤`DD`与档位状态（T1/T2/T3）：待更新
- 到 2028-12 剩余执行次数 \(R\)：待更新
- 战略剩余 \(S=\max(C-(15\%+U)\times V,0)\)：待更新
- Core 正缺口合计 \(G\)：待更新
- 战略基线 \(B=\min(S/R,G)\)：待更新
- 本月回撤部署金额：0 / 按档执行
- 战术加速 \(T\)：0 / 待 IC 批准

| 分类 | 实时市值 | 实时权重 | 动态目标 | 状态 |
|---|---:|---:|---:|---|
| Physical Cash | 待更新 | 待更新 | `15%+U` | 待更新 |
| 其中：SOXX Stage Reserve | 不重复计入 | `U` | `U` | 现金用途标签 |
| SPYM | 待更新 | 待更新 | `57%-A_basis` | 待更新 |
| QQQM | 待更新 | 待更新 | 28% | 待更新 |
| SOXX / 板块倾斜 | 待更新 | `A_actual` | 当前执行≤3%，硬上限6% | 按Registry |
| Legacy / Restricted | 待更新 | 待更新 | 按独立计划 | 待更新 |

## 板块倾斜状态

| 标的 | 生命周期 | 实时数量 / 市值 | 月度新增分配 | 状态 |
|---|---|---:|---:|---|
| SOXX | 按`04-Alpha/Position-Registry.md` | 从IBKR读取 | 0 | 追加须当季核查+完整IC |

本表不缓存数量；新增或退出以`04-Alpha/Position-Registry.md`和相应治理流程为准。追加闸门顺序为`当季手工穿透核查 → 实时账户读取 → 完整IC APPROVE（当日有效）→ 人工下单`。

## 四条资金通道

| 通道 | 当月金额 | 目标 | 所需闸门 |
|---|---:|---|---|
| Routine DCA | \(D=\min(F,G_0)\)；D无默认值，F取实际到账 | SPYM / QQQM正缺口 | 月度Data / Execution Gate |
| Strategic Baseline | \(B\) | 非`VERY EXPENSIVE`的SPYM / QQQM正缺口 | 月度Data / Execution Gate |
| Drawdown Deployment | 按档：`DD≥15%/25%/35%`对应下限`10/8/6%+U` | SPYM / QQQM正缺口 | 例行检查；不受估值约束；每档每周期一次 |
| Tactical Acceleration | \(T\) | `CHEAP`且通过数据质量的Core缺口 | 完整IC |

## Tactical Dashboard

| 指标 | SPYM | QQQM |
|---|---:|---:|
| 当前权重 / 动态目标 | 待更新 | 待更新 |
| 正缺口 | 待更新 | 待更新 |
| 当前价格 / `DD`与档位状态 | 待更新 | 待更新 |
| Forward P/E、口径与自身历史百分位 | 待更新 | 待更新 |
| 利率差 / 盈利增长 / 三个月预测修正 | 待更新 | 待更新 |
| 最终估值等级 / 置信度 | 待更新 | 待更新 |
| 新增资格 | `D / B / T候选 / B暂停` | `D / B / T候选 / B暂停` |

## 完成判断

- 交易后物理现金不低于现行下限（常态`12%+U`；回撤档生效时按其临时下限），且无融资。
- Routine DCA、\(B\)与回撤部署完全符合公式与档位规则。
- Red / N/A估值只令\(T=0\)；`VERY EXPENSIVE`只暂停对应标的的\(B\)。
- SOXX没有通过月度流程获得追加；任何追加只走独立完整IC。
- 预计进入 Maintenance Mode：待更新。
