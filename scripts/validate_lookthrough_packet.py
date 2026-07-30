#!/usr/bin/env python3
"""Validate immutable ETF look-through evidence bundles without third parties."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import re
import sys
import tempfile
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from parse_lookthrough_sources import SOURCE_FORMATS, SourceParseError, parse_source

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
CANONICAL_ISSUER = re.compile(r"^(?:cik:[0-9]{10}|lei:[0-9A-Z]{20})$")
CANONICAL_SECURITY = re.compile(
    r"^(?:"
    r"CUSIP:[A-Z0-9*@#]{9}|"
    r"ISIN:[A-Z]{2}[A-Z0-9]{9}[0-9]|"
    r"SEDOL:[A-Z0-9]{7}|"
    r"TICKER:[A-Z0-9][A-Z0-9./-]{0,31}|"
    r"MANAGER:[A-Z0-9][A-Z0-9./-]{0,63}|"
    r"CASH:[A-Z]{3}"
    r")$"
)
SCHEMA_VERSION = "1.3"
MAPPING_VERSION = "1.2"
ISSUER_REGISTRY_VERSION = "1.1"
ACCOUNT_VERSION = "1.0"
CANDIDATE_VERSION = "1.0"
EPS = 1e-9
ROUNDING_TOLERANCE = 5e-4  # 5 bps; accepts an official 100.01% rounded total.
MAX_SOURCE_AGE_DAYS = 7
MAX_PACKET_BYTES = 20 * 1024 * 1024
MAX_MAPPING_BYTES = 10 * 1024 * 1024
MAX_ACCOUNT_BYTES = 1024 * 1024
MAX_SOURCE_BYTES = 100 * 1024 * 1024
MAX_HOLDINGS_PER_FUND = 20_000
CURRENT_EXECUTION_CAP = 0.03
MIN_FUND_ECONOMIC_EXPOSURE = 0.95
MAX_CLOCK_SKEW = timedelta(minutes=5)
MAX_CANDIDATE_TTL = timedelta(days=1)
ROOT = Path(__file__).resolve().parents[1]
ISSUER_AUTHORITY_PATH = ROOT / "08-Data/REGISTRIES/LOOKTHROUGH_ISSUER_AUTHORITY.json"
CLASSIFICATION_AUTHORITY_PATH = (
    ROOT / "08-Data/REGISTRIES/LOOKTHROUGH_CLASSIFICATION_AUTHORITY.json"
)
IDENTITY_EVIDENCE_HOSTS = {
    "sec.gov",
    "gleif.org",
    "openfigi.com",
    "ssga.com",
    "invesco.com",
    "ishares.com",
    "blackrock.com",
}
CLASSIFICATION_EVIDENCE_HOSTS = {
    "msci.com",
    "spglobal.com",
    "ssga.com",
    "invesco.com",
    "ishares.com",
    "blackrock.com",
}


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
    path = parsed.path.lower()
    required_path_tokens = {
        "SPYM": ("spym",),
        "QQQM": ("qqqm", "nasdaq-100-etf"),
        "SOXX": ("soxx", "239705", "semiconductor-etf"),
    }[ticker]
    if not any(token in path for token in required_path_tokens):
        fail(f"{field} does not identify the {ticker} product")


def canonical_sha256(packet: dict) -> str:
    body = copy.deepcopy(packet)
    body["packet_sha256"] = ""
    payload = json.dumps(
        body, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def canonical_record(value: dict) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def validate_evidence(
    value: object,
    label: str,
    *,
    allowed_hosts: set[str],
    allow_test: bool,
) -> None:
    if not isinstance(value, dict):
        fail(f"{label} must be a structured evidence object")
    require_keys(value, {"source_url", "as_of"}, label)
    source_url = value["source_url"]
    if not isinstance(source_url, str):
        fail(f"{label}.source_url must be HTTPS")
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host:
        fail(f"{label}.source_url must be HTTPS")
    if not (allow_test and host == "example.invalid") and not any(
        host == allowed or host.endswith("." + allowed) for allowed in allowed_hosts
    ):
        fail(f"{label}.source_url host is not approved: {host}")
    iso_date(value["as_of"], f"{label}.as_of")


def test_authorities() -> tuple[dict, dict]:
    """Repository-controlled authority used only by the synthetic self-test."""
    issuers: dict[str, dict] = {}
    securities: dict[str, dict] = {}
    mappings: dict[str, dict] = {}
    for fund_number, ticker in enumerate(FUNDS, start=1):
        direct_security_ids = []
        for index in range(10):
            is_alphabet = ticker == "QQQM" and index in {8, 9}
            raw_identifier = (
                "02079K305"
                if is_alphabet and index == 8
                else "02079K107"
                if is_alphabet
                else "000000001"
                if index == 0
                else f"{fund_number}{index:05d}00{index}"
            )
            security_id = f"CUSIP:{raw_identifier}"
            direct_security_ids.append(security_id)
            is_semi = index == 0 or ticker == "SOXX"
            issuer_number = (
                1
                if raw_identifier == "000000001"
                else 1_652_044
                if is_alphabet
                else int(raw_identifier)
            )
            issuer_id = f"cik:{issuer_number:010d}"
            issuers.setdefault(
                issuer_id,
                {
                    "issuer_group_id": issuer_id,
                    "canonical_name": (
                        "Alphabet Inc"
                        if is_alphabet
                        else f"Self Test Issuer {issuer_number}"
                    ),
                    "evidence_url": f"https://example.invalid/cik/{issuer_number}",
                },
            )
            securities[security_id] = {
                "security_id": security_id,
                "canonical_security_id": security_id,
                "issuer_group_id": issuer_id,
                "evidence": {
                    "source_url": "https://example.invalid/identity",
                    "as_of": "2026-07-29",
                },
            }
            mappings[security_id] = {
                "security_id": security_id,
                "normalized_sector": (
                    TECH
                    if is_semi
                    else "Communication Services"
                    if is_alphabet
                    else "Industrials"
                ),
                "normalized_industry": SEMI if is_semi else OTHER_INDUSTRY,
                "derivative_components": None,
                "evidence": {
                    "source_url": "https://example.invalid/classification",
                    "as_of": "2026-07-29",
                },
            }
        if ticker == "SOXX":
            future_security_id = "CUSIP:900000009"
            mappings[future_security_id] = {
                "security_id": future_security_id,
                "normalized_sector": None,
                "normalized_industry": None,
                "derivative_components": [
                    {
                        "security_id": component_security_id,
                        "weight": 1 / len(direct_security_ids[:-1]),
                    }
                    for component_security_id in direct_security_ids[:-1]
                ],
                "evidence": {
                    "source_url": "https://example.invalid/derivative",
                    "as_of": "2026-07-29",
                },
            }
    for sedol, cusip in (
        ("SEDOL:BYVY8G0", "CUSIP:02079K305"),
        ("SEDOL:BYY88Y7", "CUSIP:02079K107"),
    ):
        securities[sedol] = {
            "security_id": sedol,
            "canonical_security_id": cusip,
            "issuer_group_id": "cik:0001652044",
            "evidence": {
                "source_url": "https://example.invalid/cross-identifier",
                "as_of": "2026-07-29",
            },
        }
    return (
        {
            "schema_version": ISSUER_REGISTRY_VERSION,
            "authority_id": "lookthrough-issuer-authority",
            "issuers": list(issuers.values()),
            "securities": list(securities.values()),
        },
        {
            "schema_version": MAPPING_VERSION,
            "authority_id": "lookthrough-classification-authority",
            "taxonomy": "GICS",
            "records": list(mappings.values()),
        },
    )


def load_authority(path: Path, label: str, *, allow_test: bool) -> dict:
    if allow_test:
        issuer, classification = test_authorities()
        return issuer if label == "issuer authority" else classification
    return read_json(path, MAX_MAPPING_BYTES, label)


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


def load_mapping(
    bundle: Path,
    path_value: object,
    digest_value: object,
    *,
    allow_test: bool,
) -> dict[str, dict]:
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
                "normalized_sector",
                "normalized_industry",
                "derivative_components",
                "evidence",
            },
            label,
        )
        security_id = record["security_id"]
        require_security_id(security_id, f"{label}.security_id")
        if security_id in by_security:
            fail(f"mapping has duplicate security_id: {security_id}")
        validate_evidence(
            record["evidence"],
            f"{label}.evidence",
            allowed_hosts=CLASSIFICATION_EVIDENCE_HOSTS,
            allow_test=allow_test,
        )
        components = record["derivative_components"]
        direct = components is None
        if direct:
            sector = record["normalized_sector"]
            industry = record["normalized_industry"]
            validate_taxonomy(sector, industry, label)
        else:
            if any(record[key] is not None for key in ("normalized_sector", "normalized_industry")):
                fail(f"{label} derivative mapping must use components, not direct fields")
            validate_components(components, label)
        by_security[security_id] = record

    authority = load_authority(
        CLASSIFICATION_AUTHORITY_PATH, "classification authority", allow_test=allow_test
    )
    require_keys(
        authority,
        {"schema_version", "authority_id", "taxonomy", "records"},
        "classification authority",
    )
    if authority["schema_version"] != MAPPING_VERSION:
        fail(f"classification authority schema_version must be {MAPPING_VERSION}")
    if authority["authority_id"] != "lookthrough-classification-authority":
        fail("classification authority_id is invalid")
    if authority["taxonomy"] != "GICS" or not isinstance(authority["records"], list):
        fail("classification authority must contain a GICS records array")
    approved = {canonical_record(item) for item in authority["records"]}
    for record in records:
        if canonical_record(record) not in approved:
            fail(
                f"mapping record is not present in the reviewed classification authority: "
                f"{record['security_id']}"
            )
    return by_security


def load_issuer_registry(
    bundle: Path,
    path_value: object,
    digest_value: object,
    *,
    allow_test: bool,
) -> dict[str, dict[str, str]]:
    _, registry = validate_reference(
        bundle,
        {"path": path_value, "sha256": digest_value},
        label="issuer_registry",
        max_bytes=MAX_MAPPING_BYTES,
    )
    require_keys(
        registry,
        {"schema_version", "registry_id", "issuers", "securities"},
        "issuer_registry",
    )
    if registry["schema_version"] != ISSUER_REGISTRY_VERSION:
        fail(f"issuer_registry.schema_version must be {ISSUER_REGISTRY_VERSION}")
    if not isinstance(registry["registry_id"], str) or not registry["registry_id"].strip():
        fail("issuer_registry.registry_id is required")
    issuers = registry["issuers"]
    securities = registry["securities"]
    if not isinstance(issuers, list) or not issuers:
        fail("issuer_registry.issuers must be a non-empty array")
    if not isinstance(securities, list) or not securities:
        fail("issuer_registry.securities must be a non-empty array")

    issuer_ids: set[str] = set()
    issuer_names: set[str] = set()
    for index, issuer in enumerate(issuers):
        label = f"issuer_registry.issuers[{index}]"
        if not isinstance(issuer, dict):
            fail(f"{label} must be an object")
        require_keys(
            issuer,
            {"issuer_group_id", "canonical_name", "evidence_url"},
            label,
        )
        issuer_id = require_issuer(issuer["issuer_group_id"], f"{label}.issuer_group_id")
        if issuer_id in issuer_ids:
            fail(f"issuer_registry has duplicate issuer_group_id: {issuer_id}")
        issuer_ids.add(issuer_id)
        canonical_name = issuer["canonical_name"]
        if not isinstance(canonical_name, str) or not canonical_name.strip():
            fail(f"{label}.canonical_name is required")
        normalized_name = re.sub(r"[^a-z0-9]+", "", canonical_name.casefold())
        if not normalized_name or normalized_name in issuer_names:
            fail("issuer_registry canonical issuer names must be unique")
        issuer_names.add(normalized_name)
        evidence_url = issuer["evidence_url"]
        if not isinstance(evidence_url, str):
            fail(f"{label}.evidence_url is required")
        parsed = urlparse(evidence_url)
        host = (parsed.hostname or "").lower()
        if allow_test and host == "example.invalid":
            continue
        if issuer_id.startswith("cik:"):
            cik = issuer_id.removeprefix("cik:")
            if host not in {"sec.gov", "www.sec.gov"} or cik.lstrip("0") not in evidence_url:
                fail(f"{label}.evidence_url must identify the same issuer on sec.gov")
        elif host not in {"gleif.org", "www.gleif.org"} or issuer_id.removeprefix("lei:") not in evidence_url.upper():
            fail(f"{label}.evidence_url must identify the same issuer on gleif.org")

    by_security: dict[str, dict[str, str]] = {}
    by_cusip_issuer: dict[str, str] = {}
    for index, security in enumerate(securities):
        label = f"issuer_registry.securities[{index}]"
        if not isinstance(security, dict):
            fail(f"{label} must be an object")
        require_keys(
            security,
            {
                "security_id",
                "canonical_security_id",
                "issuer_group_id",
                "evidence",
            },
            label,
        )
        security_id = require_security_id(security["security_id"], f"{label}.security_id")
        if security_id in by_security:
            fail(f"issuer_registry has duplicate security_id: {security_id}")
        canonical_security_id = require_security_id(
            security["canonical_security_id"], f"{label}.canonical_security_id"
        )
        issuer_id = require_issuer(
            security["issuer_group_id"], f"{label}.issuer_group_id"
        )
        if issuer_id not in issuer_ids:
            fail(f"{label}.issuer_group_id is absent from issuer_registry.issuers")
        validate_evidence(
            security["evidence"],
            f"{label}.evidence",
            allowed_hosts=IDENTITY_EVIDENCE_HOSTS,
            allow_test=allow_test,
        )
        cusip_issuer = (
            security_id.removeprefix("CUSIP:")[:6]
            if security_id.startswith("CUSIP:")
            else security_id.removeprefix("ISIN:")[2:8]
            if security_id.startswith("ISIN:US")
            else None
        )
        if cusip_issuer is not None:
            previous = by_cusip_issuer.setdefault(cusip_issuer, issuer_id)
            if previous != issuer_id:
                fail(
                    "securities sharing a CUSIP issuer number must share one issuer identity"
                )
        by_security[security_id] = {
            "canonical_security_id": canonical_security_id,
            "issuer_group_id": issuer_id,
        }

    for security_id, identity in by_security.items():
        canonical_security_id = identity["canonical_security_id"]
        canonical = by_security.get(canonical_security_id)
        if canonical is None:
            fail(
                f"issuer_registry canonical security is absent: {canonical_security_id}"
            )
        if canonical["canonical_security_id"] != canonical_security_id:
            fail(
                f"issuer_registry canonical security must resolve to itself: "
                f"{canonical_security_id}"
            )
        if canonical["issuer_group_id"] != identity["issuer_group_id"]:
            fail(
                f"issuer_registry alias and canonical security must share one issuer: "
                f"{security_id}"
            )

    authority = load_authority(
        ISSUER_AUTHORITY_PATH, "issuer authority", allow_test=allow_test
    )
    require_keys(
        authority,
        {"schema_version", "authority_id", "issuers", "securities"},
        "issuer authority",
    )
    if authority["schema_version"] != ISSUER_REGISTRY_VERSION:
        fail(f"issuer authority schema_version must be {ISSUER_REGISTRY_VERSION}")
    if authority["authority_id"] != "lookthrough-issuer-authority":
        fail("issuer authority_id is invalid")
    if not isinstance(authority["issuers"], list) or not isinstance(
        authority["securities"], list
    ):
        fail("issuer authority must contain issuer and security arrays")
    approved_issuers = {canonical_record(item) for item in authority["issuers"]}
    approved_securities = {canonical_record(item) for item in authority["securities"]}
    for issuer in issuers:
        if canonical_record(issuer) not in approved_issuers:
            fail(
                "issuer record is not present in the reviewed issuer authority: "
                f"{issuer['issuer_group_id']}"
            )
    for security in securities:
        if canonical_record(security) not in approved_securities:
            fail(
                "security identity is not present in the reviewed issuer authority: "
                f"{security['security_id']}"
            )
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
    seen_security_ids: set[str] = set()
    for index, component in enumerate(value):
        prefix = f"{label}.derivative_components[{index}]"
        if not isinstance(component, dict):
            fail(f"{prefix} must be an object")
        require_keys(
            component,
            {"security_id", "weight"},
            prefix,
        )
        security_id = require_security_id(component["security_id"], f"{prefix}.security_id")
        if security_id in seen_security_ids:
            fail(f"{label}.derivative_components has duplicate security_id: {security_id}")
        seen_security_ids.add(security_id)
        total += bounded(component["weight"], f"{prefix}.weight", 0, 1)
    if abs(total - 1) > ROUNDING_TOLERANCE:
        fail(f"{label}.derivative_components weights must sum to 1 within 5 bps")


def require_issuer(value: object, field: str) -> str:
    if not isinstance(value, str) or not CANONICAL_ISSUER.fullmatch(value):
        fail(f"{field} must be a canonical cik:<10-digits> or lei:<20-character-LEI>")
    if value == "cik:0000000000":
        fail(f"{field} must not use the null CIK")
    return value


def require_security_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not CANONICAL_SECURITY.fullmatch(value):
        fail(
            f"{field} must be a typed CUSIP, ISIN, SEDOL, TICKER, MANAGER or CASH identifier"
        )
    return value


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
        {"schema_version", "account_snapshot_id", "observed_at", "nav", "current_market_values"},
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
    nav = number(account["nav"], "account_scenario.nav")
    if nav <= 0:
        fail("account_scenario nav must be positive")
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
    return {
        "account_snapshot_id": account["account_snapshot_id"],
        "observed_at": observed,
        "nav": nav,
        "values": values,
    }


def load_candidate(
    bundle: Path,
    path_value: object,
    digest_value: object,
    packet: dict,
    account: dict,
    observed_at: datetime,
) -> float:
    _, candidate = validate_reference(
        bundle,
        {"path": path_value, "sha256": digest_value},
        label="candidate",
        max_bytes=MAX_ACCOUNT_BYTES,
    )
    require_keys(
        candidate,
        {
            "schema_version",
            "candidate_packet_id",
            "created_at",
            "expires_at",
            "ticker",
            "side",
            "proposed_notional",
            "max_notional",
            "account_snapshot_id",
            "account_snapshot_sha256",
        },
        "candidate",
    )
    if candidate["schema_version"] != CANDIDATE_VERSION:
        fail(f"candidate.schema_version must be {CANDIDATE_VERSION}")
    if candidate["candidate_packet_id"] != packet.get("candidate_packet_id"):
        fail("candidate_packet_id does not match candidate file")
    if candidate["ticker"] != "SOXX" or candidate["side"] != "ADD":
        fail("candidate must be an ADD scenario for SOXX")
    if candidate["account_snapshot_id"] != account["account_snapshot_id"]:
        fail("candidate account_snapshot_id does not match account file")
    if candidate["account_snapshot_sha256"] != packet["account_snapshot_sha256"]:
        fail("candidate account_snapshot_sha256 does not match packet")
    created = iso_datetime(candidate["created_at"], "candidate.created_at")
    expires = iso_datetime(candidate["expires_at"], "candidate.expires_at")
    if not account["observed_at"] <= created <= observed_at:
        fail("candidate must be created after the account snapshot and by observed_at")
    if expires <= created or expires - created > MAX_CANDIDATE_TTL or observed_at >= expires:
        fail("candidate must be unexpired at observed_at")
    proposed = number(candidate["proposed_notional"], "candidate.proposed_notional")
    maximum = number(candidate["max_notional"], "candidate.max_notional")
    if proposed <= 0 or maximum <= 0 or proposed > maximum + EPS:
        fail("candidate proposed_notional must be positive and not exceed max_notional")
    if proposed > account["values"]["cash"] + EPS:
        fail("candidate proposed_notional exceeds cash")
    return proposed


def raw_source_path(bundle: Path, ticker: str, value: object) -> Path:
    path = bundle_file(bundle, value, f"{ticker}.source_file")
    relative = path.relative_to(bundle)
    if len(relative.parts) != 2 or relative.parts[0] != "raw":
        fail(f"{ticker}.source_file must be a direct child of raw/")
    if Path(relative.name).stem.upper() != ticker:
        fail(f"{ticker}.source_file must be named raw/{ticker}.<official extension>")
    return path


def reconcile_parsed_holdings(ticker: str, reported: object, parsed: list[dict]) -> None:
    if not isinstance(reported, list) or len(reported) != len(parsed):
        fail(f"{ticker}.holdings must contain every parser-derived source row")
    keys = {
        "security_id",
        "source_identifiers",
        "raw_name",
        "instrument_type",
        "market_weight",
        "exposure_weight",
        "raw_sector",
        "raw_industry",
    }
    for index, (actual, expected) in enumerate(zip(reported, parsed)):
        label = f"{ticker}.holdings[{index}]"
        if not isinstance(actual, dict):
            fail(f"{label} must be an object")
        require_keys(actual, keys, label)
        for field in keys - {"market_weight", "exposure_weight"}:
            if actual[field] != expected[field]:
                fail(f"{label}.{field} does not match parsed archived source")
        for field in ("market_weight", "exposure_weight"):
            value = number(actual[field], f"{label}.{field}")
            if abs(value - expected[field]) > EPS:
                fail(f"{label}.{field} does not match parsed archived source")


def resolve_identity(
    holding: dict,
    issuer_registry: dict[str, dict[str, str]],
    label: str,
) -> dict[str, str] | None:
    source_identifiers = holding["source_identifiers"]
    if (
        not isinstance(source_identifiers, list)
        or not source_identifiers
        or len(set(source_identifiers)) != len(source_identifiers)
        or source_identifiers[0] != holding["security_id"]
    ):
        fail(f"{label}.source_identifiers must be a unique primary-first array")
    identities = []
    for index, security_id in enumerate(source_identifiers):
        require_security_id(
            security_id, f"{label}.source_identifiers[{index}]"
        )
        identity = issuer_registry.get(security_id)
        if identity is None:
            return None
        identities.append(identity)
    canonical_ids = {item["canonical_security_id"] for item in identities}
    issuer_ids = {item["issuer_group_id"] for item in identities}
    if len(canonical_ids) != 1 or len(issuer_ids) != 1:
        fail(f"{label} source identifiers do not resolve to one security and issuer")
    return identities[0]


def expand_mapping(
    record: dict,
    mapping: dict[str, dict],
    issuer_registry: dict[str, dict[str, str]],
) -> list[tuple[str, str, str, float]]:
    components = record["derivative_components"]
    if components is None:
        security_id = record["security_id"]
        identity = issuer_registry.get(security_id)
        if identity is None:
            fail(f"issuer registry has no entry for {security_id}")
        return [
            (
                identity["issuer_group_id"],
                record["normalized_sector"],
                record["normalized_industry"],
                1.0,
            )
        ]
    total = sum(float(item["weight"]) for item in components)
    expanded = []
    for item in components:
        security_id = item["security_id"]
        component_mapping = mapping.get(security_id)
        identity = issuer_registry.get(security_id)
        if component_mapping is None or identity is None:
            fail(
                f"derivative component {security_id} must exist in both mapping and issuer registry"
            )
        if component_mapping["derivative_components"] is not None:
            fail(f"derivative component {security_id} must resolve to a direct security")
        expanded.append(
            (
                identity["issuer_group_id"],
                component_mapping["normalized_sector"],
                component_mapping["normalized_industry"],
                float(item["weight"]) / total,
            )
        )
    return expanded


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
    if (
        label.startswith("SOXX.")
        and holding["instrument_type"] == "equity"
        and record["normalized_industry"] != SEMI
    ):
        fail(f"{label} SOXX equity must remain semiconductor-classified")


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
        "candidate_path",
        "candidate_sha256",
        "weight_basis",
        "account_scenario_path",
        "account_snapshot_sha256",
        "issuer_registry_path",
        "issuer_registry_sha256",
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
    now = datetime.now(timezone.utc)
    if observed_at.astimezone(timezone.utc) > now + MAX_CLOCK_SKEW:
        fail("review_date and observed_at must not be in the future")
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
    if packet["account_scenario_path"] != "account.json":
        fail("account_scenario_path must be account.json")
    if packet["mapping_path"] != "mapping.json":
        fail("mapping_path must be mapping.json")
    if packet["issuer_registry_path"] != "issuer-registry.json":
        fail("issuer_registry_path must be issuer-registry.json")
    if packet["candidate_path"] != "candidate.json":
        fail("candidate_path must be candidate.json")

    issuer_registry = load_issuer_registry(
        bundle,
        packet["issuer_registry_path"],
        packet["issuer_registry_sha256"],
        allow_test=allow_test,
    )
    mapping = load_mapping(
        bundle,
        packet["mapping_path"],
        packet["mapping_sha256"],
        allow_test=allow_test,
    )
    account = load_account(
        bundle,
        packet["account_scenario_path"],
        packet["account_snapshot_sha256"],
        packet,
        review_date,
    )
    if account["observed_at"] > observed_at:
        fail("account snapshot must not be later than packet observed_at")
    candidate_notional = load_candidate(
        bundle,
        packet["candidate_path"],
        packet["candidate_sha256"],
        packet,
        account,
        observed_at,
    )
    account_values = dict(account["values"])
    account_values["cash"] -= candidate_notional
    account_values["SOXX"] += candidate_notional
    account_weights = {
        key: value / account["nav"] for key, value in account_values.items()
    }
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
                "source_format",
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
        if fund["source_format"] != SOURCE_FORMATS[ticker]:
            fail(f"{ticker}.source_format must be {SOURCE_FORMATS[ticker]}")
        source_date = iso_date(fund["source_as_of"], f"{ticker}.source_as_of")
        if source_date > review_date:
            fail(f"{ticker}.source_as_of cannot be in the future")
        if (review_date - source_date).days > MAX_SOURCE_AGE_DAYS:
            fail(f"{ticker}.source_as_of is more than 7 days old")
        source_dates.add(source_date)
        retrieved = iso_datetime(fund["retrieved_at"], f"{ticker}.retrieved_at")
        if retrieved.date() != review_date or retrieved > observed_at:
            fail(f"{ticker}.retrieved_at must be on review_date and not after observed_at")
        source_path = raw_source_path(bundle, ticker, fund["source_file"])
        if source_path in seen_source_files:
            fail("each fund must archive a distinct source file")
        seen_source_files.add(source_path)
        expected_digest = require_sha(fund["source_sha256"], f"{ticker}.source_sha256")
        if digest_file(source_path, MAX_SOURCE_BYTES, f"{ticker}.source_file") != expected_digest:
            fail(f"{ticker}.source_sha256 does not match archived source bytes")

        try:
            parsed_source = parse_source(ticker, source_path, fund["source_format"])
        except SourceParseError as exc:
            raise PacketError(f"{ticker} archived source cannot be parsed: {exc}") from exc
        if parsed_source["source_as_of"] != fund["source_as_of"]:
            fail(f"{ticker}.source_as_of does not match parsed archived source")
        reconcile_parsed_holdings(ticker, fund["holdings"], parsed_source["holdings"])
        holdings = parsed_source["holdings"]
        if not isinstance(holdings, list) or not 0 < len(holdings) <= MAX_HOLDINGS_PER_FUND:
            fail(f"{ticker}.holdings count must be within [1, {MAX_HOLDINGS_PER_FUND}]")
        market_sum = 0.0
        exposure_sum = 0.0
        seen_ids = set()
        for index, holding in enumerate(holdings):
            prefix = f"{ticker}.holdings[{index}]"
            if not isinstance(holding, dict):
                fail(f"{prefix} must be an object")
            require_keys(
                holding,
                {
                    "security_id",
                    "source_identifiers",
                    "raw_name",
                    "instrument_type",
                    "market_weight",
                    "exposure_weight",
                    "raw_sector",
                    "raw_industry",
                },
                prefix,
            )
            security_id = holding["security_id"]
            require_security_id(security_id, f"{prefix}.security_id")
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
            exposure_sum += exposure_weight
            if instrument in {"equity", "fund", "other"} and market_weight < -EPS:
                fail(f"{prefix} non-derivative market_weight must not be negative")
            if instrument == "cash" and exposure_weight > EPS:
                fail(f"{prefix} cash exposure_weight must be zero")
            if instrument in {"equity", "fund", "other"} and abs(
                exposure_weight - max(market_weight, 0)
            ) > ROUNDING_TOLERANCE:
                fail(f"{prefix} exposure_weight must match positive market_weight")
            if instrument == "other" and exposure_weight <= EPS:
                fail(f"{prefix} unexplained other instrument cannot have zero exposure")
            if exposure_weight <= EPS:
                continue
            identity = resolve_identity(holding, issuer_registry, prefix)
            canonical_security_id = (
                identity["canonical_security_id"] if identity is not None else security_id
            )
            record = mapping.get(canonical_security_id)
            contribution = portfolio_weights[ticker] * exposure_weight
            gross += contribution
            if instrument != "derivative":
                if identity is None:
                    issuer_unknown += contribution
                else:
                    issuer = identity["issuer_group_id"]
                    issuer_weights[issuer] = issuer_weights.get(issuer, 0.0) + contribution
                if record is None:
                    class_unknown += contribution
                else:
                    if record["derivative_components"] is not None:
                        fail(f"{prefix} non-derivative cannot use derivative components")
                    check_raw_mapping(record, holding, prefix)
                    if record["normalized_sector"] == TECH:
                        tech_known += contribution
                    if record["normalized_industry"] == SEMI:
                        semi_known += contribution
                continue
            if record is None:
                fail(f"{prefix} derivative requires a mapping record")
            if record["derivative_components"] is None:
                fail(f"{prefix} derivative requires audited look-through components")
            check_raw_mapping(record, holding, prefix)
            for issuer, sector, industry, fraction in expand_mapping(
                record, mapping, issuer_registry
            ):
                part = contribution * fraction
                issuer_weights[issuer] = issuer_weights.get(issuer, 0.0) + part
                if sector == TECH:
                    tech_known += part
                if industry == SEMI:
                    semi_known += part
        if abs(market_sum - 1) > ROUNDING_TOLERANCE:
            fail(f"{ticker}.market_weight total must equal 1 within 5 bps")
        if exposure_sum < MIN_FUND_ECONOMIC_EXPOSURE - ROUNDING_TOLERANCE:
            fail(f"{ticker} parsed economic exposure is below 95% of fund NAV")

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
        fail(f"metrics keys do not match schema {SCHEMA_VERSION}")
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


def write_xlsx_fixture(path: Path, rows: list[list[object]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row, start=1):
            number_value = isinstance(value, (int, float)) and not isinstance(value, bool)
            column = ""
            current = column_index
            while current:
                current, remainder = divmod(current - 1, 26)
                column = chr(65 + remainder) + column
            reference = f"{column}{row_index}"
            if number_value:
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
            else:
                cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
                )
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Holdings" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet)
    return digest_file(path, MAX_SOURCE_BYTES, str(path))


def sample(root: Path) -> tuple[dict, Path]:
    review = "2026-07-30"
    packet_id = f"lookthrough-{review}-selftest"
    bundle = root / review / packet_id
    bundle.mkdir(parents=True)
    mapping_records = []
    registry_issuers: dict[str, dict] = {}
    registry_securities: dict[str, dict] = {}
    funds = []
    for fund_number, ticker in enumerate(FUNDS, start=1):
        source_rows = []
        direct_security_ids = []
        for index in range(10):
            is_alphabet = ticker == "QQQM" and index in {8, 9}
            raw_identifier = (
                "02079K305"
                if is_alphabet and index == 8
                else "02079K107"
                if is_alphabet
                else "000000001"
                if index == 0
                else f"{fund_number}{index:05d}00{index}"
            )
            security_id = f"CUSIP:{raw_identifier}"
            direct_security_ids.append(security_id)
            is_semi = index == 0 or ticker == "SOXX"
            sector = (
                "Technology"
                if is_semi
                else "Communication Services"
                if is_alphabet
                else "Industrials"
            )
            raw_name = (
                f"Alphabet Inc Class {'A' if index == 8 else 'C'}"
                if is_alphabet
                else f"{ticker} Security {index}"
            )
            raw_ticker = (
                "GOOGL"
                if is_alphabet and index == 8
                else "GOOG"
                if is_alphabet
                else f"{ticker}{index}"
            )
            source_rows.append(
                [
                    raw_identifier,
                    raw_ticker,
                    raw_name,
                    sector,
                    "Semiconductors" if is_semi else "Other",
                    "Equity",
                    10.0,
                    10_000_000,
                    10_000_000,
                ]
            )
            if not any(item["security_id"] == security_id for item in mapping_records):
                mapping_records.append(
                    {
                        "security_id": security_id,
                        "normalized_sector": (
                            TECH
                            if is_semi
                            else "Communication Services"
                            if is_alphabet
                            else "Industrials"
                        ),
                        "normalized_industry": SEMI if is_semi else OTHER_INDUSTRY,
                        "derivative_components": None,
                        "evidence": {
                            "source_url": "https://example.invalid/classification",
                            "as_of": "2026-07-29",
                        },
                    }
                )
                issuer_number = (
                    1
                    if raw_identifier == "000000001"
                    else 1_652_044
                    if is_alphabet
                    else int(raw_identifier)
                )
                issuer_id = f"cik:{issuer_number:010d}"
                registry_issuers.setdefault(
                    issuer_id,
                    {
                        "issuer_group_id": issuer_id,
                        "canonical_name": (
                            "Alphabet Inc"
                            if is_alphabet
                            else f"Self Test Issuer {issuer_number}"
                        ),
                        "evidence_url": f"https://example.invalid/cik/{issuer_number}",
                    },
                )
                registry_securities[security_id] = {
                    "security_id": security_id,
                    "canonical_security_id": security_id,
                    "issuer_group_id": issuer_id,
                    "evidence": {
                        "source_url": "https://example.invalid/identity",
                        "as_of": "2026-07-29",
                    },
                }
        if ticker == "SOXX":
            source_rows[-1] = [
                "900000009",
                "--",
                "SOXX Index Future",
                "Cash and/or Derivatives",
                "Futures",
                "Futures",
                0.01,
                10_000,
                500_000,
            ]
            source_rows[1][6] = 19.99
            source_rows[1][7] = 19_990_000
            source_rows[1][8] = 19_990_000
            future_security_id = "CUSIP:900000009"
            mapping_records.append(
                {
                    "security_id": future_security_id,
                    "normalized_sector": None,
                    "normalized_industry": None,
                    "derivative_components": [
                        {
                            "security_id": component_security_id,
                            "weight": 1 / len(direct_security_ids[:-1]),
                        }
                        for component_security_id in direct_security_ids[:-1]
                    ],
                    "evidence": {
                        "source_url": "https://example.invalid/derivative",
                        "as_of": "2026-07-29",
                    },
                }
            )
        headers = [
            "CUSIP",
            "Ticker",
            "Name",
            "Sector",
            "Industry",
            "Asset Class",
            "Weight (%)",
            "Market Value",
            "Notional Value",
        ]
        if ticker == "SPYM":
            source_file = "raw/SPYM.xlsx"
            source_sha = write_xlsx_fixture(
                bundle / source_file,
                [["SPYM 3 Holdings: As of 29-Jul-2026"], headers, *source_rows],
            )
        else:
            source_file = f"raw/{ticker}.csv"
            if ticker == "QQQM":
                invesco_headers = [
                    "Security Identifier",
                    "Holding Ticker",
                    "Holding Name",
                    "Date",
                    "Sector",
                    "Industry",
                    "Holding Type",
                    "Percentage of Fund",
                    "Market Value",
                    "Notional Value",
                ]
                source_rows = [
                    [*row[:3], "07/29/2026", *row[3:]] for row in source_rows
                ]
                source_table = [invesco_headers, *source_rows]
            else:
                source_table = [
                    ["Fund Holdings as of", "Jul 29, 2026"],
                    headers,
                    *source_rows,
                ]
            csv_text = io.StringIO()
            writer = csv.writer(csv_text, lineterminator="\n")
            writer.writerows(source_table)
            source_sha = write_fixture(bundle / source_file, csv_text.getvalue().encode())
        parsed = parse_source(ticker, bundle / source_file, SOURCE_FORMATS[ticker])
        funds.append(
            {
                "ticker": ticker,
                "source_name": "Official test fixture",
                "source_url": f"https://example.invalid/{ticker.lower()}",
                "source_format": SOURCE_FORMATS[ticker],
                "source_as_of": "2026-07-29",
                "retrieved_at": "2026-07-30T11:00:00+09:00",
                "source_file": source_file,
                "source_sha256": source_sha,
                "holdings": parsed["holdings"],
            }
        )
    for sedol, cusip in (
        ("SEDOL:BYVY8G0", "CUSIP:02079K305"),
        ("SEDOL:BYY88Y7", "CUSIP:02079K107"),
    ):
        registry_securities[sedol] = {
            "security_id": sedol,
            "canonical_security_id": cusip,
            "issuer_group_id": "cik:0001652044",
            "evidence": {
                "source_url": "https://example.invalid/cross-identifier",
                "as_of": "2026-07-29",
            },
        }
    issuer_registry = {
        "schema_version": ISSUER_REGISTRY_VERSION,
        "registry_id": "selftest-issuer-registry-1",
        "issuers": list(registry_issuers.values()),
        "securities": list(registry_securities.values()),
    }
    issuer_registry_sha = write_fixture(
        bundle / "issuer-registry.json", issuer_registry
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
        "nav": 100000,
        "current_market_values": {
            "cash": 16000,
            "SPYM": 55000,
            "QQQM": 28000,
            "SOXX": 1000,
        },
    }
    account_sha = write_fixture(bundle / "account.json", account)
    candidate = {
        "schema_version": CANDIDATE_VERSION,
        "candidate_packet_id": "candidate-selftest-1",
        "created_at": "2026-07-30T11:00:00+09:00",
        "expires_at": "2026-07-30T13:00:00+09:00",
        "ticker": "SOXX",
        "side": "ADD",
        "proposed_notional": 1000,
        "max_notional": 1000,
        "account_snapshot_id": account["account_snapshot_id"],
        "account_snapshot_sha256": account_sha,
    }
    candidate_sha = write_fixture(bundle / "candidate.json", candidate)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": packet_id,
        "review_date": review,
        "observed_at": "2026-07-30T12:00:00+09:00",
        "candidate_packet_id": "candidate-selftest-1",
        "candidate_path": "candidate.json",
        "candidate_sha256": candidate_sha,
        "weight_basis": "post_trade",
        "account_scenario_path": "account.json",
        "account_snapshot_sha256": account_sha,
        "issuer_registry_path": "issuer-registry.json",
        "issuer_registry_sha256": issuer_registry_sha,
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
        bad_account["observed_at"] = "2026-07-30T12:30:00+09:00"
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

        # Real manager rounding of 100.01% remains representable and parser-bound.
        rounded = copy.deepcopy(good)
        soxx_path = packet_path.parent / rounded["funds"][2]["source_file"]
        soxx_rows = list(csv.reader(io.StringIO(soxx_path.read_text(encoding="utf-8"))))
        header_index = next(
            index for index, row in enumerate(soxx_rows) if "Weight (%)" in row
        )
        weight_index = soxx_rows[header_index].index("Weight (%)")
        soxx_rows[header_index + 1][weight_index] = "10.01"
        buffer = io.StringIO()
        csv.writer(buffer, lineterminator="\n").writerows(soxx_rows)
        soxx_path.write_text(buffer.getvalue(), encoding="utf-8")
        rounded["funds"][2]["source_sha256"] = digest_file(
            soxx_path, MAX_SOURCE_BYTES, "rounded SOXX fixture"
        )
        rounded["funds"][2]["holdings"] = parse_source(
            "SOXX", soxx_path, SOURCE_FORMATS["SOXX"]
        )["holdings"]
        metrics, gates, verdict = evaluate(rounded, packet_path, allow_test=True)
        rounded["metrics"], rounded["gates"], rounded["verdict"] = metrics, gates, verdict
        rounded["packet_sha256"] = canonical_sha256(rounded)
        validate(rounded, packet_path, allow_test=True)

        duplicate = '{"schema_version":"1.3","schema_version":"0.0"}'
        duplicate_path = packet_path.parent / "duplicate.json"
        duplicate_path.write_text(duplicate, encoding="utf-8")
        try:
            read_json(duplicate_path, MAX_PACKET_BYTES, "duplicate fixture")
        except PacketError:
            pass
        else:
            fail("self-test accepted duplicate JSON keys")

    print(f"Look-through packet schema {SCHEMA_VERSION} self-tests passed.")


def validate_authority_catalogs() -> None:
    issuer = read_json(
        ISSUER_AUTHORITY_PATH, MAX_MAPPING_BYTES, "issuer authority"
    )
    require_keys(
        issuer,
        {"schema_version", "authority_id", "issuers", "securities"},
        "issuer authority",
    )
    if issuer["schema_version"] != ISSUER_REGISTRY_VERSION:
        fail(f"issuer authority schema_version must be {ISSUER_REGISTRY_VERSION}")
    if issuer["authority_id"] != "lookthrough-issuer-authority":
        fail("issuer authority_id is invalid")
    if not isinstance(issuer["issuers"], list) or not isinstance(
        issuer["securities"], list
    ):
        fail("issuer authority must contain issuer and security arrays")

    classification = read_json(
        CLASSIFICATION_AUTHORITY_PATH,
        MAX_MAPPING_BYTES,
        "classification authority",
    )
    require_keys(
        classification,
        {"schema_version", "authority_id", "taxonomy", "records"},
        "classification authority",
    )
    if classification["schema_version"] != MAPPING_VERSION:
        fail(f"classification authority schema_version must be {MAPPING_VERSION}")
    if (
        classification["authority_id"] != "lookthrough-classification-authority"
        or classification["taxonomy"] != "GICS"
        or not isinstance(classification["records"], list)
    ):
        fail("classification authority metadata is invalid")

    with tempfile.TemporaryDirectory(prefix="lookthrough-authority-") as tmp:
        root = Path(tmp)
        if issuer["issuers"] or issuer["securities"]:
            snapshot = {
                "schema_version": ISSUER_REGISTRY_VERSION,
                "registry_id": "authority-validation",
                "issuers": issuer["issuers"],
                "securities": issuer["securities"],
            }
            digest = write_fixture(root / "issuer-registry.json", snapshot)
            load_issuer_registry(
                root,
                "issuer-registry.json",
                digest,
                allow_test=False,
            )
        if classification["records"]:
            snapshot = {
                "schema_version": MAPPING_VERSION,
                "mapping_id": "authority-validation",
                "taxonomy": "GICS",
                "records": classification["records"],
            }
            digest = write_fixture(root / "mapping.json", snapshot)
            load_mapping(root, "mapping.json", digest, allow_test=False)


def scan_root(root: Path) -> None:
    validate_authority_catalogs()
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
