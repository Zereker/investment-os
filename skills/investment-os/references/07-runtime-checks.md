# Skill 运行时校验

本文件落实 `06-data-contract.md`，不创建投资政策。skill 负责核验事实来源与
任务路由；本地 helper 负责确定性检查和金额计算，不要求 MCP 服务。

## 1. 能力与证据

按 `05-state.md` 固定顺序读取 Account Summary、Balances、Positions、Open Orders。
每项记录 status、source、observed_at、source_as_of（券商未提供时为 null）。
不能把观察时间冒充券商数据时间。原始结果只在当前私有运行时中存在。
未连接、读取失败、未知与明确为空必须区分；缺失数据保持 null。

校验必须包括来源、读取时效、币种、净值对账、重复合约、现金借款及订单状态。
账户对账用 BASE 折算现金加全部证券市值（包括 Legacy），容差为净值 0.5%。
策略现金另取 USD 行；不得把 CNH 等外币算成可部署美元，也不得把 BASE 当作货币。
对账差额在容差内可披露，不可仅因非零差额关闭路径。差额来源只能作为假设。

Daily 还检查提醒与常驻自动化；按任务局部关闭，不能用可选字段未请求制造故障。
市场背景缺失只作披露，不影响资金规则。账户接口缺失或实质冲突关闭交易路径。

## 2. 本地执行契约

从已安装 skill 的目录解析 `scripts/check_runtime.py`，Python 3.11 以上即可运行，
不安装依赖、不联网、不保存输入。通过 stdin 传 JSON，stdout 返回 JSON；
成功退出码为 0，`DATA INCOMPLETE` 为 2。不得把账户 JSON 写入仓库、临时文件、
命令行参数、调试日志或测试数据。使用宿主支持的内存 stdin 输入能力；没有该能力
时不强行落盘。工具调用本身不证明来源，agent 必须先核验连接器证据。

输入结构：task 为 account 或 monthly；capabilities 按能力名索引，每项含
status、source（IBKR）、observed_at 和 data。data 使用原始连接器 envelope：
account_summary 含 currency、net_liquidation；balances 含 balances 数组；
positions 含 positions 数组；open_orders 含 orders 数组。

月度必须读取 USD cash_balance 与 settled_cash，取较小值作为可用美元现金。
cash_transactions 为可选披露，缺失不影响月度计算，不推断入金。
market_inputs.data 按 SPYM、QQQM 分别提供 drawdown（小数）、close_as_of、
tiers_executed（经成交重建的 T1–T4 列表；确认为未执行才传空列表）。

schedule 含 source=NYSE、monthly_execution_date 和 calculation_already_run。
执行日必须由当年度 NYSE 官方日历确认；已执行状态须有可验证的私有会话或执行
证据。未知不得填 false。helper 检查当日一致，但不能自行证明日历或生命周期。

所有月度前置门完成前，deployment 为 null，不生成 B 或回撤部署金额。
helper 输出仅为候选：整股、佣金、价格、券商能力、授权与成交回读另行核验；
candidate_tiers 不代表已执行档位，只有实际成交后才消耗。

## 3. 无代码执行时

skill 可直接依据权威结果完成账户校验、对账、权重披露、规则解释与阻碍报告。
月度部署金额仍需要确定性 helper，无法执行时只关闭该路径。不得声称读取 skill
等于安装工具；不得要求恢复 MCP 来替代缺失券商数据能力。

## 4. 输出与恢复

逐项报告能力、时效、币种、对账、订单、入金、回撤状态及执行日。
区分工具不可用、事实不可得和不在执行日，写明最小恢复条件。
入金流水缺失不阻断现金部署；回撤不到档时不创造部署理由。
本地 helper 不替代 canonical SKILL.md 的账户所有者授权边界。

## 5. 待换汇资金披露

helper 输出 funding_preparation，CNH 余额与可用美元现金分开显示。
AWAIT_OWNER_REVIEW 表示存在已结算 CNH，仍需确认投资用途、本次金额及券商费用。
WAIT 表示当前没有已结算 CNH；DATA INCOMPLETE 表示 CNH 行或结算事实缺失。
该局部状态不降低可独立通过的美元月度检查。余额不证明入金来源；helper 不输出
预计美元所得，不创建换汇订单。实际流程见 `08-funding-fx.md`。
