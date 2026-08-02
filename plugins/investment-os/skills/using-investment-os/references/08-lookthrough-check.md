# 季度穿透手工核查（Look-through Manual Check）

v4.0 起本核查表取代 Look-through Evidence Bundle 验证器。目标用时 15 分钟。它计算组合合并穿透暴露并对照 Constitution 护栏；通过或失败都不自动改变 Registry、不授权交易。

## 频率与时效

- 每季度一次；任何 SOXX / 自主倾斜追加 IC 前必须存在当季有效核查。
- 三只 ETF 的行业/持仓数据须在同一核查日读取各自最新官方版本，记录各自 `source_as_of`。

## 自动化辅助（推荐先跑）

```bash
python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario current            # 目标权重
python3 skills/routing-investment-research/scripts/fetch_etf_data.py --weights spym=…,qqqm=…,soxx=…,cash=…   # 实际权重
python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario current --markdown # 生成快照粘贴块
```

脚本自动完成:SPYM 官方全量持仓(SSGA xlsx,Green)、QQQM/SOXX 前25(聚合源,Yellow)、半导体合并下界+尾部上界、发行人合并与护栏对照。**IT 行业合并值仍须按第 2 步官方行业表手工加权**;需要 Green 质量时用官方页面交叉核对 QQQM/SOXX 数值。脚本失败或数字异常时,回退到下方全手工步骤。

## 步骤

1. 从 IBKR 读取当前 NAV 与 SPYM / QQQM / SOXX / 现金 / 其他持仓市值，计算各袖套权重 `w`。
2. 打开三家管理人官方页面，记录：
   - 各基金信息技术行业权重 `IT_f`（SSGA / Invesco / iShares 官方行业表）；
   - 各基金半导体及设备行业权重 `Semi_f`（SOXX 可按 ~100% 处理并注明）；
   - 各基金前 10 大持仓及权重。
3. 计算合并暴露：
   - `IT_combined = Σ w_f × IT_f`（另加直接持仓中属于 IT 的权重）；
   - `Semi_combined = Σ w_f × Semi_f`（同上）；
   - 对前 10 大发行人：`W_issuer = Σ w_f × h_{f,issuer}`（GOOGL/GOOG 等多股类合并为同一发行人）。
4. 对照护栏：IT 45% WARN / 50% 冻结自主倾斜新增；半导体 15% 倾斜新增须 IC；单一发行人 8% WARN / 10% 冻结。
5. 把下方记录模板保存为同级 `08-YYYY-MM-DD-lookthrough-check.md`，通过 PR 提交；历史记录只增不改。

## 记录模板

```markdown
# Look-through Check — YYYY-MM-DD

- observed_at:
- 组合权重 w（来自实时 IBKR）：cash / SPYM / QQQM / SOXX / other =
- SPYM：source_url / source_as_of / IT% / Semi% / 前10大
- QQQM：source_url / source_as_of / IT% / Semi% / 前10大
- SOXX：source_url / source_as_of / Semi%≈100% 说明 / 前10大
- IT_combined =        ｜ 护栏结论：
- Semi_combined =      ｜ 护栏结论：
- Top issuers combined（≥4% 全列）｜ 护栏结论：
- 未分类/近似处理说明（QQQM 尾部、直接持仓等）：
- 总结论：`PASS / WARN / FREEZE-TILT / DATA INCOMPLETE`
```

## 失败处理

- 任一官方页面不可得或口径不明：该字段记 `N/A`，总结论 `DATA INCOMPLETE`，自主倾斜追加冻结；SPYM / QQQM 例行路径不受阻断。
- 数字不得估算、不得沿用上季数值冒充本季。
- 核查发现越线只限制自主倾斜新增或触发复核，不自动卖出。
