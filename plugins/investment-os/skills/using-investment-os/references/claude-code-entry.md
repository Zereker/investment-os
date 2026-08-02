# Claude Code Entry — Investment OS

本文件是 Claude Code 的冷启动入口，只规定如何加载和运行系统，不复制投资参数。具体规则、阈值、公式和投资宇宙必须每次从**本次安装所分发的政策文件**读取。默认分支 HEAD 是这些文件的规范来源，但会话不在运行时另行获取更新：分发是否落后于默认分支属于发版问题，不是会话能自证的问题（见 `docs/SKILL-DISTRIBUTION.md` 的 Version boundary）。

## 1. Mandatory Start

每个新会话依次执行：

1. 读取 `project-contract.md`、`production-contract.md` 和 `agent-execution-contract.md`；
2. 从 `skills/using-investment-os/SKILL.md` 开始路由任务；
3. 根据任务加载所需组合 Skill；
4. 从 Broker Adapter 现场重建状态，不继承旧报告或其他 Agent 的状态；
5. 运行确定性脚本，先取得机器权威结果，再生成自然语言回答。

禁止把本文件、聊天记忆或旧摘要当成参数来源。

## 2. Composable Skill System

Investment OS 是一个 router 加多个可组合 Skills：

- `using-investment-os`：统一入口与任务路由；
- `broker-runtime`：验证 Broker 能力、新鲜度和运行时完整性；
- `reconstructing-portfolio-state`：重建账户与市场状态；
- `enforcing-behavioral-controls`：维持交易意图、批准和多 Agent 控制；
- `running-daily-review`：生成 Daily `DecisionPacket` 与报告；
- `running-monthly-review`：执行月度资金审查；
- `evaluating-transaction-candidates`：评估具体候选；
- `validating-drawdown-state`：验证回撤周期与警报指针；
- `execution-runtime`：在单次所有者授权下执行并验证 Broker 操作；
- `routing-investment-research`：隔离未批准研究；
- `auditing-investment-os`：审计政策、实现、隐私、测试和运行准备度。

Skill 只保存流程，不保存易变参数。每次运行都必须重读本次分发的政策文件，不得沿用聊天记忆、旧摘要或上次运行的结论。

## 3. Runtime Chain

```text
Broker Adapter
→ broker-runtime
→ account_reconciliation.py
→ deterministic decision engine
→ DecisionPacket
→ renderer / LLM explanation
→ execution-runtime（仅有单次授权时）
```

关键边界：

- Adapter 只负责把具体 Broker 工具映射成规范化输入；
- `broker-runtime` 自己验证数据，不信任调用者自报 PASS；
- `account_reconciliation.py` 独立核对 NAV、现金和持仓；
- `DecisionPacket` 是事实、计算、结论、阻塞项和执行权限的机器权威；
- LLM 只能解释或格式化，不得重算、改写或升级权限；
- `execution-runtime` 只接受当前会话、单一规范化操作的明确所有者授权。

## 4. Broker State

仓库不保存账户状态。每次任务按需要读取：

- Account Summary；
- Balances；
- Positions；
- Open Orders；
- Quotes / market inputs；
- Alerts；
- Cash Transactions（若 Adapter 提供）。

能力缺失必须如实标为 unavailable。当前 Adapter 取不到的数据不能靠猜测、余额变化倒推、截图、手工贴数或旧报告补齐。

特别是月度入金 `F`：缺少权威 `cash_transactions` 能力时，Routine DCA 必须 `DATA INCOMPLETE`，除非 Production 未来正式批准一条窄化的 owner-attested runtime fact 规则。

## 5. Decision and Presentation

Daily 路径必须先生成有效 `DecisionPacket`，再由 Markdown renderer 或 LLM 表达。

LLM 不得：

- 自己计算部署金额；
- 把未知数据当成零；
- 把缺失能力降级为普通提示；
- 修改 `runtime_status`、`decision`、阻塞项或 `execution_authority`；
- 从候选、IC Verdict、历史批准或其他 Agent 输出推导执行权限。

## 6. Broker Execution

Agent 不是“永不操作 Broker”，但任何写操作或交易都必须经过 `execution-runtime`：

1. 规范化完整操作；
2. 计算 operation digest；
3. 验证当前会话的单次所有者授权；
4. 检查 capability、政策门、数据门和行为门；
5. 只提交一次；
6. 权威 read-back；
7. 比较预期与实际结果；
8. 报告 `COMPLETED`、`NOT EXECUTED`、`EXECUTION UNKNOWN` 或 `VERIFICATION FAILED`。

禁止泛化授权、跨会话继承、无人值守执行链和不确定结果后的静默重试。

## 7. Behavioral Controls

交易意图按底层行为识别，不按措辞、理由、ticker 是否重复来重置。用户换公司描述、行业描述、理由、语言、拆分请求或插入无关问题，都不能自动清除之前的阻断状态。

真实语义连续性目前只能由 clean-session Agent eval 验证。非 LLM 测试全绿时仍必须保留：

```text
Real Harness behavior: NOT YET VERIFIED
```

## 8. Validation

提交前运行唯一入口：

```bash
bash tests/run-all.sh
```

该入口覆盖 Skill、Broker Runtime、账户对账、DecisionPacket、Execution Runtime、月度数据门、Eval harness 完整性、产品契约、隐私和治理检查。

真实 Agent 行为 eval 必须使用：

- 同一 actor clean session 的完整多轮 transcript；
- 独立 verifier 进程与 clean session；
- 逐条 required / forbidden 证据；
- 语义判断，而不是关键词命中。

## 9. Repository and Privacy

- 不直接推受保护默认分支；
- 通过分支和 PR 提交；
- 不在仓库、Issue、PR、fixture 或日志中保存真实账户数据；
- synthetic 测试数据必须明确且不可反推个人资产；
- 临时授权、执行回执和运行时状态不持久化；
- `.plugin-version` 只表示分发版本，不表示政策版本。

## 10. Fail Closed

任何关键规则、状态、能力、授权或验证缺失时：

```text
DATA INCOMPLETE / NOT EXECUTED
```

停止新的候选或执行，不估算、不沿用旧值、不自行放宽规则。


## 11. Deterministic Entry Points

月度确定性计算入口是 `skills/running-monthly-review/scripts/monthly_execution.py`。调用前必须先通过 Broker Runtime、账户对账、权威 `F` 与 Open Orders 状态门；脚本输出候选，不自动形成执行权限。
