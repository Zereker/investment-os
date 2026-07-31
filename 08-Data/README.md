# 08-Data

Investment OS 的可审计数据层。

## 文件

- `DATA_REGISTRY.md`：允许进入 Production 的来源和失败处理。
- `DATA_DICTIONARY.md`：字段定义、口径与缺失值规则。
- `DATA_QUALITY.md`：Green / Yellow / Red 数据质量闸门。
- `LOOKTHROUGH_PACKET.md`：SPYM / QQQM / SOXX 穿透证据Bundle v1.5及Green关闭标准。
- `LOOKTHROUGH_ISSUER_REGISTRY_TEMPLATE.json`：以 CIK / LEI 统一多股权类别发行人身份的注册表模板。
- `SNAPSHOTS/`：按观察日期保存不可变的官方估值与穿透快照。

运行时身份与分类数据由已登记的专业来源分别提供，仓库不维护重复的中央证券数据库。普通巡检不写仓库；只有形成真实决策证据时，才把当次来源、日期、身份、分类、原始文件和哈希冻结在不可变 Bundle 中。

## 每周估值快照流程

1. 打开已登记的基金管理人官方页面。
2. 记录 `observed_at`、官方 `source_as_of`、字段标签和值。
3. 按 Data Quality Gate 评级。
4. 缺失字段写 `N/A`，不得估算或沿用旧值。
5. 穿透快照按`LOOKTHROUGH_PACKET.md`保存原始文件哈希、完整底层持仓、重算指标和Packet哈希。
6. 运行验证器；只有通过后才可把该Packet标记为`DATA GATE PASS`。
7. 通过 PR 写入快照；历史快照不覆盖，只新增。

## Production 边界

快照只提供事实数据。是否影响交易由 `PRODUCTION.md`、Constitution 和 Operating System 决定。数据文件不得自行增加或改变交易规则。
