# Look-through Evidence Bundle v1.4

本规范把 SPYM / QQQM / SOXX 穿透 Data Gate 变成可验证证据。它可记录**当前 HOLD 观察**或**指定交易后 ADD 情景**，并判断数据是否完整、自洽且满足已发布护栏；**验证通过不改变 Position Registry，不创建交易指令，也不授权交易。**

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
    ├── SPYM.xlsx（来源完整时）
    ├── QQQM.json（来源完整时）
    └── SOXX.csv（来源完整时）
```

模板保存在快照目录之外的 `08-Data/LOOKTHROUGH_PACKET_TEMPLATE.json`。Production 快照目录没有按文件名排除的模板通道；每个审核目录都必须含 `packet.json`。

仓库级受控 authority 保存在：

```text
08-Data/REGISTRIES/
├── LOOKTHROUGH_ISSUER_AUTHORITY.json
└── LOOKTHROUGH_CLASSIFICATION_AUTHORITY.json
```

所有 Bundle 文件只增不改。两份 authority 也只允许在数组尾部追加经独立审查的记录，不允许改写、重排或删除既有身份与分类。CI 以 PR base 或 push 前一提交为基点执行两类历史检查。来源、映射、账户或候选情景变化时必须创建新 Bundle。

Bundle 顶层和 `raw/` 必须与契约引用精确一致；未被 Packet 绑定的影子 Packet、额外来源、子目录或其他文件都会失败。历史检查必须能够读取并验证完整 base commit 及两份 base authority；base 不可用或 authority 不可读时失败关闭，不能静默跳过。

## Packet 必填结构

- `schema_version`：当前固定为 `1.4`。
- `packet_id`：`lookthrough-<review_date>-<id>`，且必须与 Bundle 目录名一致。
- `review_date`、带时区的 `observed_at`；日历日期必须一致。
- `candidate_packet_id / candidate_path / candidate_sha256`：绑定同一 Bundle 内真实、未失效的 SOXX Candidate 文件。`ADD` 必须有正的拟议金额且不超过金额上限；`HOLD` 必须使用零金额。两者都不代表已批准。
- `weight_basis`：`HOLD` 固定为 `current`；`ADD` 固定为 `post_trade`。
- `account_scenario_path / account_snapshot_sha256`：固定指向同一 Bundle 内的 `account.json`；账户文件保存 IBKR 来源、活动订单数、当前 NAV 与 `cash / other / SPYM / QQQM / SOXX` 市值，且时间不得晚于 Packet。
- `issuer_registry_path / issuer_registry_sha256`：固定绑定 `issuer-registry.json`。该文件只能包含中央 issuer authority 中逐对象完全相同的记录；每个来源 ID 先解析为 `canonical_security_id`，再绑定唯一 CIK 或 LEI。不同 ID 与股权类别必须通过中央 crosswalk 共用同一法律实体身份。
- `mapping_path / mapping_sha256`：指向同一 Bundle 内的统一行业映射快照。每条记录必须逐对象存在于中央 classification authority，Bundle 不能自行创建或重写分类。
- `portfolio_weights`：仅含 `cash / other / SPYM / QQQM / SOXX`，必须与账户情景重算值一致。SOXX 超过当前 3% 执行上限时必须被真实记录并使对应 gate 为假，不能让整个 Bundle 因此无法落盘。
- `funds`：恰好为 SPYM / QQQM / SOXX。`complete` 保存官方 URL、版本化 `source_format`、`source_as_of`、`retrieved_at`、`raw/` 原始文件和真实字节 `source_sha256`；`unavailable` 保存非空 `failure_reason`，不得声称不存在的日期、文件、哈希或 holdings。
- `holdings`：保留主 `security_id`、原始行中全部有效 `source_identifiers`、原始名称、Sector/Industry、`instrument_type`、`market_weight` 和 `exposure_weight`；必须逐行等于验证器从归档字节解析的结果。
- `metrics / gates / verdict`：必须等于验证器从当前或交易后账户情景、持仓和映射重算的结果。
- `packet_sha256`：将该字段暂置空字符串后，对键排序、无多余空格的 UTF-8 JSON 求 SHA-256。

验证器使用严格 JSON：重复键、NaN、Infinity、超大文件、路径逃逸、符号链接和超量持仓均被拒绝。

## 官方来源与时效

允许的管理人域名按 ticker 固定：

| Ticker | 官方域名 |
|---|---|
| SPYM | `ssga.com` |
| QQQM | `invesco.com` |
| SOXX | `ishares.com` / `blackrock.com` |

URL 白名单不是单独的真实性证明。URL 路径还必须识别具体产品；完整来源文件分别为 `raw/SPYM.xlsx`、`raw/QQQM.json`、`raw/SOXX.csv`。验证器使用 `ssga-xlsx-v1`、`invesco-json-v1`、`ishares-csv-v1` 三个确定性解析器，从归档字节重建日期与完整 holdings，再逐行核对 Packet。归档字节自身也必须绑定产品：State Street工作簿元数据必须识别SPYM，Invesco响应必须包含QQQM CUSIP `46138G649`、一致的`effectiveDate / effectiveBusinessDate`以及与数组长度相等的`totalNumberOfHoldings`，iShares CSV元数据必须识别`iShares Semiconductor ETF`。Invesco重复JSON键被拒绝。仅保存哈希或只在Packet中自述产品URL不能通过。

证券 ID 按实际识别出的类型执行 `CUSIP → ISIN → SEDOL → 管理人标识 → 非占位 ticker` 优先级，而不是按原始列出现顺序选择；因此 State Street 同时提供通用 `Identifier` 与 `SEDOL` 时，通用列中的有效 CUSIP 仍优先。所有有效 ID 都以 `source_identifiers` 原顺序无关、类型优先的数组保存；验证器要求它们在中央 crosswalk 中解析到同一 `canonical_security_id` 与发行人。ID 使用 `CUSIP:`、`ISIN:`、`SEDOL:`、`MANAGER:` 或 `TICKER:` 带类型形式。`-`、`--`、`-CASH-` 等占位 ticker 不能覆盖稳定标识；没有稳定标识的非现金行不得进入 Green。

State Street `ssga-xlsx-v1` 明确识别 Daily XLSX 中的 `Holdings: As of DD-Mon-YYYY`；Invesco 使用 `effectiveDate`。`review_date` 与 `observed_at` 不得处于未来。`retrieved_at` 必须处于审核日且不晚于 `observed_at`；完整来源解析出的 `source_as_of` 必须等于 Packet 声明、不得晚于审核日、不得老于 7 个自然日。三只基金全部完整且日期完全一致，`sources_complete_same_date` 才为真；缺失基金的组合权重全部进入发行人和分类未知上界。

## 权重、舍入与衍生品

- 组合交易后权重必须精确合计 100%。
- 管理人持仓 `market_weight` 允许最多 5 bps 的披露舍入差；因此 100.01% 可表达，但更大缺口不能被重新归一化隐藏。
- 普通股票/基金的 `exposure_weight` 必须与正的 `market_weight` 一致；现金敞口为 0。
- 无法解释的 `other` 不能以零敞口进入 Green。
- 账户级 `other` 残差不能从风险计算中消失；其全部权重同时进入发行人未知与分类未知最坏情形。
- 衍生品必须记录单独的 `exposure_weight`。该字段表示相对基金 NAV 的经济名义敞口，不能因市场权重显示为 0 而省略。
- Invesco期货的`Synthetic Cash / CONTRA FUTURE`配对行是市场价值抵销项，保留其负`market_weight`但`exposure_weight`为0；实际期货行按名义值计一次，不能把同一风险双计。
- 每个正衍生品敞口只有在哈希化映射表中提供 `derivative_components` 后才能获得覆盖；底层分解权重在 5 bps 内合计 100%。缺少映射时其敞口进入发行人和分类未知上界，而不是伪造身份或阻止观察 Bundle 落盘。

iShares 对 `Notional Value` 的说明可作为 SOXX 衍生品 `exposure_weight` 的原始口径；Packet 必须保留管理人原始字段，不能用手填汇总替代。

## 统一映射

`mapping.json` 采用 GICS Sector，并只允许受控 Industry 值：

- `Semiconductors & Semiconductor Equipment`
- `Other / non-semiconductor`

发行人注册表与行业映射中的每条记录都必须保存结构化 `source_url / as_of` 证据，并逐对象匹配仓库中央 authority；自由文本不再满足证据契约。发行人身份只允许 `cik:<10-digits>` 或 `lei:<20-character-LEI>`；CIK 必须绑定同一编号的 SEC URL，LEI 必须绑定同一编号的 GLEIF URL。注册表拒绝重复发行人 ID、重复规范公司名和重复来源 ID；每个 SEDOL、CUSIP、ISIN 或 ticker alias 必须指向 authority 中已存在、且自指的 `canonical_security_id`，alias 与 canonical 必须共用发行人。因此跨基金的 SEDOL↔CUSIP 以及 Alphabet A/C 都按同一实体累计。衍生品映射中的每个组件必须同时存在于同一映射快照并直接解析为普通证券；中央classification authority中的组件还必须是中央issuer authority内的canonical证券，缺失、嵌套或循环组件即使尚未被当前持仓引用也不能进入只增不改authority。Bundle发行人子集若暂未包含某个已批准组件，分类仍可独立计算，但该组件权重必须进入发行人未知。可识别的管理人原始Sector/Industry必须与统一映射一致；原始分类缺失时也只能引用中央classification authority，不能由Bundle自述降低风险。

## 独立缺口与最坏情形

发行人未知权重和分类未知权重分别计算：

- `issuer_unknown_weight` 只进入单一发行人最坏情形上界；
- `classification_unknown_weight` 只进入科技与半导体最坏情形上界；
- 不再用一个 `min()` 残差混合两个不同缺口。

衍生品名义敞口可能使 `gross_lookthrough_exposure` 高于非现金市值；覆盖率以实际总经济敞口为分母。

## Green 关闭标准

验证器只在以下条件全部成立时输出 `DATA GATE PASS`：

1. 三只基金在同一审核日采集、`source_as_of` 完全一致且满足时效上限；
2. 官方产品 URL、原始文件实哈希、确定性解析结果、中央 authority、Bundle 身份/分类快照、账户、Candidate 与 Packet 哈希全部通过；
3. 账户快照不晚于 Packet、活动订单为零，Candidate 已创建且未失效；`ADD` 拟议金额不超过上限并可重算交易后权重，`HOLD` 使用当前权重和零金额；SOXX 为正且不高于 3%；
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

Packet通过只是SOXX解冻的必要条件之一。现行 NYSE Semiconductor Index 完整方法证据仍须独立完成，Registry 仍须经治理更新；此后每次潜在追加仍需实时 IBKR、未过期 `ADD` Candidate Packet、完整 IC `APPROVE` 与账户所有者人工下单。`HOLD` Bundle 永远不构成交易授权。
