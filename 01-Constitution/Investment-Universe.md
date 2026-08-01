# Production Investment Universe

## 1. Current Production Scope

Investment OS 当前只管理三个可购买标的：

- `SPYM` — 核心广谱股票配置；
- `QQQM` — 战略成长配置；
- `SOXX` — 唯一自主行业倾斜。

现金是资金状态和风险缓冲，不是第四个投资标的。

## 2. Closed Universe Rule

Production 是封闭投资宇宙。除 SPYM、QQQM、SOXX 外：

- 不进入每日购买候选；
- 不参与目标缺口计算；
- 不因新闻、热度、模型推荐或临时观点进入 Production；
- 不与三个生产标的进行机会排序；
- 只可作为 Legacy、异常持仓或 Research 对象被披露。

系统每天回答的不是“市场上什么值得买”，而是：

> SPYM、QQQM、SOXX 中，今天是否有标的获得现行规则授权？

## 3. Treatment of Other Holdings

实时账户中出现其他证券时：

1. 必须在日报中单独列为 `Legacy / Out-of-Universe`；
2. 不得静默并入 SPYM、QQQM 或 SOXX；
3. 不得自动产生新增购买候选；
4. 卖出、换仓或处置必须进入完整人工审查或既有转型规则；
5. 无法识别的持仓使账户健康至少为 `WARN`，必要时为 `DATA INCOMPLETE`。

## 4. Admission of a New Asset

新增第四个生产标的必须依次完成：

```text
Research → written proposal → owner approval → Constitution change
→ Operating System update → executable checks → version release
```

任何 AI、脚本、日报或临时会话都无权自行扩展投资宇宙。

## 5. Daily Decision Boundary

日报的购买结论只允许以下三种标的标签：

- `BUY CANDIDATE — SPYM`
- `BUY CANDIDATE — QQQM`
- `BUY CANDIDATE — SOXX`

若没有符合条件的标的，输出 `HOLD`、`WAIT` 或 `DATA INCOMPLETE`，不得为了产生动作而引入其他证券。

## 6. Privacy

本文件只定义公共政策范围，不保存真实持仓、金额、数量、成本或交易记录。实际账户中是否持有其他资产，只能在受信任的运行时中读取和处理。
