#!/usr/bin/env python3
"""Validate immutable ETF look-through evidence bundles without third parties."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

FUNDS = ("SPYM", "QQQM", "SOXX")
OFFICIAL_HOSTS = {
    "SPYM": ("ssga.com",),
    "QQQM": ("invesco.com",),
    "SOXX": ("ishares.com", "blackrock.com"),
}
TECH = "Information Technology"
SEMI = "Semiconductors & Semiconductor Equipment"
OTHER_INDUSTRY = "Other / non-semiconductor"
GICS_SECTORS = {
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    TECH,
    "Materials",
    "Real Estate",
    "Utilities",
}
INSTRUMENT_TYPES = {"equity", "fund", "derivative", "cash", "other"}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PACKET_ID = re.compile(r"^lookthrough-\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]{0,63}$")
SCHEMA_VERSION = "1.1"
MAPPING_VERSION = "1.0"
ACCOUNT_VERSION = "1.0"
EPS = 1e-9
ROUNDING_TOLERANCE = 5e-4  # 5 bps; accepts an official 100.01% rounded total.
MAX_SOURCE_AGE_DAYS = 7
MAX_PACKET_BYTES = 20 * 1024 * 1024
MAX_MAPPING_BYTES = 10 * 1024 * 1024
MAX_ACCOUNT_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_HOLDINGS_PER_FUND = 20_000
CURRENT_EXECUTION_CAP = 0.03


class PacketError(ValueError):
    pass


def fail(message: str) -> None:
    raise PacketError(message)


def strict_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path, max_bytes: int, label: str) -> dict:
    if path.is_symlink():
        fail(f"{label} must not be a symlink")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise PacketError(f"{label} cannot be read: {exc}") from exc
    if size > max_bytes:
        fail(f"{label} exceeds {max_bytes} bytes")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise PacketError(f"{label} is not strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        fail(f"{label} root must be an object")
    return value


def digest_file(path: Path, max_bytes: int, label: str) -> str:
    if path.is_symlink():
        fail(f"{label} must not be a symlink")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise PacketError(f"{label} cannot be read: {exc}") from exc
    if size > max_bytes:
        fail(f"{label} exceeds {max_bytes} bytes")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise PacketError(f"{label} cannot be read: {exc}") from exc
    return digest.hexdigest()


def bundle_file(bundle: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        fail(f"{label} must be a non-empty POSIX relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        fail(f"{label} must stay inside the evidence bundle")
    root = bundle.resolve()
    resolved = (bundle / relative).resolve()
    if resolved == root or root not in resolved.parents:
        fail(f"{label} must stay inside the evidence bundle")
    return resolved


def require_keys(value: dict, keys: set[str], label: str) -> None:
    if set(value) != keys:
        missing = sorted(keys - set(value))
        extra = sorted(set(value) - keys)
        fail(f"{label} keys mismatch; missing={missing}, extra={extra}")


def number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        fail(f"{field} must be finite")
    return result


def bounded(value: object, field: str, low: float, high: float) -> float:
    result = number(value, field)
    if result < low - EPS or result > high + EPS:
        fail(f"{field} must be within [{low}, {high}]")
    return result


def iso_date(value: object, field: str) -> date:
    if not isinstance(value, str):
        fail(f"{field} must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise PacketError(f"{field} must be YYYY-MM-DD") from exc


def iso_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        fail(f"{field} must be an ISO 8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PacketError(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        fail(f"{field} must include a timezone")
    return parsed


def require_sha(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        fail(f"{field} must be a lowercase SHA-256")
    return value


def official_url(ticker: str, value: object, field: str, *, allow_test: bool) -> None:
    if not isinstance(value, str):
        fail(f"{field} must be an official HTTPS URL")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower().rstrip(".")
    allowed = OFFICIAL_HOSTS[ticker]
    if parsed.scheme != "https" or not host:
        fail(f"{field} must be an official HTTPS URL")
    if allow_test and host == "example.invalid":
        return
    if not any(host == suffix or host.endswith("." + suffix) for suffix in allowed):
        fail(f"{field} host is not approved for {ticker}: {host}")


def canonical_sha256(packet: dict) -> str:
    body = copy.deepcopy(packet)
    body["packet_sha256"] = ""
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_reference(
    bundle: Path,
    reference: object,
    *,
    label: str,
    max_bytes: int,
) -> tuple[Path, dict]:
    if not isinstance(reference, dict):
        fail(f"{label} must be an object")
    require_keys(reference, {"path", "sha256"}, label)
    path = bundle_file(bundle, reference["path"], f"{label}.path")
    expected = require_sha(reference["sha256"], f"{label}.sha256")
    actual = digest_file(path, max_bytes, label)
    if actual != expected:
        fail(f"{label}.sha256 does not match archived bytes")
    return path, read_json(path, max_bytes, label)


def load_mapping(bundle: Path, path_value: object, digest_value: object) -> dict[str, dict]:
    _, mapping = validate_reference(
        bundle,
        {"path": path_value, "sha256": digest_value},
        label="mapping",
        max_bytes=MAX_MAPPING_BYTES,
    )
    require_keys(mapping, {"schema_version", "mapping_id", "taxonomy", "records"}, "mapping")
    if mapping["schema_version"] != MAPPING_VERSION:
        fail(f"mapping.schema_version must be {MAPPING_VERSION}")
    if not isinstance(mapping["mapping_id"], str) or not mapping["mapping_id"].strip():
        fail("mapping.mapping_id is required")
    if mapping["taxonomy"] != "GICS":
        fail("mapping.taxonomy must be GICS")
    records = mapping["records"]
    if not isinstance(records, list) or not records:
        fail("mapping.records must be a non-empty array")
    by_security: dict[str, dict] = {}
    for index, record in enumerate(records):
        label = f"mapping.records[{index}]"
        if not isinstance(record, dict):
            fail(f"{label} must be an object")
        require_keys(
            record,
            {
                "security_id",
                "issuer_group_id",
                "normalized_sector",
                "normalized_industry",
                "derivative_components",
                "evidence",
            },
            label,
        )
        security_id = record["security_id"]
        if not isinstance(security_id, str) or not security_id.strip():
            fail(f"{label}.security_id is required")
        if security_id != security_id.strip().upper():
            fail(f"{label}.security_id must be canonical uppercase without edge whitespace")
        if security_id in by_security:
            fail(f"mapping has duplicate security_id: {security_id}")
        evidence = record["evidence"]
        if not isinstance(evidence, str) or not evidence.strip():
            fail(f"{label}.evidence is required")
        components = record["derivative_components"]
        direct = components is None
        if direct:
            issuer = record["issuer_group_id"]
            sector = record["normalized_sector"]
            industry = record["normalized_industry"]
            if not isinstance(issuer, str) or not issuer.strip():
                fail(f"{label}.issuer_group_id is required")
            validate_taxonomy(sector, industry, label)
        else:
            if any(
                record[key] is not None
                for key in ("issuer_group_id", "normalized_sector", "normalized_industry")
            ):
                fail(f"{label} derivative mapping must use components, not direct fields")
            validate_components(components, label)
        by_security[security_id] = record
    return by_security


def validate_taxonomy(sector: object, industry: object, label: str) -> None:
    if sector not in GICS_SECTORS:
        fail(f"{label}.normalized_sector is not in the controlled GICS sector set")
    if industry not in {SEMI, OTHER_INDUSTRY}:
        fail(f"{label}.normalized_industry is not in the controlled industry set")
    if industry == SEMI and sector != TECH:
        fail(f"{label} semiconductor industry must map to Information Technology")


def validate_components(value: object, label: str) -> None:
    if not isinstance(value, list) or not value:
        fail(f"{label}.derivative_components must be a non-empty array or null")
    total = 0.0
    for index, component in enumerate(value):
        prefix = f"{label}.derivative_components[{index}]"
        if not isinstance(component, dict):
            fail(f"{prefix} must be an object")
        require_keys(
            component,
            {"issuer_group_id", "normalized_sector", "normalized_industry", "weight"},
            prefix,
        )
        issuer = component["issuer_group_id"]
        if not isinstance(issuer, str) or not issuer.strip():
            fail(f"{prefix}.issuer_group_id is required")
        validate_taxonomy(
            component["normalized_sector"], component["normalized_industry"], prefix
        )
        total += bounded(component["weight"], f"{prefix}.weight", 0, 1)
    if abs(total - 1) > ROUNDING_TOLERANCE:
        fail(f"{label}.derivative_components weights must sum to 1 within 5 bps")


def load_account(
    bundle: Path,
    path_value: object,
    digest_value: object,
    packet: dict,
    review_date: date,
) -> dict[str, float]:
    _, account = validate_reference(
        bundle,
        {"path": path_value, "sha256": digest_value},
        label="account_scenario",
        max_bytes=MAX_ACCOUNT_BYTES,
    )
    require_keys(
        account,
        {
            "schema_version",
            "account_snapshot_id",
            "observed_at",
            "candidate_packet_id",
            "candidate_ticker",
            "candidate_notional",
            "nav",
            "current_market_values",
        },
        "account_scenario",
    )
    if account["schema_version"] != ACCOUNT_VERSION:
        fail(f"account_scenario.schema_version must be {ACCOUNT_VERSION}")
    if not isinstance(account["account_snapshot_id"], str) or not account[
        "account_snapshot_id"
    ].strip():
        fail("account_scenario.account_snapshot_id is required")
    observed = iso_datetime(account["observed_at"], "account_scenario.observed_at")
    if observed.date() != review_date:
        fail("account_scenario must be observed on review_date")
    if account["candidate_packet_id"] != packet.get("candidate_packet_id"):
        fail("candidate_packet_id does not match account scenario")
    if account["candidate_ticker"] != "SOXX":
        fail("candidate_ticker must be SOXX")
    nav = number(account["nav"], "account_scenario.nav")
    candidate = number(account["candidate_notional"], "account_scenario.candidate_notional")
    if nav <= 0 or candidate <= 0:
        fail("account_scenario nav and candidate_notional must be positive")
    current = account["current_market_values"]
    if not isinstance(current, dict):
        fail("account_scenario.current_market_values must be an object")
    require_keys(current, {"cash", *FUNDS}, "account_scenario.current_market_values")
    values = {
        key: bounded(value, f"account_scenario.current_market_values.{key}", 0, nav)
        for key, value in current.items()
    }
    if abs(sum(values.values()) - nav) > max(0.01, nav * EPS):
        fail("account_scenario current market values must reconcile to nav")
    if candidate > values["cash"] + EPS:
        fail("candidate_notional exceeds cash")
    values["cash"] -= candidate
    values["SOXX"] += candidate
    return {key: value / nav for key, value in values.items()}


def expand_mapping(record: dict) -> list[tuple[str, str, str, float]]:
    components = record["derivative_components"]
    if components is None:
        return [
            (
                record["issuer_group_id"],
                record["normalized_sector"],
                record["normalized_industry"],
                1.0,
            )
        ]
    total = sum(float(item["weight"]) for item in components)
    return [
        (
            item["issuer_group_id"],
            item["normalized_sector"],
            item["normalized_industry"],
            float(item["weight"]) / total,
        )
        for item in components
    ]


def check_raw_mapping(record: dict, holding: dict, label: str) -> None:
    """Prevent a normalized map from contradicting recognizable manager labels."""
    if record["derivative_components"] is not None:
        return
    raw_sector = holding["raw_sector"]
    raw_industry = holding["raw_industry"]
    if raw_sector is not None and not isinstance(raw_sector, str):
        fail(f"{label}.raw_sector must be a string or null")
    if raw_industry is not None and not isinstance(raw_industry, str):
        fail(f"{label}.raw_industry must be a string or null")
    sector_key = " ".join((raw_sector or "").lower().replace("&", "and").split())
    sector_aliases = {
        "communication services": "Communication Services",
        "consumer discretionary": "Consumer Discretionary",
        "consumer staples": "Consumer Staples",
        "energy": "Energy",
        "financials": "Financials",
        "health care": "Health Care",
        "healthcare": "Health Care",
        "industrials": "Industrials",
        "information technology": TECH,
        "technology": TECH,
        "materials": "Materials",
        "real estate": "Real Estate",
        "utilities": "Utilities",
    }
    expected_sector = sector_aliases.get(sector_key)
    if expected_sector and record["normalized_sector"] != expected_sector:
        fail(f"{label} normalized sector contradicts raw manager sector")
    if "semiconductor" in (raw_industry or "").lower():
        if record["normalized_industry"] != SEMI:
            fail(f"{label} normalized industry contradicts raw semiconductor label")


def evaluate(
    packet: dict,
    packet_path: Path,
    *,
    allow_test: bool = False,
) -> tuple[dict[str, float], dict[str, bool], str]:
    if not isinstance(packet, dict):
        fail("packet root must be an object")
    expected_keys = {
        "schema_version",
        "packet_id",
        "review_date",
        "observed_at",
        "candidate_packet_id",
        "weight_basis",
        "account_scenario_path",
        "account_snapshot_sha256",
        "mapping_path",
        "mapping_sha256",
        "portfolio_weights",
        "funds",
        "metrics",
        "gates",
        "verdict",
        "packet_sha256",
    }
    if allow_test:
        expected_keys.add("test_only")
    require_keys(packet, expected_keys, "packet")
    if packet.get("test_only") is True and not allow_test:
        fail("test_only packet cannot enter Production")
    if allow_test and packet.get("test_only") is not True:
        fail("self-test packet must set test_only=true")
    if packet["schema_version"] != SCHEMA_VERSION:
        fail(f"schema_version must be {SCHEMA_VERSION}")
    if packet["weight_basis"] != "post_trade":
        fail("weight_basis must be post_trade")

    review_date = iso_date(packet["review_date"], "review_date")
    observed_at = iso_datetime(packet["observed_at"], "observed_at")
    if observed_at.date() != review_date:
        fail("observed_at calendar date must equal review_date")
    packet_id = packet["packet_id"]
    if not isinstance(packet_id, str) or not PACKET_ID.fullmatch(packet_id):
        fail("packet_id format is invalid")
    if not packet_id.startswith(f"lookthrough-{review_date.isoformat()}-"):
        fail("packet_id date must equal review_date")
    candidate_id = packet["candidate_packet_id"]
    if not isinstance(candidate_id, str) or not candidate_id.strip():
        fail("candidate_packet_id is required")

    bundle = packet_path.parent.resolve()
    if bundle.name != packet_id or bundle.parent.name != review_date.isoformat():
        fail("packet must be stored at <review_date>/<packet_id>/packet.json")
    if packet_path.name != "packet.json":
        fail("Production packet filename must be packet.json")

    mapping = load_mapping(bundle, packet["mapping_path"], packet["mapping_sha256"])
    account_weights = load_account(
        bundle,
        packet["account_scenario_path"],
        packet["account_snapshot_sha256"],
        packet,
        review_date,
    )
    portfolio = packet["portfolio_weights"]
    if not isinstance(portfolio, dict):
        fail("portfolio_weights must be an object")
    require_keys(portfolio, {"cash", *FUNDS}, "portfolio_weights")
    portfolio_weights = {
        key: bounded(value, f"portfolio_weights.{key}", 0, 1)
        for key, value in portfolio.items()
    }
    if abs(sum(portfolio_weights.values()) - 1) > EPS:
        fail("portfolio_weights must sum to 1")
    for key in portfolio_weights:
        if abs(portfolio_weights[key] - account_weights[key]) > EPS:
            fail(f"portfolio_weights.{key} does not match post-trade account scenario")
    if portfolio_weights["SPYM"] <= EPS or portfolio_weights["QQQM"] <= EPS:
        fail("SPYM and QQQM post-trade weights must be positive")
    if portfolio_weights["SOXX"] <= EPS:
        fail("SOXX post-trade weight must be positive")
    if portfolio_weights["SOXX"] > CURRENT_EXECUTION_CAP + EPS:
        fail("SOXX post-trade weight exceeds current 3% execution cap")

    funds = packet["funds"]
    if not isinstance(funds, list) or len(funds) != 3:
        fail("funds must contain exactly three records")
    by_ticker = {}
    for fund in funds:
        if not isinstance(fund, dict):
            fail("each fund must be an object")
        require_keys(
            fund,
            {
                "ticker",
                "source_name",
                "source_url",
                "source_as_of",
                "retrieved_at",
                "source_file",
                "source_sha256",
                "holdings",
            },
            "fund",
        )
        ticker = fund["ticker"]
        if ticker not in FUNDS or ticker in by_ticker:
            fail("fund tickers must be unique SPYM, QQQM and SOXX")
        by_ticker[ticker] = fund
    if set(by_ticker) != set(FUNDS):
        fail("fund tickers must be exactly SPYM, QQQM and SOXX")

    source_dates = set()
    issuer_weights: dict[str, float] = {}
    tech_known = semi_known = issuer_unknown = class_unknown = gross = 0.0
    seen_source_files = set()

    for ticker in FUNDS:
        fund = by_ticker[ticker]
        if not isinstance(fund["source_name"], str) or not fund["source_name"].strip():
            fail(f"{ticker}.source_name is required")
        official_url(ticker, fund["source_url"], f"{ticker}.source_url", allow_test=allow_test)
        source_date = iso_date(fund["source_as_of"], f"{ticker}.source_as_of")
        if source_date > review_date:
            fail(f"{ticker}.source_as_of cannot be in the future")
        if (review_date - source_date).days > MAX_SOURCE_AGE_DAYS:
            fail(f"{ticker}.source_as_of is more than 7 days old")
        source_dates.add(source_date)
        retrieved = iso_datetime(fund["retrieved_at"], f"{ticker}.retrieved_at")
        if retrieved.date() != review_date or retrieved > observed_at:
            fail(f"{ticker}.retrieved_at must be on review_date and not after observed_at")
        source_path = bundle_file(bundle, fund["source_file"], f"{ticker}.source_file")
        if source_path in seen_source_files:
            fail("each fund must archive a distinct source file")
        seen_source_files.add(source_path)
        expected_digest = require_sha(fund["source_sha256"], f"{ticker}.source_sha256")
        if digest_file(source_path, MAX_SOURCE_BYTES, f"{ticker}.source_file") != expected_digest:
            fail(f"{ticker}.source_sha256 does not match archived source bytes")

        holdings = fund["holdings"]
        if not isinstance(holdings, list) or not 0 < len(holdings) <= MAX_HOLDINGS_PER_FUND:
            fail(f"{ticker}.holdings count must be within [1, {MAX_HOLDINGS_PER_FUND}]")
        market_sum = 0.0
        seen_ids = set()
        for index, holding in enumerate(holdings):
            prefix = f"{ticker}.holdings[{index}]"
            if not isinstance(holding, dict):
                fail(f"{prefix} must be an object")
            require_keys(
                holding,
                {
                    "security_id",
                    "instrument_type",
                    "market_weight",
                    "exposure_weight",
                    "raw_sector",
                    "raw_industry",
                },
                prefix,
            )
            security_id = holding["security_id"]
            if not isinstance(security_id, str) or not security_id.strip():
                fail(f"{prefix}.security_id is required")
            if security_id != security_id.strip().upper():
                fail(f"{prefix}.security_id must be canonical uppercase without edge whitespace")
            if security_id in seen_ids:
                fail(f"{ticker} has duplicate security_id: {security_id}")
            seen_ids.add(security_id)
            instrument = holding["instrument_type"]
            if instrument not in INSTRUMENT_TYPES:
                fail(f"{prefix}.instrument_type is invalid")
            if "raw_sector" not in holding or "raw_industry" not in holding:
                fail(f"{prefix} must preserve raw classification fields")
            market_weight = bounded(
                holding["market_weight"], f"{prefix}.market_weight", -0.1, 1.1
            )
            exposure_weight = bounded(
                holding["exposure_weight"], f"{prefix}.exposure_weight", 0, 2
            )
            market_sum += market_weight
            if instrument == "cash" and exposure_weight > EPS:
                fail(f"{prefix} cash exposure_weight must be zero")
            if instrument in {"equity", "fund"} and abs(
                exposure_weight - max(market_weight, 0)
            ) > ROUNDING_TOLERANCE:
                fail(f"{prefix} exposure_weight must match positive market_weight")
            if instrument != "derivative" and exposure_weight > EPS and security_id not in mapping:
                issuer_unknown += portfolio_weights[ticker] * exposure_weight
                class_unknown += portfolio_weights[ticker] * exposure_weight
                gross += portfolio_weights[ticker] * exposure_weight
                continue
            if exposure_weight <= EPS:
                continue
            record = mapping.get(security_id)
            if record is None:
                issuer_unknown += portfolio_weights[ticker] * exposure_weight
                class_unknown += portfolio_weights[ticker] * exposure_weight
                gross += portfolio_weights[ticker] * exposure_weight
                continue
            if instrument == "derivative" and record["derivative_components"] is None:
                fail(f"{prefix} derivative requires audited look-through components")
            if instrument != "derivative" and record["derivative_components"] is not None:
                fail(f"{prefix} non-derivative cannot use derivative components")
            check_raw_mapping(record, holding, prefix)
            contribution = portfolio_weights[ticker] * exposure_weight
            gross += contribution
            for issuer, sector, industry, fraction in expand_mapping(record):
                part = contribution * fraction
                issuer_weights[issuer] = issuer_weights.get(issuer, 0.0) + part
                if sector == TECH:
                    tech_known += part
                if industry == SEMI:
                    semi_known += part
        if abs(market_sum - 1) > ROUNDING_TOLERANCE:
            fail(f"{ticker}.market_weight total must equal 1 within 5 bps")

    if len(source_dates) != 1:
        fail("Green packet requires identical source_as_of for SPYM, QQQM and SOXX")
    if gross <= EPS:
        fail("gross look-through exposure must be positive")
    issuer_covered = gross - issuer_unknown
    class_covered = gross - class_unknown
    issuer_max = max(issuer_weights.values(), default=0.0)
    metrics = {
        "gross_lookthrough_exposure": gross,
        "issuer_coverage_ratio": issuer_covered / gross,
        "classification_coverage_ratio": class_covered / gross,
        "issuer_unknown_weight": issuer_unknown,
        "classification_unknown_weight": class_unknown,
        "technology_known_weight": tech_known,
        "technology_upper_bound": tech_known + class_unknown,
        "semiconductor_known_weight": semi_known,
        "semiconductor_upper_bound": semi_known + class_unknown,
        "max_issuer_known_weight": issuer_max,
        "max_issuer_upper_bound": issuer_max + issuer_unknown,
    }
    gates = {
        "technology_below_50": metrics["technology_upper_bound"] < 0.50 - EPS,
        "semiconductor_at_or_below_15": metrics["semiconductor_upper_bound"] <= 0.15 + EPS,
        "issuer_at_or_below_10": metrics["max_issuer_upper_bound"] <= 0.10 + EPS,
        "full_issuer_coverage": issuer_unknown <= EPS,
        "full_classification_coverage": class_unknown <= EPS,
        "post_trade_soxx_at_or_below_3": portfolio_weights["SOXX"]
        <= CURRENT_EXECUTION_CAP + EPS,
    }
    verdict = "DATA GATE PASS" if all(gates.values()) else "DATA INCOMPLETE"
    return metrics, gates, verdict


def validate(packet: dict, packet_path: Path, *, allow_test: bool = False) -> dict[str, float]:
    metrics, gates, verdict = evaluate(packet, packet_path, allow_test=allow_test)
    reported = packet["metrics"]
    if not isinstance(reported, dict) or set(reported) != set(metrics):
        fail("metrics keys do not match schema 1.1")
    for key, calculated in metrics.items():
        value = bounded(reported[key], f"metrics.{key}", 0, 2)
        if abs(value - calculated) > EPS:
            fail(f"metrics.{key} does not reconcile")
    if packet["gates"] != gates:
        fail("gates do not equal validator-calculated results")
    if packet["verdict"] != verdict:
        fail(f"verdict must be {verdict}")
    digest = require_sha(packet["packet_sha256"], "packet_sha256")
    if digest != canonical_sha256(packet):
        fail("packet_sha256 does not match canonical packet content")
    return metrics


def write_fixture(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    return digest_file(path, MAX_SOURCE_BYTES, str(path))


def sample(root: Path) -> tuple[dict, Path]:
    review = "2026-07-30"
    packet_id = f"lookthrough-{review}-selftest"
    bundle = root / review / packet_id
    bundle.mkdir(parents=True)
    mapping_records = []
    funds = []
    for ticker in FUNDS:
        rows = []
        for index in range(10):
            security_id = "AAA" if index == 0 else f"{ticker}-{index}"
            is_semi = index == 0 or ticker == "SOXX"
            rows.append(
                {
                    "security_id": security_id,
                    "instrument_type": "equity",
                    "market_weight": 0.10,
                    "exposure_weight": 0.10,
                    "raw_sector": "Technology" if is_semi else "Other",
                    "raw_industry": "Semiconductors" if is_semi else "Other",
                }
            )
            if not any(item["security_id"] == security_id for item in mapping_records):
                mapping_records.append(
                    {
                        "security_id": security_id,
                        "issuer_group_id": "issuer-a"
                        if security_id == "AAA"
                        else f"issuer-{security_id.lower()}",
                        "normalized_sector": TECH if is_semi else "Industrials",
                        "normalized_industry": SEMI if is_semi else OTHER_INDUSTRY,
                        "derivative_components": None,
                        "evidence": "self-test mapping",
                    }
                )
        if ticker == "SOXX":
            rows[-1] = {
                "security_id": "SOXX-FUT",
                "instrument_type": "derivative",
                "market_weight": 0.0001,
                "exposure_weight": 0.005,
                "raw_sector": "Cash and/or Derivatives",
                "raw_industry": "Futures",
            }
            rows[1]["market_weight"] = 0.1999
            rows[1]["exposure_weight"] = 0.1999
            mapping_records.append(
                {
                    "security_id": "SOXX-FUT",
                    "issuer_group_id": None,
                    "normalized_sector": None,
                    "normalized_industry": None,
                    "derivative_components": [
                        {
                            "issuer_group_id": f"future-issuer-{index}",
                            "normalized_sector": TECH,
                            "normalized_industry": SEMI,
                            "weight": 0.1,
                        }
                        for index in range(10)
                    ],
                    "evidence": "self-test derivative decomposition",
                }
            )
        raw = f"official fixture for {ticker}\n".encode()
        source_file = f"raw/{ticker}.bin"
        source_sha = write_fixture(bundle / source_file, raw)
        funds.append(
            {
                "ticker": ticker,
                "source_name": "Official test fixture",
                "source_url": f"https://example.invalid/{ticker}",
                "source_as_of": "2026-07-29",
                "retrieved_at": "2026-07-30T11:00:00+09:00",
                "source_file": source_file,
                "source_sha256": source_sha,
                "holdings": rows,
            }
        )
    mapping = {
        "schema_version": MAPPING_VERSION,
        "mapping_id": "selftest-map-1",
        "taxonomy": "GICS",
        "records": mapping_records,
    }
    mapping_sha = write_fixture(bundle / "mapping.json", mapping)
    account = {
        "schema_version": ACCOUNT_VERSION,
        "account_snapshot_id": "selftest-account-1",
        "observed_at": "2026-07-30T10:55:00+09:00",
        "candidate_packet_id": "candidate-selftest-1",
        "candidate_ticker": "SOXX",
        "candidate_notional": 1000,
        "nav": 100000,
        "current_market_values": {
            "cash": 16000,
            "SPYM": 55000,
            "QQQM": 28000,
            "SOXX": 1000,
        },
    }
    account_sha = write_fixture(bundle / "account.json", account)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": packet_id,
        "review_date": review,
        "observed_at": "2026-07-30T12:00:00+09:00",
        "candidate_packet_id": "candidate-selftest-1",
        "weight_basis": "post_trade",
        "account_scenario_path": "account.json",
        "account_snapshot_sha256": account_sha,
        "mapping_path": "mapping.json",
        "mapping_sha256": mapping_sha,
        "portfolio_weights": {"cash": 0.15, "SPYM": 0.55, "QQQM": 0.28, "SOXX": 0.02},
        "funds": funds,
        "metrics": {},
        "gates": {},
        "verdict": "",
        "packet_sha256": "",
        "test_only": True,
    }
    packet_path = bundle / "packet.json"
    metrics, gates, verdict = evaluate(packet, packet_path, allow_test=True)
    packet["metrics"] = metrics
    packet["gates"] = gates
    packet["verdict"] = verdict
    packet["packet_sha256"] = canonical_sha256(packet)
    write_fixture(packet_path, packet)
    return packet, packet_path


def expect_invalid(
    name: str,
    packet: dict,
    packet_path: Path,
    mutate,
    *,
    rewrite_dependencies: bool = False,
) -> None:
    bad = copy.deepcopy(packet)
    mutate(bad)
    if rewrite_dependencies:
        bad["packet_sha256"] = canonical_sha256(bad)
    try:
        validate(bad, packet_path, allow_test=True)
    except PacketError:
        return
    fail(f"self-test accepted invalid packet: {name}")


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="lookthrough-selftest-") as tmp:
        root = Path(tmp)
        good, packet_path = sample(root)
        validate(good, packet_path, allow_test=True)
        mutations = [
            ("unofficial domain", lambda p: p["funds"][0].update(source_url="https://evil.example/x")),
            ("forged source hash", lambda p: p["funds"][0].update(source_sha256="0" * 64)),
            ("stale source", lambda p: p["funds"][0].update(source_as_of="1999-01-01")),
            ("future source", lambda p: p["funds"][0].update(source_as_of="2026-08-01")),
            ("source date skew", lambda p: p["funds"][0].update(source_as_of="2026-07-28")),
            ("SOXX zero", lambda p: p["portfolio_weights"].update(SOXX=0.0, cash=0.17)),
            ("metric forgery", lambda p: p["metrics"].update(technology_upper_bound=0.0)),
            ("verdict forgery", lambda p: p.update(verdict="DATA INCOMPLETE")),
            ("packet hash mismatch", lambda p: p.update(candidate_packet_id="tampered")),
            ("non-finite", lambda p: p["portfolio_weights"].update(SOXX=float("nan"))),
            ("template flag", lambda p: p.update(_template=True)),
        ]
        for name, mutate in mutations:
            expect_invalid(name, good, packet_path, mutate)

        # Re-hashing a forged packet must not bypass account/source/mapping controls.
        expect_invalid(
            "rehash after account mismatch",
            good,
            packet_path,
            lambda p: p["portfolio_weights"].update(SOXX=0.0, cash=0.17),
            rewrite_dependencies=True,
        )

        source_path = packet_path.parent / good["funds"][0]["source_file"]
        original_source = source_path.read_bytes()
        source_path.write_bytes(original_source + b"tampered")
        try:
            validate(good, packet_path, allow_test=True)
        except PacketError:
            pass
        else:
            fail("self-test accepted changed archived source bytes")
        source_path.write_bytes(original_source)

        mapping_path = packet_path.parent / good["mapping_path"]
        original_mapping = mapping_path.read_bytes()
        bad_mapping = read_json(mapping_path, MAX_MAPPING_BYTES, "mapping fixture")
        bad_mapping["records"][0]["normalized_sector"] = "Industrials"
        bad_mapping["records"][0]["normalized_industry"] = OTHER_INDUSTRY
        mapping_path.write_text(
            json.dumps(bad_mapping, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        remapped = copy.deepcopy(good)
        remapped["mapping_sha256"] = digest_file(
            mapping_path, MAX_MAPPING_BYTES, "mapping fixture"
        )
        remapped["packet_sha256"] = canonical_sha256(remapped)
        try:
            validate(remapped, packet_path, allow_test=True)
        except PacketError:
            pass
        else:
            fail("self-test accepted mapping that contradicts raw manager labels")
        mapping_path.write_bytes(original_mapping)

        account_path = packet_path.parent / good["account_scenario_path"]
        original_account = account_path.read_bytes()
        bad_account = read_json(account_path, MAX_ACCOUNT_BYTES, "account fixture")
        bad_account["candidate_notional"] = 0
        account_path.write_text(
            json.dumps(bad_account, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        rebound = copy.deepcopy(good)
        rebound["account_snapshot_sha256"] = digest_file(
            account_path, MAX_ACCOUNT_BYTES, "account fixture"
        )
        rebound["packet_sha256"] = canonical_sha256(rebound)
        try:
            validate(rebound, packet_path, allow_test=True)
        except PacketError:
            pass
        else:
            fail("self-test accepted a re-hashed invalid account scenario")
        account_path.write_bytes(original_account)

        # Real manager rounding of 100.01% remains representable.
        rounded = copy.deepcopy(good)
        rounded["funds"][2]["holdings"][0]["market_weight"] += 0.0001
        rounded["funds"][2]["holdings"][0]["exposure_weight"] += 0.0001
        metrics, gates, verdict = evaluate(rounded, packet_path, allow_test=True)
        rounded["metrics"], rounded["gates"], rounded["verdict"] = metrics, gates, verdict
        rounded["packet_sha256"] = canonical_sha256(rounded)
        validate(rounded, packet_path, allow_test=True)

        duplicate = '{"schema_version":"1.1","schema_version":"0.0"}'
        duplicate_path = packet_path.parent / "duplicate.json"
        duplicate_path.write_text(duplicate, encoding="utf-8")
        try:
            read_json(duplicate_path, MAX_PACKET_BYTES, "duplicate fixture")
        except PacketError:
            pass
        else:
            fail("self-test accepted duplicate JSON keys")

    print("Look-through packet schema 1.1 self-tests passed.")


def scan_root(root: Path) -> None:
    if not root.is_dir():
        fail(f"snapshot root does not exist: {root}")
    packet_paths = []
    for date_dir in sorted(root.iterdir()):
        if date_dir.name == ".gitkeep" and date_dir.is_file() and not date_dir.is_symlink():
            continue
        if date_dir.is_symlink() or not date_dir.is_dir():
            fail(f"snapshot root may contain only YYYY-MM-DD directories: {date_dir}")
        iso_date(date_dir.name, "snapshot directory")
        for bundle in sorted(date_dir.iterdir()):
            if bundle.is_symlink() or not bundle.is_dir():
                fail(f"review date directory may contain only packet bundles: {bundle}")
            packet_path = bundle / "packet.json"
            if not packet_path.is_file() or packet_path.is_symlink():
                fail(f"packet bundle is missing regular packet.json: {bundle}")
            packet_paths.append(packet_path)
    for path in packet_paths:
        packet = read_json(path, MAX_PACKET_BYTES, str(path))
        validate(packet, path)
        print(f"{path}: valid")
    print(f"Validated {len(packet_paths)} Production look-through bundle(s).")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--scan-root", type=Path)
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        if args.scan_root is not None:
            scan_root(args.scan_root)
        for path in args.paths:
            packet = read_json(path, MAX_PACKET_BYTES, str(path))
            validate(packet, path)
            print(f"{path}: valid")
    except (PacketError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not args.self_test and args.scan_root is None and not args.paths:
        parser.error("provide --self-test, --scan-root, or at least one packet path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
