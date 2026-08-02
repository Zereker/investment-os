# Look-through Check — 2026-07-31

- observed_at: 2026-07-31（美股 7/31 收盘后）
- 组合权重 w：本次按目标情景 cash=15% / SPYM=51% / QQQM=28% / SOXX=6% 计算（实际权重需 IBKR,本环境无接口;实际权重版本待日常运行环境复算）
- 采集方式：`python3 skills/routing-investment-research/scripts/fetch_etf_data.py --scenario current --markdown` + 官方页面行业表交叉核对

## 来源

- SPYM：SSGA 官方持仓 xlsx（全量 505 行）/ source_as_of 30-Jul-2026 / **Green**；官方行业表 IT=37.22%（source_as_of 30-Jul-2026）
- QQQM：stockanalysis.com 持仓页（top-25,覆盖 70.1%）/ source_as_of Jul 24, 2026 / **Yellow**（聚合源;Invesco 官方页为 SPA,无头抓取不可得）
- SOXX：stockanalysis.com 持仓页（top-25,覆盖 96.7%）/ source_as_of Jul 24, 2026 / **Yellow**;官方行业表交叉核对：iShares 产品页 30-Jul-2026,半导体 78.88% + 半导体设备 20.99% = **99.87%**,现金 0.13% —— 验证「残余按半导体」处理

## 结果

- **Semi_combined（已知下界）= 22.5%**,未覆盖尾部 ≤8.4pp（主要为 QQQM 尾部 29.9%×28%）
  - 护栏对照：≥15% → **半导体线结构性触发**,任何 SOXX/倾斜新增须完整 IC 并显式确认
- **IT_combined ≈ 41.8%**（51%×37.22 官方 + 28%×≈60 名义层估算 + 6%×99.87 官方）
  - QQQM 的 IT 用 top-25 名义层 GICS 分类 + 尾部近似,**Yellow**;官方行业表不可得
  - 护栏对照：< 45% WARN 线,**ok**（含 ±2pp 估算误差仍低于 45%）
- **单一发行人合并**（≥4% 全列）：NVDA 6.6%、AAPL 6.2%、GOOGL(A+C) 4.5%、MSFT 4.0%
  - 护栏对照：全部 < 8% WARN 线,**ok**
- 未分类/近似处理：QQQM/SOXX 持仓仅 top-25（聚合源）;SPYM 官方全量;股类合并仅 GOOGL/GOOG

## 总结论

**WARN — 半导体线结构性触发（Core 自身即 >15%）,倾斜新增须 IC;IT 与发行人护栏正常。**

本核查不改变 Registry、不创建候选、不授权任何订单。下次核查:2026-Q4 或任何倾斜追加 IC 前。
