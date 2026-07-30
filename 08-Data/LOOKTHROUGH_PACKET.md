# Look-through Evidence Packet v1.0

本规范把 SPYM / QQQM / SOXX 穿透 Data Gate 从文字要求变为可验证证据。它只判断数据包是否完整、自洽且满足已发布护栏；**验证通过不改变 Position Registry，不创建 Add Candidate，也不授权交易。**

## 文件与不可变性

Production Packet 保存为：

`08-Data/SNAPSHOTS/lookthrough/YYYY-MM-DD/lookthrough-YYYY-MM-DD-<id>.json`

每次审核新增文件，不覆盖历史文件。原始官方持仓文件应与 Packet 一并归档或保存在持久证据库；Packet 对每个原始文件记录小写十六进制 SHA-256。若原始文件、映射或组合权重变化，必须创建新 Packet。

## 必填结构

- `schema_version`：当前固定为 `1.0`。
- `packet_id`：以 `lookthrough-<review_date>-` 开头。
- `review_date`、带时区的 `observed_at`；两者日历日期必须一致。
- `mapping_version`：本次发行人、Sector与Industry统一映射的不可变版本标识。\n- `portfolio_weights`：仅含 `cash / SPYM / QQQM / SOXX`，合计 1。
- `funds`：恰好三项且 ticker 唯一；每项保存官方来源、`source_as_of`、原始文件 SHA-256 和完整 holdings。
- `holdings`：基金内权重必须合计 1；现金、衍生品、嵌套基金和未分类残余也必须作为行保留，不得把已知持仓重新归一。
- 每个holding必须保存稳定`security_id`和管理人原始`raw_sector / raw_industry`字段；原始值未知时使用JSON `null`。\n- `issuer_group_id / normalized_sector / normalized_industry`：未知时使用 JSON `null`，不得猜测或空字符串。
- `metrics / gates / verdict`：必须等于验证器从 holdings 与组合权重重新计算的结果。
- `packet_sha256`：将该字段暂置空字符串后，对键排序、无多余空格的 UTF-8 JSON 求 SHA-256。

## Green 关闭标准

验证器只在以下条件全部成立时输出 `DATA GATE PASS`：

1. SPYM、QQQM、SOXX均使用同一审核日可得的最新官方完整持仓；
2. 三只基金的 `source_as_of` 完全相同；
3. 三只基金内部权重各自合计 100%，组合权重合计 100%；
4. 发行人和统一分类覆盖率均为 100%，未分类贡献为 0；
5. 用“已知暴露 + 未分类暴露”计算的上界满足：
   - 科技严格低于 50%；
   - 半导体不高于 15%；
   - 单一发行人不高于 10%；
6. Packet 内容哈希一致且全部数值有限。

8%发行人水平仍是治理复核线；10%是验证器的硬阻断线。验证器不会替代 IC 对 8%–10% 区间的判断。

任一条件失败，Packet不得写成 `DATA GATE PASS`；应修复数据或保持 `DATA INCOMPLETE`。Yellow日期错位不满足SOXX新增所需的Green标准。

## 执行

```bash
python3 scripts/validate_lookthrough_packet.py --self-test
python3 scripts/validate_lookthrough_packet.py 08-Data/SNAPSHOTS/lookthrough/2026-08-01/lookthrough-2026-08-01-run1.json
```

CI 会运行故障注入自测，并验证仓库中除 `TEMPLATE.json` 外的所有 JSON Packet。Production Packet不得设置 `test_only=true`。

## 与SOXX解冻的关系

Packet通过只是SOXX解冻的必要条件之一。现行NYSE Semiconductor Index完整方法证据仍须独立完成，Registry仍须经治理更新为 `Approved / Hold`；此后每次潜在追加仍需实时IBKR、未过期 Add Candidate Packet、完整IC `APPROVE` 与账户所有者人工下单。
