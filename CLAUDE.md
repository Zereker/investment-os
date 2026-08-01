# AI 执行手册（CLAUDE.md）

本仓库是一套**由 AI 执行的个人投资操作系统**（当前 v4.0）。你（AI）的职责是按已发布规则读取数据、计算、报告和把关——**永远不下单**；下单只能由账户所有者在 IBKR 人工完成。

## 30 秒理解系统

- 目标配置：现金 15% ｜ QQQM 28% ｜ SPYM `57%−A_basis` ｜ SOXX（半导体板块倾斜）硬上限 6%。
- `A_basis=max(A_actual, 6%)`，`U=max(6%−A_actual, 0)` 是现金里的 SOXX 用途标签。
- 规则优先级：`00-IPS` → `01-Constitution` → `02-Operating-System` → `03-Transition` → `05-Journal`。冲突时高层覆盖低层;聊天记录与 `Research/` 无规则效力。
- 三条铁律：数据缺失 = `DATA INCOMPLETE`（停止建议,不猜);估值贵不卖出;护栏触发只冻结新增、不自动卖出。

## 例行任务入口

| 任务 | 流程文件 | 要点 |
|---|---|---|
| 每日巡检 | `02-Operating-System/Daily-Review.md` | 先实时读 IBKR 四项(Account Summary/Balances/Positions/Open Orders);记录 SPYM 相对历史高点回撤 `DD` 与档位状态 |
| 周度复盘 | `02-Operating-System/Weekly-Review.md` | 只产出 `NO ACTION / MONTHLY INPUT / IC REVIEW / DATA FIX` |
| 月度执行 | `02-Operating-System/Monthly-Workflow.md` | `D=min(F,G0)`;`B=min(S/R,G)`;回撤达档执行部署;估值只影响 `B/T` |
| 季度审核 | `02-Operating-System/Quarterly-Workflow.md` | 第一步做穿透核查(见下),再审 SOXX 与护栏 |
| 非例行交易 | `02-Operating-System/Decision-Checklist.md` | 完整 IC 四视角;任一失败 = `HOLD / STOP` |

## 如何查询 ETF 数据（穿透核查）

```bash
# 一条命令拿到三只 ETF 持仓 + 合并穿透 + 护栏对照(约10秒):
python3 scripts/fetch_etf_data.py --scenario current
# 用实际权重(从 IBKR 读取后填入):
python3 scripts/fetch_etf_data.py --weights spym=0.49,qqqm=0.20,soxx=0.078,cash=0.232
# 生成可粘贴到 08-Data/SNAPSHOTS/ 的核查快照:
python3 scripts/fetch_etf_data.py --scenario current --markdown
```

数据层次（本沙箱 2026-07-31 实测）：

1. **SPYM**：SSGA 官方 xlsx 直接下载,全量持仓,Green。脚本自动处理。
2. **QQQM / SOXX**：`stockanalysis.com` 聚合页,前 25 大,Yellow。iShares/Invesco 官方页拦截无头抓取(403/406)——需要 Green 质量时,用你的网页抓取工具访问官方页交叉核对,或让所有者浏览器确认。
3. **yfinance**：标准 Python 库答案(`yf.Ticker("SOXX").funds_data` 提供 sector_weightings/top_holdings),但**本沙箱网络层不可用**(curl_cffi TLS 与代理冲突);不要在此环境反复尝试。
4. IT 行业合并值：脚本持仓表不含行业列,按 `08-Data/LOOKTHROUGH_CHECK.md` 第 2 步用官方行业表手工加权(SSGA/Invesco/iShares 产品页各一个数字)。

依赖:`pip install openpyxl`(requests 标准环境已有;脚本其余为标准库)。

解读规则:脚本输出「已知下界 + 未覆盖尾部」;若已知值未越线但加上尾部可能越线,倾斜新增结论必须为 `WAIT / DATA INCOMPLETE`(定义见 `08-Data/DATA_DICTIONARY.md`)。

## 验证与 CI

```bash
python3 scripts/check_policy_consistency.py   # 提交前必须本地通过
```

每个 PR 由 `.github/workflows/policy-consistency.yml` 强制执行同一检查。改规则文档时,同步更新该脚本的断言——它是规则的可执行镜像。

## 已知结构性事实（2026-07 实测,勿重复惊讶）

- Core 自身(51% SPYM + 28% QQQM)合并半导体暴露约 18%,**恒定高于 15% 护栏线**——这是指数结构事实,护栏因此只约束 SOXX 等自主倾斜的新增,不阻断 Core 例行路径。
- SOXX 实际权重可能漂移超过 6% 上限:处理方式是冻结新增、不自动卖出、每日披露。
- QQQM Forward P/E 等估值字段长期 Red:这**不阻塞** `D/B`,只关闭战术加速 `T`。
- 完整证据:`Research/2026-07-31-v4-Evidence-and-Proposal.md`。

## 红线（违反即 BUG）

1. 不下单、不生成可直接执行的订单指令;结论只能是 `HOLD / REVIEW / BUY CANDIDATE / SELL CANDIDATE` 等既定词表。
2. 不用历史快照冒充实时账户数据;IBKR Positions 是持仓数量唯一权威。
3. 不在执行过程中临时改阈值、换口径、引入 Research 指标。
4. 数据拿不到就写 `N/A` 并标 `DATA INCOMPLETE`,不估算、不沿用旧值。
5. 改规则必须走 `Research/` 提案 → 所有者批准 → 版本发布 → 同步 CI,并在 `Decision-Log.md` 留痕。

## 冷启动:先重建状态

本仓库**不存储任何账户数据**。每个新会话第一件事:按 `02-Operating-System/State-Reconstruction.md` 的确定性程序,从 IBKR + 规则重建全部状态(派生权重、SOXX 生命周期、回撤周期档位、实际入金 F)。回撤档位指针存在 IBKR 警报里(`get_alerts` 读取),不在仓库里。

## 仓库卫生与隐私门(公开仓库,红线)

- 临时分析、抓取的原始数据放会话工作目录,不提交仓库;只有形成决策证据的快照才进 `08-Data/SNAPSHOTS/`(只增不改)。
- **公开安全写法(CI 强制)**:任何提交的 Markdown 中不得出现 NAV、美元金额、股数、成交价格明细。可写:日期、标的、方向、**权重百分比**、定性事实、裁决。数量与金额永久保存在 IBKR,审计时现场调取。
- 向所有者报告账户数字时用聊天输出,永不落盘。
- 历史版本说明已清理:v3.x 要点见 `Decision-Log.md` 与 `BUGLOG.md` 的存档节(git 历史已重建,不可回溯);现行规则一律以工作树文件为准。
