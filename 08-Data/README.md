# 08-Data

Investment OS 的可审计数据层。

## 文件

- `DATA_REGISTRY.md`：允许进入 Production 的来源和失败处理。
- `DATA_DICTIONARY.md`：字段定义、口径与缺失值规则。
- `DATA_QUALITY.md`：Green / Yellow / Red 数据质量闸门。
- `SNAPSHOTS/`：按观察日期保存不可变的官方估值快照。

## 每周估值快照流程

1. 打开已登记的基金管理人官方页面。
2. 记录 `observed_at`、官方 `source_as_of`、字段标签和值。
3. 按 Data Quality Gate 评级。
4. 缺失字段写 `N/A`，不得估算或沿用旧值。
5. 通过 PR 写入快照；历史快照不覆盖，只新增。

## Production 边界

快照只提供事实数据。是否影响交易由 `PRODUCTION.md`、Constitution 和 Operating System 决定。数据文件不得自行增加或改变交易规则。
