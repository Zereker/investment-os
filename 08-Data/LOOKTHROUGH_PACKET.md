# Look-through Evidence Bundle v1.3

本规范把 SPYM / QQQM / SOXX 穿透 Data Gate 变成可验证证据。它只判断一个**指定交易后情景**的数据是否完整、自洽且满足已发布护栏；**验证通过不改变 Position Registry，不创建 Add Candidate，也不授权交易。**

## 目录与不可变性

每次审核创建独立 Bundle：

```text
08-Data/SNAPSHOTS/lookthrough/YYYY-MM-DD/lookthrough-YYYY-MM-DD-<id>/
├── packet.json
├── account.json
├── candidate.json
├── issuer-registry.json
├── mapping.json
└── raw/
    ├── SPYM.<原始扩展名>
    ├── QQQM.<原始扩展名>
    └── SOXX.<原始扩展名>
```

模板保存在快照目录之外的 `08-Data/LOOKTHROUGH_PACKET_TEMPLATE.json`。Production 快照目录没有按文件名排除的模板通道；每个审核目录都必须含 `packet.json`。

所有 Bundle 文件只增不改。CI 以 PR base 或 push 前一提交为基点，拒绝对既有快照的修改、重命名或删除。来源、映射、账户或候选情景变化时必须创建新 Bundle。

## Packet 必填结构

- `schema_version`：当前固定为 `1.3`。
- `packet_id`：`lookthrough-<review_date>-<id>`，且必须与 Bundle 目录名一致。
- `review_date`、带时区的 `observed_at`；日历日期必须一致。
- `candidate_packet_id / candidate_path / candidate_sha256`：绑定同一 Bundle 内真实、未失效的 SOXX Add Candidate 文件；验证器检查其账户快照哈希、拟议金额、金额上限和失效时间。Candidate 存在不代表已批准。
- `weight_basis`：固定为 `post_trade`。
- `account_scenario_path / account_snapshot_sha256`：固定指向同一 Bundle 内的 `account.json`；账户文件只保存当前 NAV 与市值，且时间不得晚于 Packet。
- `issuer_registry_path / issuer_registry_sha256`：固定绑定 `issuer-registry.json`。注册表以 CIK 或 LEI 作为发行人身份，并将每个稳定证券 ID 映射到唯一发行人；不同股权类别必须共用同一法律实体身份。
- `mapping_path / mapping_sha256`：指向同一 Bundle 内的统一行业映射表。发行人身份不再由该文件自由填写。
- `portfolio_weights`：仅含 `cash / SPYM / QQQM / SOXX`，必须与账户情景重算值一致；SOXX 必须为正且不高于当前 3% 执行上限。
- `funds`：恰好为 SPYM / QQQM / SOXX；每项保存具体产品官方 URL、版本化 `source_format`、`source_as_of`、`retrieved_at`、`raw/` 下固定名称的原始文件和真实字节 `source_sha256`。
- `holdings`：保留带类型的稳定证券标识、原始名称、Sector/Industry、`instrument_type`、`market_weight` 和 `exposure_weight`；必须逐行等于验证器从归档字节解析的结果。
- `metrics / gates / verdict`：必须等于验证器从交易后权重、持仓和映射重算的结果。
- `packet_sha256`：将该字段暂置空字符串后，对键排序、无多余空格的 UTF-8 JSON 求 SHA-256。

验证器使用严格 JSON：重复键、NaN、Infinity、超大文件、路径逃逸、符号链接和超量持仓均被拒绝。

## 官方来源与时效

允许的管理人域名按 ticker 固定：

| Ticker | 官方域名 |
|---|---|
| SPYM | `ssga.com` |
| QQQM | `invesco.com` |
| SOXX | `ishares.com` / `blackrock.com` |

URL 白名单不是单独的真实性证明。URL 路径还必须识别具体产品；原始文件必须分别为 `raw/SPYM.xlsx`、`raw/QQQM.csv`、`raw/SOXX.csv`。验证器使用 `ssga-xlsx-v1`、`invesco-csv-v1`、`ishares-csv-v1` 三个确定性解析器，从归档字节重建日期与完整 holdings，再逐行核对 Packet；Invesco 解析器明确支持官方导出的 `Security Identifier / Holding Ticker / Holding Name / Date` 列。仅保存哈希但不解析不能通过。

证券 ID 按 `CUSIP → ISIN → SEDOL → 管理人标识 → 非占位 ticker` 的顺序选择，并保存为 `CUSIP:`、`ISIN:`、`SEDOL:`、`MANAGER:` 或 `TICKER:` 带类型形式。`-`、`--`、`-CASH-` 等占位 ticker 不能覆盖稳定标识；没有稳定标识的非现金行不得进入 Green。

`review_date` 与 `observed_at` 不得处于未来。`retrieved_at` 必须处于审核日且不晚于 `observed_at`；解析出的 `source_as_of` 必须等于 Packet 声明、不得晚于审核日、不得老于 7 个自然日，三只基金必须完全一致。是否确为管理人当时“最新可得版本”仍须人工核对页面发布日期。

## 权重、舍入与衍生品

- 组合交易后权重必须精确合计 100%。
- 管理人持仓 `market_weight` 允许最多 5 bps 的披露舍入差；因此 100.01% 可表达，但更大缺口不能被重新归一化隐藏。
- 普通股票/基金的 `exposure_weight` 必须与正的 `market_weight` 一致；现金敞口为 0。
- 无法解释的 `other` 不能以零敞口进入 Green。
- 衍生品必须记录单独的 `exposure_weight`。该字段表示相对基金 NAV 的经济名义敞口，不能因市场权重显示为 0 而省略。
- 每个正衍生品敞口必须在哈希化映射表中提供 `derivative_components`，底层分解权重在 5 bps 内合计 100%。组件只能引用注册表和行业映射中同时存在的直接证券 ID，不能自由填写发行人 ID。验证器按分解后的发行人、科技和半导体暴露计算。

iShares 对 `Notional Value` 的说明可作为 SOXX 衍生品 `exposure_weight` 的原始口径；Packet 必须保留管理人原始字段，不能用手填汇总替代。

## 统一映射

`mapping.json` 采用 GICS Sector，并只允许受控 Industry 值：

- `Semiconductors & Semiconductor Equipment`
- `Other / non-semiconductor`

发行人注册表与行业映射中的每条记录都必须保存非空证据。发行人身份只允许 `cik:<10-digits>` 或 `lei:<20-character-LEI>`；CIK 必须绑定同一编号的 SEC URL，LEI 必须绑定同一编号的 GLEIF URL。注册表拒绝重复发行人 ID、重复规范公司名和重复证券 ID，并强制共享 CUSIP issuer number（也包括美国 ISIN 内嵌的 CUSIP）的证券使用同一发行人，因此 Alphabet A/C 等多股权类别不能拆分。可识别的管理人原始 Sector/Industry 必须与统一映射一致；例如原始 `Technology` 不能映射成 Industrials，包含 `Semiconductor` 的原始 Industry 不能映射成非半导体。

## 独立缺口与最坏情形

发行人未知权重和分类未知权重分别计算：

- `issuer_unknown_weight` 只进入单一发行人最坏情形上界；
- `classification_unknown_weight` 只进入科技与半导体最坏情形上界；
- 不再用一个 `min()` 残差混合两个不同缺口。

衍生品名义敞口可能使 `gross_lookthrough_exposure` 高于非现金市值；覆盖率以实际总经济敞口为分母。

## Green 关闭标准

验证器只在以下条件全部成立时输出 `DATA GATE PASS`：

1. 三只基金在同一审核日采集、`source_as_of` 完全一致且满足时效上限；
2. 官方产品 URL、原始文件实哈希、确定性解析结果、发行人注册表、行业映射、账户、Candidate 与 Packet 哈希全部通过；
3. 账户快照不晚于 Packet，Candidate 已创建且未失效，拟议金额不超过上限；交易后权重可独立重算，SOXX 为正且不高于 3%；
4. 管理人市值权重仅有允许的舍入差，衍生品名义敞口已分解；
5. 发行人和统一分类覆盖率均为 100%；
6. 最坏情形上界满足：
   - 科技严格低于 50%；
   - 半导体不高于 15%；
   - 单一发行人不高于 10%；
7. 全部数值有限、结构严格且历史证据没有被覆盖。

8% 发行人水平仍是治理复核线；10% 是验证器硬阻断线。验证器不会替代 IC 对 8%–10% 区间的判断。

## 执行

```bash
python3 scripts/validate_lookthrough_packet.py --self-test
python3 scripts/test_lookthrough_adversarial.py
python3 scripts/validate_lookthrough_packet.py \
  --scan-root 08-Data/SNAPSHOTS/lookthrough
python3 scripts/check_lookthrough_history.py <base-sha>
```

CI 对自测设置执行超时，并扫描固定目录结构；不存在 `TEMPLATE.json`、任意模板命名或目录缺失时静默跳过的路径。

## 与 SOXX 解冻的关系

Packet通过只是SOXX解冻的必要条件之一。现行 NYSE Semiconductor Index 完整方法证据仍须独立完成，Registry 仍须经治理更新；此后每次潜在追加仍需实时 IBKR、未过期 Add Candidate Packet、完整 IC `APPROVE` 与账户所有者人工下单。
