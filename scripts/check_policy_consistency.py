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


def main() -> None:
    dictionary = "08-Data/DATA_DICTIONARY.md"
    require(
        dictionary,
        r"SPYM \(57\%-A_{basis}\)",
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
    require("README.md", "# Investment OS v3.4.2")
    require("PRODUCTION.md", "# Investment OS v3.4.2 — Production Contract")
    require("07-Releases/v3.4.2.md", "本发布不授权任何订单")
    for path in (
        "08-Data/DATA_QUALITY.md",
        "08-Data/DATA_REGISTRY.md",
        "08-Data/README.md",
        "BUGLOG.md",
        "Decision-Log.md",
        "README.md",
    ):
        require(path, "Bundle v1.3")
    require(
        "08-Data/README.md",
        "REGISTRIES/LOOKTHROUGH_ISSUER_AUTHORITY.json",
        "REGISTRIES/LOOKTHROUGH_CLASSIFICATION_AUTHORITY.json",
    )
    require(
        "08-Data/DATA_REGISTRY.md",
        "中央Issuer Authority",
        "中央Classification Authority",
    )
    require(
        "08-Data/DATA_QUALITY.md",
        "只增不改中央authority",
    )
    require(
        "08-Data/LOOKTHROUGH_PACKET.md",
        "验证通过不改变 Position Registry",
        "source_sha256",
        "schema_version`：当前固定为 `1.3",
        "account_snapshot_sha256",
        "candidate_sha256",
        "issuer_registry_sha256",
        "mapping_sha256",
        "逐行等于验证器从归档字节解析的结果",
        "exposure_weight",
        "科技严格低于 50%",
        "Packet通过只是SOXX解冻的必要条件之一",
    )
    require(
        "08-Data/LOOKTHROUGH_PACKET_TEMPLATE.json",
        '"schema_version": "1.3"',
        '"issuer_registry_path": "issuer-registry.json"',
        '"issuer_registry_sha256": ""',
        '"source_identifiers": []',
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
        "08-Data/REGISTRIES/LOOKTHROUGH_ISSUER_AUTHORITY.json",
        '"authority_id": "lookthrough-issuer-authority"',
        '"schema_version": "1.1"',
    )
    require(
        "08-Data/REGISTRIES/LOOKTHROUGH_CLASSIFICATION_AUTHORITY.json",
        '"authority_id": "lookthrough-classification-authority"',
        '"schema_version": "1.2"',
        '"taxonomy": "GICS"',
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
        'SCHEMA_VERSION = "1.3"',
        'MAPPING_VERSION = "1.2"',
        'ISSUER_REGISTRY_VERSION = "1.1"',
        "duplicate JSON key",
        "source_sha256 does not match archived source bytes",
        "does not match parsed archived source",
        "derivative requires audited look-through components",
        "post-trade account scenario",
        "canonical_security_id",
        "source_identifiers",
        "reviewed issuer authority",
        "reviewed classification authority",
        "validate_authority_catalogs",
    )
    require(
        "scripts/parse_lookthrough_sources.py",
        '"SPYM": "ssga-xlsx-v1"',
        '"QQQM": "invesco-csv-v1"',
        '"SOXX": "ishares-csv-v1"',
        '"holding ticker"',
        '"security identifier"',
        '"date"',
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
        "SPYM 3 Holdings: As of 29-Jul-2026",
        "missing raw labels cannot authorize a bundle-local false classification",
        "max_issuer_known_weight",
    )
    require(
        "scripts/check_lookthrough_history.py",
        "Historical look-through evidence is append-only",
        "LOOKTHROUGH_ISSUER_AUTHORITY.json",
        "LOOKTHROUGH_CLASSIFICATION_AUTHORITY.json",
        "is not append-only",
    )
    forbid("02-Operating-System/Monthly-Workflow.md", "SOXX 等 Observation")
    forbid("03-Transition/Transition-Plan.md", r"现金、\(A\)、目标缺口")

    if CURRENT_EXECUTION_CAP > CURRENT_STAGE:
        raise AssertionError("current execution cap exceeds current stage")
    allocation_tests()
    benchmark_interest_tests()
    print("Policy consistency checks passed.")


if __name__ == "__main__":
    main()
