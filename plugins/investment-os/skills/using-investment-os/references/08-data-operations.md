# 08 — Data Operations

Investment OS 的可审计数据层。

## 文件

- `08-data-registry.md`：允许进入 Production 的来源和失败处理。
- `08-data-dictionary.md`：字段定义、口径与缺失值规则。
- `08-data-quality.md`：Green / Yellow / Red 数据质量闸门。
- `08-lookthrough-check.md`：季度穿透手工核查程序与记录模板（v4.0 起取代 Bundle 验证器）。
- `08-YYYY-MM-DD-lookthrough-check.md`：按观察日期保存不可变的季度核查记录。

运行时数据由已登记的专业来源分别提供，仓库不维护重复的中央证券数据库。普通数据变化不更新项目；只有估值快照与季度核查记录按只增不改原则存档。

## 每周估值快照流程

1. 打开已登记的基金管理人官方页面。
2. 记录 `observed_at`、官方 `source_as_of`、字段标签和值。
3. 按 Data Quality Gate 评级。
4. 缺失字段写 `N/A`，不得估算或沿用旧值。
5. 通过 PR 写入快照；历史快照不覆盖，只新增。

## 季度穿透核查

按 `08-lookthrough-check.md` 手工完成，记录保存为同级的日期前缀参考文件。核查结论只限制自主倾斜新增或触发复核，不自动改变 Registry、不授权交易。

## Production 边界

快照只提供事实数据。是否影响交易由 `production-contract.md`、Constitution 和 Operating System 决定。数据文件不得自行增加或改变交易规则。
