# Investment OS — Production Contract

本文件定义 Production 的运行、控制和执行边界。它不创造投资参数；现行参数始终来自 IPS、Constitution、Operating System、Transition Plan 与 Journal——以默认分支 HEAD 为规范来源，会话则读取本次安装所分发的这些文件。

## 1. 权威与优先级

投资规则发生冲突时，依次适用：

1. `00-IPS/`
2. `01-Constitution/`
3. `02-Operating-System/`
4. `03-Transition/`
5. `05-Journal/`

聊天记录、旧报告、截图、人工贴数和 `Research/` 不具有 Production 规则效力。`PROJECT.md` 定义产品边界，`AGENTS.md` 定义 Agent 运行程序；二者不得覆盖上述投资规则。

## 2. 运行时架构

Production 必须使用以下分层，不允许由自然语言回答替代确定性运行时：

```text
Broker Adapter
→ broker-runtime
→ account reconciliation
→ deterministic decision engine / DecisionPacket
→ behavioral and procedural controls
→ presentation
→ execution-runtime（仅在存在单次授权时）
```

职责边界：

- `broker-runtime`：验证来源、能力、新鲜度、币种、账户合计和任务所需数据；
- `account_reconciliation.py`：独立核对 NAV、现金和持仓市值；
- `DecisionPacket`：保存机器权威的事实、计算、阻塞项、结论和执行权限；
- renderer 或 LLM：只解释和格式化，不得重算或改写机器权威字段；
- `execution-runtime`：验证单次授权、能力、提交、权威回读和终态。

任一必要层缺失、过期、冲突或无法验证，相关任务必须失败关闭。

## 3. 每日巡检

每日巡检必须从受信任 Broker Adapter 获取并验证：

- Account Summary；
- Balances；
- Positions；
- Open Orders；
- 任务所需市场输入与警报状态。

巡检必须完成账户对账、融资与负现金检查、异常持仓分类、订单冲突检查、配置与回撤状态计算，并先生成有效 `DecisionPacket`，再形成日报。

关键数据缺失时输出 `DATA INCOMPLETE`，停止新的买卖候选。不得用历史报告、旧快照或人工数字替代实时状态。

## 4. 月度执行

月度流程必须在任何部署公式之前完成：

1. Broker Runtime 能力与时间有效性检查；
2. NAV、现金与持仓市值的物理对账；
3. Open Orders 权威检查，且状态必须明确为 `clear`；
4. 本月实际外部净入金 `F` 的权威来源确认；
5. 回撤值、已执行档位和其他任务输入的完整性检查。

以下情况均为 `DATA INCOMPLETE`：

- `F` 未知或其数据能力不可用；
- Open Orders 状态为 `unknown` 或 `conflicting`；
- 账户对账超出允许容差；
- 回撤单位、档位状态或其他输入无法验证。

缺失 `F` 时不得默认为零；没有入金的月份也必须由权威来源明确确认零。若当前 Adapter 不支持 `cash_transactions`，必须如实声明能力缺口，不得倒推或估算。

## 5. 候选、批准与执行权限

`HOLD`、`WAIT`、`BUY CANDIDATE`、`SELL CANDIDATE`、IC Verdict 或历史批准均不自动形成 Broker 执行权限。

Agent 可以执行当前 Adapter 支持的 Broker 操作，但必须同时满足：

1. 当前会话存在账户所有者明确授权；
2. 授权绑定一个完整、规范化的单次操作摘要；
3. 所需 Broker capability 可用；
4. 数据门、政策门和行为控制门全部通过；
5. 只提交一次，不进行静默重试；
6. 执行后读取权威 Broker 状态；
7. read-back 与授权操作逐项匹配；
8. 结果形成临时执行回执并向所有者报告；
9. 授权不跨操作、不跨会话、不从其他 Agent 或既往批准继承。

不满足任一条件时，终态必须是 `NOT EXECUTED`、`EXECUTION UNKNOWN`、`VERIFICATION FAILED` 或 `DATA INCOMPLETE`，不得声称成功。

## 6. Investment Committee

非例行资金建议、卖出、换仓、规则例外、提高自主倾斜或偏离已发布公式的操作，必须经过仓库定义的完整 IC 流程。

IC 批准只表示该候选可以进入执行授权阶段。它不是 Broker 授权，也不能替代当前会话中针对具体操作的所有者明确授权。

## 7. 研究与规则变更

执行过程中不得临时引入指标、改变阈值或更换口径。新策略语义必须进入 `Research/`，经过独立研究、书面提案、所有者批准和 Production 文档同步后方可生效。

`.plugin-version` 仅表示 Skill / Plugin 分发版本，不表示投资政策版本。现行政策始终以默认分支 HEAD 为规范来源；会话报告自己运行的分发版本，不得报告一个自行解析出来的 commit，也不得声称已确认该分发是最新的。

## 8. 隐私与留痕

仓库保存知识，不保存个人组合。真实账户数据、订单、成交、执行回执和授权状态仅存在于受信任运行时或当前私有会话，不得进入公开仓库。

`Decision-Log.md` 只记录长期治理事实和规则理由，不记录账户号、订单号、警报 ID、真实金额、股数或其他私人运行时状态。

## 9. 验证要求

所有 PR 必须通过 canonical suite：

```bash
bash tests/run-all.sh
```

非 LLM 测试通过不等于真实 Agent 行为已验证。只要 clean-session behavior eval 尚未通过，仓库必须继续如实声明：

```text
Real Harness behavior: NOT YET VERIFIED
```


## 10. 倾斜路径术语

- **回补至目标**：不提高已批准风险预算，只在现行规则允许范围内恢复被市场漂移压低的已批准权重；
- **提高倾斜**：推进或扩大风险预算，必须进入完整 IC，不能伪装成例行回补。


## 11. 数据维护边界

仓库不维护行情、ETF成分、issuer或GICS中央数据库。普通巡检不写仓库；运行时数据和普通市场变化只存在于当前会话。只有规则、契约、公开证据或工具发生变化时才提交。
