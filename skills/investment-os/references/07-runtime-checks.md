# Skill 运行时校验

本文件落实数据契约，不创建投资政策。skill 核验来源与路由，helper 确定性计算；
不要求 MCP。只有实际连接器证据可组装输入，工具调用本身不证明来源。

## 1. 共享账户门

按 05-state.md 顺序读取 Account Summary、Balances、Positions、Open Orders，
再由 IBKR 合约查询按持仓 contract_id 取得规范 symbol、sec_type、currency。
所有快照记录 status、source、observed_at、source_as_of（券商未提供则 null）。
不得用观察时间替代券商时间，不把缺失当空集合。原始账户快照只在私有内存。

账户对账用 BASE 折算现金加全部证券市值（含 Legacy），容差为 NAV 的 0.5%。
可部署现金只取 min(USD cash_balance, USD settled_cash)，不含 CNH 或 BASE。
检查来源、五分钟内观察时间、一致窗口、币种、借款、订单、重复合约。
持仓分类以 contract_id 关联唯一规范合约，显示名称不参与分类；缺失、重复、
非 STK 或币种不一致关闭账户相关路径。已识别的非目标股票才归 Legacy。

Daily 另检查提醒与常驻自动化。未请求的可选字段不制造故障；
市场背景缺失只披露，不阻断资金规则。账户实质冲突关闭所有部署。

## 2. 内存输入与任务入口

从安装目录解析 scripts/check_runtime.py，Python 3.11+，无依赖、不联网、不存输入。
通过宿主内存 stdin 传 JSON；不得写账户 JSON 到仓库、临时文件、命令行或日志。
没有内存 stdin 能力时不强行落盘。stdout 为 JSON；PASS 退出 0，
DATA INCOMPLETE 退出 2。输出候选不构成下单授权。

capabilities 按能力名索引，每项有 status、source=IBKR、observed_at、data。
共享能力：account_summary.data 含 currency、net_liquidation；
balances.data.balances 保留分币种行；positions.data.positions 保留全部持仓；
open_orders.data.orders；contract_details.data.contracts 为本次按 ID 核验的合约列表，
各项含 contract_id、symbol、sec_type=STK、currency=USD。不得凭显示名称自填映射。
合约数据可由 IBKR 连接器规范化，但必须保留可审计的原始来源关联。

- task=account：只完成共享账户门及披露，无部署金额。
- task=monthly：共享门 + F + 固定日期/生命周期，仅计算 D、B，不要求 market_inputs。
- task=drawdown：共享门 + market_inputs，独立计算 SPYM、QQQM，不要求 F 或 schedule。
- task=funding_ledger：纯私有台账转换，见 08-funding-fx.md；不读写磁盘或执行订单。

月度 F 使用 cash_transactions.data.external_contribution_usd；
缺失关闭 D、B，明确为 0 才按 0 处理。人民币路径改用 funding_confirmation、
funding_ledger 和 fx_funding，不叠加两条证据。funding_confirmation 含
source_currency=CNH、confirmed_new_funding=true、allocation_period=YYYY-MM、trade_ids。
fx_funding 为新鲜 IBKR 能力，data 含 trades、usd_fees_total、
fee_currency_verified、usd_settlement_verified；verified 只能来自实际券商核验。

月度 schedule 含 source=NYSE、monthly_execution_date、calculation_already_run。
日期须由当年度 NYSE 官方日历确认，生命周期须有可验证私有证据。
未知不填 false；helper 只检查传入日期一致，不自行证明官方日历或历史。

## 3. 回撤局部状态

market_inputs 为新鲜 IBKR 观察，data 按 SPYM、QQQM 分别提供 drawdown（小数）、
close_as_of、tiers_executed（经可验证用途关联重建的 T1–T4）。
确认为未执行才传空列表；收盘日期不得未来或超过 7 天。
另一只缺失不阻断可验证阶梯；两只都缺失时 deployment=null。
输入的是已完成收盘相对自身历史最高收盘的回撤，不用盘中价或有限窗口最高冒充 ATH。

共享账户门失败时 deployment=null。单只阶梯失败时 paths 逐只报告，
总状态可为 DATA INCOMPLETE，但 deployment 只包含 PASS 路径的候选；
失败标的 allocation、candidate_tiers 为 null，不写成 0 或空档位。
不得因总状态不完整而隐藏独立通过路径，也不得报告失败路径金额。

月度与回撤共享同一现金。若同日先执行月度，须先回读、刷新账户再算回撤；
不能把两个独立快照的预算相加。所有金额仍须核验整股、报价、佣金和操作授权。
candidate_tiers 不是已执行状态，只有实际成交及回读才消耗档位。

## 4. 无代码或缺失能力

无代码时可用权威结果完成账户检查、权重披露和阻碍解释；
月度及回撤金额需要确定性 helper，无法运行只关闭金额计算路径。
读取 skill 不等于安装工具，不能恢复 MCP 来替代缺失券商事实。
逐项报告来源、时效、对账、订单、F、各阶梯、执行日及最小恢复条件。
未到档是无动作，事实不足是 DATA INCOMPLETE，不混成 HOLD。

## 5. CNH 与私有存储

funding_preparation 单独披露 CNH 余额和已结算上限：
AWAIT_OWNER_REVIEW 表示有已结算 CNH，WAIT 表示为 0，
DATA INCOMPLETE 表示该局部事实未知。它不生成换汇金额或预计 USD，
不影响已结算美元的独立检查。来源确认、去重和执行见 08-funding-fx.md。

helper 不提供私有数据库或持久化保证。资金台账转换输出 persistence_required=true、
runtime_data_persisted=false；宿主必须在可信私有存储中按修订号原子保存并回读。
未配置或无法验证该存储，只能审核/模拟，关闭依赖该台账的真实定投执行。
不得以公开 GitHub、普通临时文件或模型记忆充当私有存储。
