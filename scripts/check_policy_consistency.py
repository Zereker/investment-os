#!/usr/bin/env python3
"""Fail CI when Production policy formulas, state or guardrails diverge."""

from math import isfinite, nan, inf
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = (0.06, 0.10, 0.125, 0.15)
EXECUTION_CAPS = (0.03, 0.045, 0.06, 0.10, 0.125, 0.15)
CURRENT_STAGE = 0.06
CURRENT_EXECUTION_CAP = 0.03


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        if needle not in text:
            raise AssertionError(f"{path}: missing required text: {needle}")


def forbid(path: str, *needles: str) -> None:
    text = read(path)
    for needle in needles:
        if needle in text:
            raise AssertionError(f"{path}: forbidden stale text: {needle}")


def close_to_member(value: float, allowed: tuple[float, ...]) -> bool:
    return any(abs(value - item) <= 1e-12 for item in allowed)


def allocation(actual: float, stage: float, execution_cap: float) -> dict[str, float]:
    values = (actual, stage, execution_cap)
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) for value in values):
        raise ValueError("weights must be finite numbers")
    if not 0 <= actual <= 0.15:
        raise ValueError("A_actual outside [0, 15%]")
    if not close_to_member(stage, STAGES):
        raise ValueError("illegal A_stage")
    if not close_to_member(execution_cap, EXECUTION_CAPS):
        raise ValueError("illegal A_execution_cap")
    if execution_cap > stage + 1e-12:
        raise ValueError("execution cap exceeds stage")

    basis = max(actual, stage)
    reserve = max(stage - actual, 0.0)
    targets = {
        "cash_base": 0.15,
        "stage_reserve": reserve,
        "qqqm": 0.28,
        "spym": 0.57 - basis,
        "soxx": actual,
    }
    if not all(0.0 <= value <= 1.0 for value in targets.values()):
        raise ValueError(f"target outside [0, 100%]: {targets}")
    if abs(sum(targets.values()) - 1.0) > 1e-12:
        raise ValueError(f"allocation does not sum to 100%: {targets}")
    return targets


def next_execution_cap(current: float, proposed: float) -> bool:
    if not (close_to_member(current, EXECUTION_CAPS) and close_to_member(proposed, EXECUTION_CAPS)):
        return False
    old = min(range(len(EXECUTION_CAPS)), key=lambda i: abs(EXECUTION_CAPS[i] - current))
    new = min(range(len(EXECUTION_CAPS)), key=lambda i: abs(EXECUTION_CAPS[i] - proposed))
    return new == old + 1


def allocation_tests() -> None:
    valid = [
        (0.00, 0.06, 0.03), (0.03, 0.06, 0.03), (0.06, 0.06, 0.06),
        (0.08, 0.10, 0.06), (0.10, 0.10, 0.10), (0.12, 0.125, 0.10),
        (0.125, 0.125, 0.125), (0.15, 0.15, 0.15),
    ]
    for args in valid:
        allocation(*args)

    invalid = [
        (-0.01, 0.06, 0.03), (0.16, 0.15, 0.15), (nan, 0.06, 0.03),
        (inf, 0.06, 0.03), (0.03, 0.07, 0.03), (0.03, 0.06, 0.04),
        (0.03, 0.06, 0.10), (True, 0.06, 0.03),
    ]
    for args in invalid:
        try:
            allocation(*args)
        except ValueError:
            pass
        else:
            raise AssertionError(f"illegal allocation accepted: {args}")

    if not next_execution_cap(0.03, 0.045):
        raise AssertionError("next checkpoint rejected")
    for proposed in (0.03, 0.06, 0.10, nan):
        if next_execution_cap(0.03, proposed):
            raise AssertionError(f"illegal checkpoint transition accepted: 3% -> {proposed}")


def benchmark_interest_tests() -> None:
    principal = 20_000.0
    accrued = 0.0
    rate = 0.036
    first = max(principal - 10_000.0, 0.0) * rate / 360.0
    accrued += first
    second = max(principal - 10_000.0, 0.0) * rate / 360.0
    if abs(first - second) > 1e-12:
        raise AssertionError("unposted accrual compounded")
    nav_before_posting = principal + accrued
    posting = accrued
    principal += posting
    accrued -= posting
    if abs((principal + accrued) - nav_before_posting) > 1e-12:
        raise AssertionError("posting conversion changed benchmark NAV")


def valuation_tier(percentile: float) -> str:
    if not isinstance(percentile, (int, float)) or isinstance(percentile, bool) or not isfinite(percentile):
        raise ValueError("valuation percentile must be finite")
    if not 0 <= percentile <= 100:
        raise ValueError("valuation percentile outside [0, 100]")
    if percentile < 20:
        return "CHEAP"
    if percentile < 70:
        return "FAIR"
    if percentile < 90:
        return "EXPENSIVE"
    return "VERY EXPENSIVE"


def valuation_action(tier: str) -> tuple[bool, bool, bool]:
    actions = {
        "CHEAP": (True, True, True),
        "FAIR": (True, True, False),
        "EXPENSIVE": (True, True, False),
        "VERY EXPENSIVE": (True, False, False),
        "N/A": (True, True, False),
    }
    if tier not in actions:
        raise ValueError("unknown valuation tier")
    return actions[tier]


def valuation_policy_tests() -> None:
    expected = {
        0: "CHEAP", 19.999: "CHEAP", 20: "FAIR", 69.999: "FAIR",
        70: "EXPENSIVE", 89.999: "EXPENSIVE", 90: "VERY EXPENSIVE",
        100: "VERY EXPENSIVE",
    }
    for percentile, tier in expected.items():
        if valuation_tier(percentile) != tier:
            raise AssertionError(f"wrong valuation tier at {percentile}")
    for invalid in (-0.01, 100.01, nan, inf, True):
        try:
            valuation_tier(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"illegal valuation percentile accepted: {invalid}")
    if valuation_action("CHEAP") != (True, True, True):
        raise AssertionError("CHEAP action mapping changed")
    if valuation_action("EXPENSIVE") != (True, True, False):
        raise AssertionError("EXPENSIVE must preserve D and B")
    if valuation_action("VERY EXPENSIVE") != (True, False, False):
        raise AssertionError("VERY EXPENSIVE may delay B but must preserve D")
    if valuation_action("N/A") != (True, True, False):
        raise AssertionError("N/A must preserve strategic D and B")


def main() -> None:
    dictionary = "08-Data/DATA_DICTIONARY.md"
    require(
        dictionary,
        r"SPYM \(57\%-A_{basis}\)",
        r"\(D_{max}=\min(F,G_0)\)",
        r"\(D\le D_{max}\)",
        r"\(S=\max(C-(15\%+U)\times V,0)\)",
        r"P_{B,m,0}+A_{B,m,0}=15\%\times V_{B,m,0}",
        r"E_{B,d}=\max(P^*_{B,d}-10000,0)",
        r"A_{B,d}=A^*_{B,d}+i_{B,d}",
        "应计利息计入基准NAV，但在正式入账前不得进入计息本金",
        "`source_as_of`完全相同才可为Green",
    )
    forbid(
        dictionary,
        r"SPYM \(57\%-A\)",
        r"\(S=\max(C-15\%\times V,0)\)",
        r"C_{B,d}=15\%\times V_{B,d}",
        r"C_{B,m,d}=C^-_{B,m,d}+i_{B,m,d}",
    )

    active_lifecycle_files = [
        "README.md", "PRODUCTION.md",
        "02-Operating-System/Daily-Review.md",
        "02-Operating-System/Decision-Checklist.md",
        "02-Operating-System/Monthly-Workflow.md",
        "02-Operating-System/Weekly-Review.md",
        "03-Transition/Transition-Dashboard.md",
        "03-Transition/Transition-Plan.md",
        "04-Alpha/Alpha-Framework.md",
        "04-Alpha/Position-Registry.md",
        "04-Alpha/Research/SOXX.md",
    ]
    for path in active_lifecycle_files:
        forbid(path, "Approved / Frozen", "Registry先更新为`Approved / Add Candidate`")

    require(
        "04-Alpha/Position-Registry.md",
        r"当前\(A_{execution\_cap}=3\%\)",
        "3%→4.5%→6%→10%→12.5%→15%",
        "同一次IC不得既跳档又执行交易",
        "短时效的`Add Candidate` IC Packet",
        "`approved_as_of`", "`data_as_of`", "`expires_at`",
        "`max_notional`", "`max_post_trade_weight`",
        "最迟于当日常规收盘失效",
    )
    require(
        "04-Alpha/Research/SOXX.md",
        "Incomplete — INDEX METHODOLOGY EVIDENCE",
        "NYSE Semiconductor Index",
    )
    forbid(
        "04-Alpha/Research/SOXX.md",
        "indexes.nasdaq.com",
        "前三大权重上限分别为12%、10%、8%",
    )
    require("README.md", "# Investment OS v3.5.1")
    require("PRODUCTION.md", "# Investment OS v3.5.1 — Production Contract")
    require("07-Releases/v3.4.2.md", "本发布不授权任何订单")
    require("07-Releases/v3.5.md", "本发布不写入当前价格、P/E或当日动作，不授权任何订单")
    require(
        "02-Operating-System/ETF-Valuation-Framework.md",
        "本框架只覆盖 `SPYM / QQQM / SOXX`",
        "`p < 20`",
        "`20 ≤ p < 70`",
        "`70 ≤ p < 90`",
        "`p ≥ 90`",
        "估值贵本身不能触发卖出",
        "至少需要连续 5 年、60 个互不重复的月末观察值",
        "Trailing P/E 时不得判定为便宜",
        "仅当生产级高质量信号确认时才可延缓 `B`",
        "板块代理、跨口径序列或不足 60 个月的数据只输出 `PROXY CAUTION`",
    )
    require(
        "02-Operating-System/Monthly-Workflow.md",
        "估值不得关闭例行 `D`",
        "`B`默认按既定迁移计划执行",
        "`N/A / VALUATION UNAVAILABLE`或`PROXY CAUTION`不阻塞Routine DCA",
    )
    require(
        "08-Data/DATA_QUALITY.md",
        "Routine DCA `D`与既定战略基线`B`照常",
        "低质量估值不得通过单边关闭`B`造成现金拖累",
    )
    require("07-Releases/v3.5.1.md", "本发布不授权任何订单")
    for path in (
        "README.md",
        "PRODUCTION.md",
        "02-Operating-System/Daily-Review.md",
        "02-Operating-System/Monthly-Workflow.md",
        "02-Operating-System/Deployment-Framework.md",
        "02-Operating-System/Weekly-Review.md",
        "03-Transition/Transition-Dashboard.md",
    ):
        forbid(path, "Valuation Score", "Opportunity Score")
    for path in (
        "08-Data/DATA_QUALITY.md",
        "08-Data/DATA_REGISTRY.md",
        "08-Data/README.md",
    ):
        require(path, "Bundle v1.5")
    for path in ("BUGLOG.md", "Decision-Log.md", "README.md"):
        require(path, "Bundle v1.4")
    require(
        "README.md",
        "仓库不维护重复的中央证券数据库",
        "普通数据变化不更新项目",
    )
    require(
        "PRODUCTION.md",
        "仓库不维护行情、ETF成分、issuer或GICS中央数据库",
        "普通巡检不写仓库",
    )
    require(
        "Decision-Log.md",
        "运行时多源数据与决策留证",
        "删除仓库中的中央issuer/GICS全量表",
    )
    require(
        "08-Data/LOOKTHROUGH_PACKET.md",
        "验证通过不改变 Position Registry",
        "source_sha256",
        "schema_version`：当前固定为 `1.5",
        "account_snapshot_sha256",
        "candidate_sha256",
        "issuer_registry_sha256",
        "mapping_sha256",
        "逐行等于验证器从归档字节解析的结果",
        "exposure_weight",
        "科技严格低于 50%",
        "`HOLD` Bundle 永远不构成交易授权",
        "Packet通过只是SOXX解冻的必要条件之一",
        "仓库不维护中央 issuer / GICS 数据库",
        "普通巡检不写仓库",
    )
    require(
        "08-Data/LOOKTHROUGH_PACKET_TEMPLATE.json",
        '"schema_version": "1.5"',
        '"issuer_registry_path": "issuer-registry.json"',
        '"issuer_registry_sha256": ""',
        '"source_identifiers": []',
        '"status": "complete"',
        '"source_format": "invesco-json-v1"',
        '"other": 0',
    )
    require(
        "08-Data/LOOKTHROUGH_ISSUER_REGISTRY_TEMPLATE.json",
        '"schema_version": "1.1"',
        '"issuer_group_id": "cik:0001652044"',
        '"security_id": "CUSIP:02079K305"',
        '"security_id": "CUSIP:02079K107"',
        '"canonical_security_id": "CUSIP:02079K305"',
        '"security_id": "SEDOL:BYVY8G0"',
    )
    require(
        "08-Data/LOOKTHROUGH_ACCOUNT_TEMPLATE.json",
        '"schema_version": "1.2"',
        '"direct_holdings": []',
    )
    require(
        "08-Data/LOOKTHROUGH_MAPPING_TEMPLATE.json",
        '"schema_version": "1.2"',
        '"source_url": ""',
        '"as_of": "YYYY-MM-DD"',
    )
    require(
        ".github/workflows/policy-consistency.yml",
        "python3 scripts/validate_lookthrough_packet.py --self-test",
        "python3 scripts/test_lookthrough_adversarial.py",
        "--scan-root 08-Data/SNAPSHOTS/lookthrough",
        "python3 scripts/check_lookthrough_history.py",
        "fetch-depth: 0",
    )
    require(
        "scripts/validate_lookthrough_packet.py",
        'SCHEMA_VERSION = "1.5"',
        'SUPPORTED_SCHEMA_VERSIONS = {"1.4", SCHEMA_VERSION}',
        'MAPPING_VERSION = "1.2"',
        'ISSUER_REGISTRY_VERSION = "1.1"',
        'ACCOUNT_VERSION = "1.2"',
        'SUPPORTED_ACCOUNT_VERSIONS = {"1.1", ACCOUNT_VERSION}',
        'CANDIDATE_VERSION = "1.1"',
        "duplicate JSON key",
        "source_sha256 does not match archived source bytes",
        "does not match parsed archived source",
        "derivative requires audited look-through components",
        "does not match account scenario",
        "canonical_security_id",
        "source_identifiers",
        "mapping derivative component is absent from the same snapshot",
        "issuer_registry canonical security is absent",
        "candidate must be an ADD or HOLD scenario for SOXX",
        "sources_complete_same_date",
        "soxx_at_or_below_3",
        "direct_holdings",
        'verdict = "POLICY GATE FAIL"',
    )
    require(
        "scripts/parse_lookthrough_sources.py",
        '"SPYM": "ssga-xlsx-v1"',
        '"QQQM": "invesco-json-v1"',
        '"SOXX": "ishares-csv-v1"',
        '"effectiveDate"',
        '"holdings"',
        "_invesco_json_rows",
        "CUSIP:",
        "%d-%b-%Y",
        "derivative has zero economic exposure",
    )
    require(
        "scripts/test_lookthrough_adversarial.py",
        "packet holdings unrelated to archived bytes",
        "SOXX erased as zero-exposure other instruments",
        "Alphabet A and C split across issuer identities",
        "SEDOL and canonical CUSIP split across issuer identities",
        "derivative component uses a free issuer id",
        "future-dated 2099 bundle",
        "official download unavailable at retrieval time",
        "SPYM 3 Holdings: As of 29-Jul-2026",
        "bundle mapping cannot violate controlled GICS semantics",
        "max_issuer_known_weight",
    )
    require(
        "scripts/check_lookthrough_history.py",
        "Historical look-through evidence is append-only",
        "status != \"A\"",
    )
    for path in (
        "08-Data/README.md",
        "08-Data/DATA_REGISTRY.md",
        "08-Data/DATA_QUALITY.md",
        "08-Data/LOOKTHROUGH_PACKET.md",
        "scripts/validate_lookthrough_packet.py",
        "scripts/check_lookthrough_history.py",
    ):
        forbid(
            path,
            "LOOKTHROUGH_ISSUER_AUTHORITY",
            "LOOKTHROUGH_CLASSIFICATION_AUTHORITY",
            "reviewed issuer authority",
            "reviewed classification authority",
        )
    forbid("02-Operating-System/Monthly-Workflow.md", "SOXX 等 Observation")
    forbid("03-Transition/Transition-Plan.md", r"现金、\(A\)、目标缺口")

    if CURRENT_EXECUTION_CAP > CURRENT_STAGE:
        raise AssertionError("current execution cap exceeds current stage")
    allocation_tests()
    benchmark_interest_tests()
    valuation_policy_tests()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
