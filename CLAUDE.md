# AI 执行手册（CLAUDE.md）

本仓库是一套**由 AI 执行的个人投资操作系统**（当前 v4.6）。你（AI）的职责是按已发布规则读取数据、计算、报告和把关——**永远不下单**；下单只能由账户所有者在 IBKR 人工完成。

## 30 秒理解系统

- 目标配置：现金 15% ｜ QQQM 28% ｜ SPYM `57%−A_basis` ｜ SOXX（半导体板块倾斜）硬上限 6%。
- `A_basis=max(A_actual, 6%)`，`U=max(6%−A_actual, 0)` 是现金里的 SOXX 用途标签。
- SOXX 买入分两类，判别只看 `A_execution_cap` 动没动：**回补至目标**（执行档不动，买回被市场打下去的权重）走月度例行路径，资金只来自 `U`；**提高倾斜**（推进执行档 3%→4.5%→6%）须完整 IC。别把二者混称「追加」。
- 规则优先级：`00-IPS` → `01-Constitution` → `02-Operating-System` → `03-Transition` → `05-Journal`。冲突时高层覆盖低层;聊天记录与 `Research/` 无规则效力。
- 三条铁律：数据缺失 = `DATA INCOMPLETE`（停止建议,不猜);价格涨跌不构成卖出理由;护栏触发只冻结新增、不自动卖出。

## 例行任务入口

| 任务 | 流程文件 | 要点 |
|---|---|---|
| 每日巡检 | `02-Operating-System/Daily-Review.md` | 先实时读 IBKR 四项(Account Summary/Balances/Positions/Open Orders);记录 SPYM 相对历史高点回撤 `DD` 与档位状态 |
| 周度复盘 | `02-Operating-System/Weekly-Review.md` | 只产出 `NO ACTION / MONTHLY INPUT / IC REVIEW / DATA FIX` |
| 月度执行 | `02-Operating-System/Monthly-Workflow.md` | `D=min(F,G0)`;`B=min(S/R,G)`;回撤达档执行部署 |
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
2. **QQQM / SOXX**：`stockanalysis.com` 聚合页,前 25 大,Yellow。官方页现状(2026-08-01 复测):iShares SOXX 页返回 200 且内嵌 JSON 可提取(含行业表与 Trailing P/E);Invesco QQQM 页返回 200 但是纯 SPA 外壳,HTML 里没有数值。需要 Green 质量时,SOXX 可解析官方页,QQQM 须用你的网页抓取工具或让所有者浏览器确认。
3. **yfinance**：标准 Python 库答案(`yf.Ticker("SOXX").funds_data` 提供 sector_weightings/top_holdings),但**本沙箱网络层不可用**(curl_cffi TLS 与代理冲突);不要在此环境反复尝试。
4. IT 行业合并值：脚本持仓表不含行业列,按 `08-Data/LOOKTHROUGH_CHECK.md` 第 2 步用官方行业表手工加权(SSGA/Invesco/iShares 产品页各一个数字)。

## 如何算本月该买什么

```bash
# 数值从 IBKR 读,只走 argv 与 stdout,永不落盘:
python3 scripts/monthly_execution.py --nav <NetLiq> --cash <TotalCash> \
    --spym <市值> --qqqm <市值> --soxx <市值> --contribution <本月已到账F> \
    --tiers-executed none \         # 或 T1 / T1,T2,按本周期实际已执行档位填
    --lookthrough-current           # 仅当季穿透核查有效时传;不传则回补冻结
python3 scripts/monthly_execution.py --self-test   # 校验算术仍镜像规则
```

一条命令产出 `A_actual/A_basis/U`、各袖套动态目标与正缺口、`D=min(F,G0)`、`S`、`B=min(S/R,G)`、回撤档位、SOXX 回补候选、例行路径检查与 `HOLD / BUY CANDIDATE` 结论,格式即 Deployment-Framework 第 6 节的月度输出。

**它是已发布规则的镜像,不是新规则**——与文档不一致即为脚本 BUG。它不下单、不生成订单指令。两个「不许静默假设」的标志都是 fail-closed:`--tiers-executed` 不填时拒绝授权回撤部署并报 `DATA INCOMPLETE`(档位已执行状态无法从价格推导);`--lookthrough-current` 不传时回补输出 `0` 并报 `DATA INCOMPLETE`(当季穿透核查是否有效无法从账户推导)。

## 如何验证回撤部署状态机

```bash
python3 scripts/drawdown_drill.py                 # SPYM 十年重放 + 七项不变量检查
python3 scripts/drawdown_drill.py --symbol spy    # 指数交叉验证(定档结果应完全一致)
```

日收盘序列同样走 `stockanalysis.com` JSON API（`range=10Y` 是该源上限,更长窗口拿不到）。已验证的是**价格→档位**这一半;「本周期各档是否已执行」的三信号重建仍未验证——首次真实触发时必须把重建过程记进 Journal。结论见 `Research/2026-08-01-drawdown-deployment-drill.md`。

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
- **只有 QQQM/SOXX 跌而 SPYM 没跌**时不触发回撤部署,由再平衡的正缺口吸收——`D/B` 每月自动流向缺口更大的标的。回撤部署只认 **SPYM** 的回撤(四档 ≥10/15/20/25%,等额分批,每档 2.25pp of NAV),从 15% 现金目标算起合计 9pp of NAV,**在 `DD` 25% 处打光,此后无论跌多深都不再解锁**(v4.6 决定,见 `Research/2026-08-01-drawdown-four-tier.md`)。实测:QQQM 近两年三次 11–14% 回撤发生时 SPYM 仅 3.9%–9.1%,均未达档。见 `Research/2026-08-01-drawdown-vs-rebalancing-scope.md` 与 `2026-08-01-t1-threshold-10pct.md`。
- 估值子系统已于 v4.2 整体退役:四个输入字段全 Red 且无法转 Green(QQQM 官方页是 SPA、SOXX 只有 Trailing P/E、历史百分位需要拿不到的 5–10 年序列)。系统不再持有任何估值判断,三条资金通道全部由公式与价格驱动。依据见 `Research/2026-08-01-valuation-subsystem-retirement.md`。
- 完整证据:`Research/2026-07-31-v4-Evidence-and-Proposal.md`。

## 红线（违反即 BUG）

1. 不下单、不生成可直接执行的订单指令;结论只能是 `HOLD / REVIEW / BUY CANDIDATE / SELL CANDIDATE` 等既定词表。
2. 不用历史快照冒充实时账户数据;IBKR Positions 是持仓数量唯一权威。
3. 不在执行过程中临时改阈值、换口径、引入 Research 指标。
4. 数据拿不到就写 `N/A` 并标 `DATA INCOMPLETE`,不估算、不沿用旧值。
5. 改规则必须走 `Research/` 提案 → 所有者批准 → 版本发布 → 同步 CI,并在 `Decision-Log.md` 留痕。

## 代码变更走 PR,不直接推 master

**你不合并 master。** 任何仓库改动一律:开分支 → 本地跑通 `check_policy_consistency.py` → 提交并推分支 → 开 PR → **由所有者审阅合并**。

- master 是受保护的现行规则;直接推 master 会让规则在无人审阅的情况下生效。
- PR 描述必须写清:改了什么、为什么、是否触及任何阈值/公式语义。触及规则语义的 PR 必须先有 `Research/` 提案与所有者批准(红线 5),PR 里引用该提案路径。
- CI(`Policy consistency`)必须绿;红灯的 PR 不提交给所有者审阅。
- 合并后删除该分支,不留已合并的残枝。

## 冷启动:先重建状态

本仓库**不存储任何账户数据**。每个新会话第一件事:按 `02-Operating-System/State-Reconstruction.md` 的确定性程序,从 IBKR + 规则重建全部状态(派生权重、SOXX 生命周期、回撤周期档位、实际入金 F)。回撤档位指针存在 IBKR 警报里(`get_alerts` 读取),不在仓库里。

## 仓库卫生与隐私门(公开仓库,红线)

- 临时分析、抓取的原始数据放会话工作目录,不提交仓库;只有形成决策证据的快照才进 `08-Data/SNAPSHOTS/`(只增不改)。
- **公开安全写法(CI 强制)**:任何提交的 Markdown 中不得出现 NAV、美元金额、股数、成交价格明细。可写:日期、标的、方向、**权重百分比**、定性事实、裁决。数量与金额永久保存在 IBKR,审计时现场调取。
- 向所有者报告账户数字时用聊天输出,永不落盘。
- 历史版本说明已清理:v3.x 要点见 `Decision-Log.md` 与 `BUGLOG.md` 的存档节(git 历史已重建,不可回溯);现行规则一律以工作树文件为准。
