# 状态重建规范（Agent 冷启动程序）

本仓库不存储任何账户数据。任何 agent 在任何新会话中，按以下确定性程序从 IBKR + 公开规则现场重建全部运行状态。两个 agent 在同一时点启动必须得到相同结论；无法重建的项一律 `DATA INCOMPLETE`，不猜测、不沿用旧值。

## 启动顺序

1. **读规则**：canonical `SKILL.md` → `00-constitution.md`。规则即代码，状态是规则作用于实时数据的函数。
2. **读账户**（IBKR，固定顺序）：Account Summary → Balances → Positions → Open Orders。任一失败 → 账户侧 `DATA INCOMPLETE`，停止交易建议。
3. **计算派生状态**（无需任何存储）：
   - 各标的实际权重 = 市值 ÷ NetLiq
   - 各标的正缺口 = 目标权重 × NetLiq − 市值，负值取 0
   - 是否位于带宽内（现金 10–20%、SPYM 45–55%、QQQM 25–35%；SOXX 无带宽）
4. **重建回撤周期状态**：
   - 拉 SPYM 一年以上日线（不足以覆盖上一个 ATH 时延长窗口），取**历史最高收盘** → 当前 `DD`。实时 `LAST` 与最后一个已完成日线收盘必须分开记录，`DD` 只使用后者。
   - 周期起点 = ATH 收盘日；新 ATH 收盘 ⇒ 周期重置，各档恢复可用。
   - **各档已执行判定以周期内 IBKR 成交记录为主信号**：识别周期起点之后、由回撤部署产生的买入，按**金额对应该档梯度定额**且**日期落在 `DD` 达该档之后**归属到具体档位。归属不确定时 `DATA INCOMPLETE`，不得猜测。
   - **现金水位只作辅助校验，不得单独判定档位。** 现金权重的分母是实时 NAV，回撤中 NAV 下跌而现金金额不变会使该读数系统性偏高，据此单独判定会反复重触发浅档。
   - 成交记录与现金水位方向冲突且无法用成交记录定夺时，`drawdown deployment state = DATA INCOMPLETE`，停止新的回撤部署候选。
   - **Alert 指针不变量**（状态存于券商，不入库）：未耗尽阶梯时，账户内必须**恰好有一个**启用警报，且满足：标的是 SPYM；字段是 `LAST`；运算符是小于等于；档位是下一个可用档；价格 = `(1−该档触发线)×ATH收盘`（T1 `0.90×`、T2 `0.85×`、T3 `0.80×`、T4 `0.75×`），允许最小报价单位误差。某档执行后删除其警报、创建下一档；**T4 执行后不再创建新警报**。新 ATH 收盘后把**周期状态与警报档位作为同一个原子状态重置**：已执行档位清空、expected pointer 退回 T1、价格按新 ATH 更新；不得只更新价格基准而保留旧档位身份。启动时读取现有警报，但警报只作为 actual pointer；expected pointer 必须由 ATH 与上述成交记录重建结果独立计算——被审计的对象不得充当自身的状态来源。
   - **一致性检查**：把当前 ATH、重建出的 `tiers_executed` 和 IBKR active alerts 输入 `python3 skills/investment-os/scripts/alert_pointer_check.py`。任何差异 ⇒ `Account Health = WARN`、`drawdown deployment state = DATA INCOMPLETE`、停止新的回撤部署候选。agent 只报告 expected/actual 和修复条件，不自动修改券商警报。
5. **实际入金 `F`**：IBKR Cash Transactions 读本月已到账外部净入金。计划数额不存在于仓库；\(D=\min(F,G_0)\) 只用实际值。

## 隐私边界

- 仓库只含：规则、公式、阈值、流程和脚本。
- 仓库永不含：账户标识、NAV、持仓权重、金额、股数、订单、成交、入金、授权或执行结果。这些只存在于受信任的私有运行时与券商记录。
- CI 隐私门（`check_policy_consistency.py`）扫描全部 Markdown，出现美元金额或股数模式即失败。
- 超出 IBKR 查询窗口的成交明细用券商 Flex 报表补，不在仓库存副本。决策当时的推理与结果不进仓库。
