#!/usr/bin/env python3
"""Validate immutable ETF look-through evidence packets without third-party packages."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

FUNDS = ("SPYM", "QQQM", "SOXX")
TECH = "Information Technology"
SEMI = "Semiconductors & Semiconductor Equipment"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA_VERSION = "1.0"
EPS = 1e-9


class PacketError(ValueError):
    pass


def fail(message: str) -> None:
    raise PacketError(message)


def number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        fail(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        fail(f"{field} must be finite")
    return result


def weight(value: object, field: str) -> float:
    result = number(value, field)
    if result < -EPS or result > 1 + EPS:
        fail(f"{field} must be within [0, 1]")
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


def official_https(url: object, field: str) -> None:
    if not isinstance(url, str):
        fail(f"{field} must be an HTTPS URL")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        fail(f"{field} must be an HTTPS URL")


def canonical_sha256(packet: dict) -> str:
    body = copy.deepcopy(packet)
    body["packet_sha256"] = ""
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def validate(packet: dict, *, allow_test: bool = False) -> dict[str, float]:
    if not isinstance(packet, dict):
        fail("packet root must be an object")
    if packet.get("_template") is True:
        fail("template is not a Production packet")
    if packet.get("test_only") is True and not allow_test:
        fail("test_only packet cannot enter Production")
    if packet.get("schema_version") != SCHEMA_VERSION:
        fail(f"schema_version must be {SCHEMA_VERSION}")

    review_date = iso_date(packet.get("review_date"), "review_date")
    observed_at = iso_datetime(packet.get("observed_at"), "observed_at")
    if observed_at.date() != review_date:
        fail("observed_at calendar date must equal review_date")

    packet_id = packet.get("packet_id")
    expected_prefix = f"lookthrough-{review_date.isoformat()}-"
    if not isinstance(packet_id, str) or not packet_id.startswith(expected_prefix):
        fail(f"packet_id must start with {expected_prefix}")

    portfolio = packet.get("portfolio_weights")
    if not isinstance(portfolio, dict) or set(portfolio) != {"cash", *FUNDS}:
        fail("portfolio_weights must contain exactly cash, SPYM, QQQM and SOXX")
    portfolio_weights = {key: weight(value, f"portfolio_weights.{key}") for key, value in portfolio.items()}
    if abs(sum(portfolio_weights.values()) - 1) > EPS:
        fail("portfolio_weights must sum to 1")
    if portfolio_weights["SPYM"] <= EPS or portfolio_weights["QQQM"] <= EPS:
        fail("SPYM and QQQM portfolio weights must be positive")
    if 1 - portfolio_weights["cash"] <= EPS:
        fail("non-cash portfolio weight must be positive")
    mapping_version = packet.get("mapping_version")
    if not isinstance(mapping_version, str) or not mapping_version.strip():
        fail("mapping_version is required")

    funds = packet.get("funds")
    if not isinstance(funds, list) or len(funds) != 3:
        fail("funds must contain exactly three records")
    by_ticker = {}
    for fund in funds:
        if not isinstance(fund, dict):
            fail("each fund must be an object")
        ticker = fund.get("ticker")
        if ticker not in FUNDS or ticker in by_ticker:
            fail("fund tickers must be unique SPYM, QQQM and SOXX")
        by_ticker[ticker] = fund
    if set(by_ticker) != set(FUNDS):
        fail("fund tickers must be exactly SPYM, QQQM and SOXX")

    source_dates = set()
    issuer: dict[str, float] = {}
    tech_known = semi_known = issuer_covered = classified = invested = 0.0

    for ticker in FUNDS:
        fund = by_ticker[ticker]
        if fund.get("source_name") in (None, ""):
            fail(f"{ticker}.source_name is required")
        official_https(fund.get("source_url"), f"{ticker}.source_url")
        digest = fund.get("source_sha256")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            fail(f"{ticker}.source_sha256 must be a lowercase SHA-256")
        source_dates.add(iso_date(fund.get("source_as_of"), f"{ticker}.source_as_of"))

        holdings = fund.get("holdings")
        if not isinstance(holdings, list) or not holdings:
            fail(f"{ticker}.holdings must be non-empty")
        holding_sum = 0.0
        for index, holding in enumerate(holdings):
            prefix = f"{ticker}.holdings[{index}]"
            if not isinstance(holding, dict):
                fail(f"{prefix} must be an object")
            security_id = holding.get("security_id")
            if not isinstance(security_id, str) or not security_id.strip():
                fail(f"{prefix}.security_id is required")
            if "raw_sector" not in holding or "raw_industry" not in holding:
                fail(f"{prefix} must preserve raw_sector and raw_industry")
            holding_weight = weight(holding.get("weight"), f"{prefix}.weight")
            holding_sum += holding_weight
            contribution = portfolio_weights[ticker] * holding_weight
            invested += contribution

            issuer_id = holding.get("issuer_group_id")
            sector = holding.get("normalized_sector")
            industry = holding.get("normalized_industry")
            if issuer_id not in (None, ""):
                if not isinstance(issuer_id, str):
                    fail(f"{prefix}.issuer_group_id must be a string or null")
                issuer_covered += contribution
                issuer[issuer_id] = issuer.get(issuer_id, 0.0) + contribution
            if sector not in (None, "") and industry not in (None, ""):
                classified += contribution
            if sector == TECH:
                tech_known += contribution
            if industry == SEMI:
                semi_known += contribution
        if abs(holding_sum - 1) > EPS:
            fail(f"{ticker}.holdings weights must sum to 1")

    if len(source_dates) != 1:
        fail("Green packet requires identical source_as_of for SPYM, QQQM and SOXX")

    noncash = 1 - portfolio_weights["cash"]
    if abs(invested - noncash) > EPS:
        fail("look-through contributions do not reconcile to non-cash weight")
    unclassified = noncash - min(issuer_covered, classified)
    issuer_max = max(issuer.values(), default=0.0)
    metrics = {
        "issuer_coverage_ratio": issuer_covered / noncash if noncash else 1.0,
        "classification_coverage_ratio": classified / noncash if noncash else 1.0,
        "unclassified_lookthrough_weight": unclassified,
        "technology_known_weight": tech_known,
        "technology_upper_bound": tech_known + unclassified,
        "semiconductor_known_weight": semi_known,
        "semiconductor_upper_bound": semi_known + unclassified,
        "max_issuer_known_weight": issuer_max,
        "max_issuer_upper_bound": issuer_max + unclassified,
    }

    reported = packet.get("metrics")
    if not isinstance(reported, dict) or set(reported) != set(metrics):
        fail("metrics keys do not match the schema")
    for key, calculated in metrics.items():
        if abs(weight(reported[key], f"metrics.{key}") - calculated) > EPS:
            fail(f"metrics.{key} does not reconcile")

    gates = packet.get("gates")
    expected_gates = {
        "technology_below_50": metrics["technology_upper_bound"] < 0.50 - EPS,
        "semiconductor_at_or_below_15": metrics["semiconductor_upper_bound"] <= 0.15 + EPS,
        "issuer_at_or_below_10": metrics["max_issuer_upper_bound"] <= 0.10 + EPS,
        "full_issuer_coverage": abs(metrics["issuer_coverage_ratio"] - 1) <= EPS,
        "full_classification_coverage": abs(metrics["classification_coverage_ratio"] - 1) <= EPS,
    }
    if gates != expected_gates:
        fail("gates do not equal validator-calculated results")

    expected_verdict = "DATA GATE PASS" if all(expected_gates.values()) else "DATA INCOMPLETE"
    if packet.get("verdict") != expected_verdict:
        fail(f"verdict must be {expected_verdict}")

    digest = packet.get("packet_sha256")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        fail("packet_sha256 must be a lowercase SHA-256")
    if digest != canonical_sha256(packet):
        fail("packet_sha256 does not match canonical packet content")
    return metrics


def sample() -> dict:
    holdings = {}
    for ticker in FUNDS:
        rows = []
        for index in range(10):
            is_semi = index == 0 or ticker == "SOXX"
            rows.append({
                "security_id": "AAA" if index == 0 else f"{ticker}-{index}",
                "raw_sector": "Technology" if is_semi else "Other",
                "raw_industry": "Semiconductors" if is_semi else "Other",
                "weight": 0.10,
                "issuer_group_id": "issuer-a" if index == 0 else f"issuer-{ticker.lower()}-{index}",
                "normalized_sector": TECH if is_semi else "Other",
                "normalized_industry": SEMI if is_semi else "Other",
            })
        holdings[ticker] = rows
    packet = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": "lookthrough-2026-07-30-selftest",
        "review_date": "2026-07-30",
        "observed_at": "2026-07-30T12:00:00+09:00",
        "test_only": True,
        "mapping_version": "selftest-1",
        "portfolio_weights": {"cash": 0.15, "SPYM": 0.55, "QQQM": 0.28, "SOXX": 0.02},
        "funds": [
            {
                "ticker": ticker,
                "source_name": "Official test fixture",
                "source_url": f"https://example.invalid/{ticker}",
                "source_as_of": "2026-07-29",
                "source_sha256": hashlib.sha256(ticker.encode()).hexdigest(),
                "holdings": holdings[ticker],
            }
            for ticker in FUNDS
        ],
        "metrics": {},
        "gates": {},
        "verdict": "",
        "packet_sha256": "",
    }

    noncash = 0.85
    issuer_a = 0.55 * 0.10 + 0.28 * 0.10
    tech = issuer_a + 0.02
    packet["metrics"] = {
        "issuer_coverage_ratio": 1.0,
        "classification_coverage_ratio": 1.0,
        "unclassified_lookthrough_weight": 0.0,
        "technology_known_weight": tech,
        "technology_upper_bound": tech,
        "semiconductor_known_weight": tech,
        "semiconductor_upper_bound": tech,
        "max_issuer_known_weight": issuer_a,
        "max_issuer_upper_bound": issuer_a,
    }
    packet["gates"] = {
        "technology_below_50": True,
        "semiconductor_at_or_below_15": True,
        "issuer_at_or_below_10": True,
        "full_issuer_coverage": True,
        "full_classification_coverage": True,
    }
    packet["verdict"] = "DATA GATE PASS"
    packet["packet_sha256"] = canonical_sha256(packet)
    return packet


def self_test() -> None:
    good = sample()
    validate(good, allow_test=True)
    mutations = [
        ("date skew", lambda p: p["funds"][0].update(source_as_of="2026-07-28")),
        ("weight drift", lambda p: p["funds"][0]["holdings"][0].update(weight=0.11)),
        ("metric forgery", lambda p: p["metrics"].update(technology_upper_bound=0.0)),
        ("verdict forgery", lambda p: p.update(verdict="DATA INCOMPLETE")),
        ("hash mismatch", lambda p: p.update(packet_id="lookthrough-2026-07-30-tampered")),
        ("non-finite", lambda p: p["portfolio_weights"].update(SOXX=float("nan"))),
    ]
    for name, mutate in mutations:
        bad = copy.deepcopy(good)
        mutate(bad)
        try:
            validate(bad, allow_test=True)
        except PacketError:
            continue
        fail(f"self-test accepted invalid packet: {name}")
    print("Look-through packet self-tests passed.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        for path in args.paths:
            packet = json.loads(path.read_text(encoding="utf-8"))
            validate(packet)
            print(f"{path}: valid")
    except (PacketError, json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not args.self_test and not args.paths:
        parser.error("provide --self-test or at least one packet path")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
