#!/usr/bin/env python3
"""Adversarial regression tests for Look-through Bundle v1.5."""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import parse_lookthrough_sources as parser
import validate_lookthrough_packet as validator


def reject(name: str, packet: dict, packet_path: Path) -> None:
    packet["packet_sha256"] = validator.canonical_sha256(packet)
    try:
        validator.validate(packet, packet_path, allow_test=True)
    except validator.PacketError:
        return
    raise AssertionError(f"validator accepted adversarial case: {name}")


def rewrite_json(path: Path, value: dict) -> str:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return validator.digest_file(path, validator.MAX_MAPPING_BYTES, str(path))


def reject_source(name: str, ticker: str, path: Path, source_format: str) -> None:
    try:
        parser.parse_source(ticker, path, source_format)
    except parser.SourceParseError:
        return
    raise AssertionError(f"parser accepted adversarial source: {name}")


def test_history_checker(root: Path) -> None:
    repository = root / "history-repository"
    (repository / "scripts").mkdir(parents=True)
    bundle = (
        repository
        / "08-Data"
        / "SNAPSHOTS"
        / "lookthrough"
        / "2026-07-31"
        / "test-bundle"
    )
    bundle.mkdir(parents=True)
    packet = bundle / "packet.json"
    packet.write_text('{"packet_id":"immutable"}\n', encoding="utf-8")
    shutil.copy2(
        Path(__file__).resolve().parent / "check_lookthrough_history.py",
        repository / "scripts" / "check_lookthrough_history.py",
    )
    commands = [
        ["git", "init", "-q"],
        ["git", "config", "user.email", "audit@example.invalid"],
        ["git", "config", "user.name", "Audit"],
        ["git", "add", "."],
        ["git", "commit", "-qm", "base"],
    ]
    for command in commands:
        subprocess.run(command, cwd=repository, check=True)
    base_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()
    checker = ["python3", "scripts/check_lookthrough_history.py"]
    assert subprocess.run(
        [*checker, base_sha], cwd=repository, check=False, capture_output=True
    ).returncode == 0
    assert subprocess.run(
        [*checker, "f" * 40], cwd=repository, check=False, capture_output=True
    ).returncode != 0
    packet.write_text('{"packet_id":"mutated"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "mutate"], cwd=repository, check=True)
    assert subprocess.run(
        [*checker, base_sha], cwd=repository, check=False, capture_output=True
    ).returncode != 0


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lookthrough-adversarial-") as tmp:
        tmp_path = Path(tmp)
        qqqm_path = tmp_path / "QQQM-real-format.json"
        qqqm_payload = {
            "cusip": "46138G649",
            "effectiveDate": "2026-07-29",
            "effectiveBusinessDate": "2026-07-29",
            "totalNumberOfHoldings": 2,
            "holdings": [
                {
                    "cusip": "02079K305",
                    "ticker": "GOOGL",
                    "issuerName": "Alphabet Inc Class A",
                    "securityTypeName": "Common Stock",
                    "securityTypeCode": "COM",
                    "percentageOfTotalNetAssets": 60,
                    "marketValueBase": 600,
                },
                {
                    "cusip": "02079K107",
                    "ticker": "--",
                    "issuerName": "Alphabet Inc Class C",
                    "securityTypeName": "Common Stock",
                    "securityTypeCode": "COM",
                    "percentageOfTotalNetAssets": 40,
                    "marketValueBase": 400,
                },
            ],
        }
        qqqm_path.write_text(json.dumps(qqqm_payload), encoding="utf-8")
        parsed_qqqm = parser.parse_source("QQQM", qqqm_path, "invesco-json-v1")
        assert parsed_qqqm["source_as_of"] == "2026-07-29"
        assert [item["security_id"] for item in parsed_qqqm["holdings"]] == [
            "CUSIP:02079K305",
            "CUSIP:02079K107",
        ]
        wrong_product_path = tmp_path / "QQQM-wrong-product.json"
        wrong_product = copy.deepcopy(qqqm_payload)
        wrong_product["cusip"] = "000000000"
        wrong_product_path.write_text(json.dumps(wrong_product), encoding="utf-8")
        reject_source(
            "QQQM response for another product",
            "QQQM",
            wrong_product_path,
            "invesco-json-v1",
        )
        wrong_count_path = tmp_path / "QQQM-wrong-count.json"
        wrong_count = copy.deepcopy(qqqm_payload)
        wrong_count["totalNumberOfHoldings"] = 999
        wrong_count_path.write_text(json.dumps(wrong_count), encoding="utf-8")
        reject_source(
            "QQQM declared holdings count mismatch",
            "QQQM",
            wrong_count_path,
            "invesco-json-v1",
        )
        wrong_date_path = tmp_path / "QQQM-wrong-business-date.json"
        wrong_date = copy.deepcopy(qqqm_payload)
        wrong_date["effectiveBusinessDate"] = "2026-07-28"
        wrong_date_path.write_text(json.dumps(wrong_date), encoding="utf-8")
        reject_source(
            "QQQM effective date mismatch",
            "QQQM",
            wrong_date_path,
            "invesco-json-v1",
        )
        duplicate_path = tmp_path / "QQQM-duplicate-key.json"
        duplicate_path.write_text(
            json.dumps(qqqm_payload).replace(
                '"cusip": "46138G649",',
                '"cusip": "000000000", "cusip": "46138G649",',
                1,
            ),
            encoding="utf-8",
        )
        reject_source(
            "QQQM duplicate product identity",
            "QQQM",
            duplicate_path,
            "invesco-json-v1",
        )
        synthetic_path = tmp_path / "QQQM-synthetic-cash.json"
        synthetic = copy.deepcopy(qqqm_payload)
        synthetic["holdings"].extend(
            [
                {
                    "cusip": "NQU6",
                    "ticker": "NQU6",
                    "issuerName": "CME E-Mini NASDAQ 100 Index Future",
                    "securityTypeName": "Index Future",
                    "securityTypeCode": "IFUT",
                    "percentageOfTotalNetAssets": 0.1,
                    "marketValueBase": 100,
                },
                {
                    "cusip": "NQU6",
                    "ticker": "NQU6_",
                    "issuerName": "CONTRA FUTURE NASDAQ 100 E-MINI",
                    "securityTypeName": "Synthetic Cash",
                    "securityTypeCode": "SYN",
                    "percentageOfTotalNetAssets": -0.1,
                    "marketValueBase": -100,
                },
            ]
        )
        synthetic["totalNumberOfHoldings"] = len(synthetic["holdings"])
        synthetic_path.write_text(json.dumps(synthetic), encoding="utf-8")
        parsed_synthetic = parser.parse_source(
            "QQQM", synthetic_path, "invesco-json-v1"
        )["holdings"]
        future = next(item for item in parsed_synthetic if item["security_id"].endswith(".IFUT"))
        contra = next(item for item in parsed_synthetic if item["security_id"].endswith(".SYN"))
        assert future["instrument_type"] == "derivative"
        assert future["exposure_weight"] > 0
        assert contra["instrument_type"] == "cash"
        assert contra["exposure_weight"] == 0
        missing_id_path = tmp_path / "QQQM-placeholder-only.json"
        missing_id = copy.deepcopy(qqqm_payload)
        missing_id["holdings"][0]["cusip"] = None
        missing_id["holdings"][0]["ticker"] = "--"
        missing_id_path.write_text(json.dumps(missing_id), encoding="utf-8")
        try:
            parser.parse_source("QQQM", missing_id_path, "invesco-json-v1")
        except parser.SourceParseError:
            pass
        else:
            raise AssertionError("parser accepted a placeholder ticker without a stable ID")

        spym_path = tmp_path / "SPYM-real-format.xlsx"
        validator.write_xlsx_fixture(
            spym_path,
            [
                ["SPYM 3 Holdings: As of 29-Jul-2026"],
                [
                    "Identifier",
                    "SEDOL",
                    "Ticker",
                    "Name",
                    "Sector",
                    "Industry",
                    "Asset Class",
                    "Weight (%)",
                    "Market Value",
                    "Notional Value",
                ],
                [
                    "02079K305",
                    "BYVY8G0",
                    "GOOGL",
                    "Alphabet Inc Class A",
                    "Communication Services",
                    "Interactive Media",
                    "Equity",
                    60,
                    600,
                    600,
                ],
                [
                    "594918104",
                    "",
                    "MSFT",
                    "Microsoft Corp",
                    "Technology",
                    "Software",
                    "Equity",
                    40,
                    400,
                    400,
                ],
            ],
        )
        parsed_spym = parser.parse_source("SPYM", spym_path, "ssga-xlsx-v1")
        assert parsed_spym["source_as_of"] == "2026-07-29"
        assert parsed_spym["holdings"][0]["security_id"] == "CUSIP:02079K305"
        assert parsed_spym["holdings"][0]["source_identifiers"] == [
            "CUSIP:02079K305",
            "SEDOL:BYVY8G0",
        ]
        wrong_spym_path = tmp_path / "SPYM-wrong-product.xlsx"
        validator.write_xlsx_fixture(
            wrong_spym_path,
            [
                ["NOT SPYM DATA: As of 29-Jul-2026"],
                [
                    "CUSIP",
                    "Ticker",
                    "Name",
                    "Asset Class",
                    "Weight (%)",
                    "Market Value",
                    "Notional Value",
                ],
                ["02079K305", "GOOGL", "Alphabet Inc", "Equity", 100, 1000, 1000],
            ],
        )
        reject_source(
            "State Street workbook for another product",
            "SPYM",
            wrong_spym_path,
            "ssga-xlsx-v1",
        )
        wrong_soxx_path = tmp_path / "SOXX-wrong-product.csv"
        wrong_soxx_path.write_text(
            "iShares Another ETF\n"
            'Fund Holdings as of,\"Jul 29, 2026\"\n'
            "Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value\n"
            "NVDA,NVIDIA CORP,Information Technology,Equity,1000,100,1000\n",
            encoding="utf-8",
        )
        reject_source(
            "iShares CSV for another product",
            "SOXX",
            wrong_soxx_path,
            "ishares-csv-v1",
        )

        good, packet_path = validator.sample(Path(tmp))
        validator.validate(good, packet_path, allow_test=True)
        shadow = packet_path.parent / "shadow-packet.json"
        shadow.write_text("{}\n", encoding="utf-8")
        reject("extra unbound bundle file", copy.deepcopy(good), packet_path)
        shadow.unlink()

        account_path = packet_path.parent / good["account_scenario_path"]
        candidate_path = packet_path.parent / good["candidate_path"]
        original_account = account_path.read_bytes()
        original_candidate = candidate_path.read_bytes()
        observed_hold = copy.deepcopy(good)
        account = validator.read_json(
            account_path, validator.MAX_ACCOUNT_BYTES, "HOLD account"
        )
        account["current_market_values"]["cash"] = 9000
        account["current_market_values"]["SOXX"] = 8000
        account_sha = rewrite_json(account_path, account)
        candidate = validator.read_json(
            candidate_path, validator.MAX_ACCOUNT_BYTES, "HOLD candidate"
        )
        candidate["side"] = "HOLD"
        candidate["proposed_notional"] = 0
        candidate["max_notional"] = 0
        candidate["account_snapshot_sha256"] = account_sha
        candidate_sha = rewrite_json(candidate_path, candidate)
        observed_hold["account_snapshot_sha256"] = account_sha
        observed_hold["candidate_sha256"] = candidate_sha
        observed_hold["weight_basis"] = "current"
        observed_hold["portfolio_weights"] = {
            "cash": 0.09,
            "other": 0.0,
            "SPYM": 0.55,
            "QQQM": 0.28,
            "SOXX": 0.08,
        }
        spym = observed_hold["funds"][0]
        spym["status"] = "unavailable"
        spym["failure_reason"] = "official download unavailable at retrieval time"
        spym["source_as_of"] = None
        spym["source_file"] = None
        spym["source_sha256"] = None
        spym["holdings"] = []
        unavailable_spym_source = packet_path.parent / good["funds"][0]["source_file"]
        unavailable_spym_bytes = unavailable_spym_source.read_bytes()
        unavailable_spym_source.unlink()
        metrics, gates, verdict = validator.evaluate(
            observed_hold, packet_path, allow_test=True
        )
        observed_hold["metrics"] = metrics
        observed_hold["gates"] = gates
        observed_hold["verdict"] = verdict
        observed_hold["packet_sha256"] = validator.canonical_sha256(observed_hold)
        validator.validate(observed_hold, packet_path, allow_test=True)
        assert verdict == "DATA INCOMPLETE"
        assert gates["sources_complete_same_date"] is False
        assert gates["soxx_at_or_below_3"] is False
        assert metrics["issuer_unknown_weight"] >= 0.55
        unavailable_spym_source.write_bytes(unavailable_spym_bytes)
        account_path.write_bytes(original_account)
        candidate_path.write_bytes(original_candidate)

        residual = copy.deepcopy(good)
        account = validator.read_json(
            account_path, validator.MAX_ACCOUNT_BYTES, "residual account"
        )
        account["current_market_values"]["cash"] -= 5000
        account["current_market_values"]["other"] = 5000
        account["direct_holdings"] = [
            {
                "security_id": "TICKER:UNKNOWN",
                "source_identifiers": ["TICKER:UNKNOWN"],
                "raw_name": "Unmapped Direct Equity",
                "instrument_type": "equity",
                "market_value": 5000,
                "raw_sector": None,
                "raw_industry": None,
            }
        ]
        account_sha = rewrite_json(account_path, account)
        candidate = validator.read_json(
            candidate_path, validator.MAX_ACCOUNT_BYTES, "residual candidate"
        )
        candidate["account_snapshot_sha256"] = account_sha
        candidate_sha = rewrite_json(candidate_path, candidate)
        residual["account_snapshot_sha256"] = account_sha
        residual["candidate_sha256"] = candidate_sha
        residual["portfolio_weights"]["cash"] -= 0.05
        residual["portfolio_weights"]["other"] = 0.05
        metrics, _, _ = validator.evaluate(residual, packet_path, allow_test=True)
        assert abs(metrics["issuer_unknown_weight"] - 0.05) < validator.EPS
        assert abs(metrics["classification_unknown_weight"] - 0.05) < validator.EPS
        account_path.write_bytes(original_account)
        candidate_path.write_bytes(original_candidate)

        registry_path = packet_path.parent / good["issuer_registry_path"]
        identities = validator.load_issuer_registry(
            packet_path.parent,
            good["issuer_registry_path"],
            good["issuer_registry_sha256"],
            allow_test=True,
        )
        assert identities["SEDOL:BYVY8G0"] == {
            "canonical_security_id": "CUSIP:02079K305",
            "issuer_group_id": "cik:0001652044",
        }

        original_registry = registry_path.read_bytes()
        registry = validator.read_json(
            registry_path, validator.MAX_MAPPING_BYTES, "partial issuer registry"
        )
        mapping_snapshot = validator.read_json(
            packet_path.parent / good["mapping_path"],
            validator.MAX_MAPPING_BYTES,
            "derivative mapping snapshot",
        )
        derivative = next(
            item
            for item in mapping_snapshot["records"]
            if item["derivative_components"] is not None
        )
        missing_component_id = derivative["derivative_components"][0]["security_id"]
        registry["securities"] = [
            item
            for item in registry["securities"]
            if item["security_id"] != missing_component_id
        ]
        partial_identity = copy.deepcopy(good)
        partial_identity["issuer_registry_sha256"] = rewrite_json(
            registry_path, registry
        )
        metrics, gates, verdict = validator.evaluate(
            partial_identity, packet_path, allow_test=True
        )
        partial_identity["metrics"] = metrics
        partial_identity["gates"] = gates
        partial_identity["verdict"] = verdict
        partial_identity["packet_sha256"] = validator.canonical_sha256(
            partial_identity
        )
        validator.validate(partial_identity, packet_path, allow_test=True)
        assert metrics["issuer_unknown_weight"] > 0
        assert metrics["classification_unknown_weight"] == 0
        registry_path.write_bytes(original_registry)

        cross_identifier = copy.deepcopy(good)
        original_spym_source = (
            packet_path.parent / good["funds"][0]["source_file"]
        ).read_bytes()
        spym_fund = cross_identifier["funds"][0]
        cross_rows = [
            ["SPYM 3 Holdings: As of 29-Jul-2026"],
            [
                "Identifier",
                "SEDOL",
                "Ticker",
                "Name",
                "Sector",
                "Industry",
                "Asset Class",
                "Weight (%)",
                "Market Value",
                "Notional Value",
            ],
        ]
        for index, holding in enumerate(spym_fund["holdings"]):
            security_id = holding["security_id"]
            identifier = security_id.removeprefix("CUSIP:")
            sedol = ""
            name = holding["raw_name"]
            sector = holding["raw_sector"]
            industry = holding["raw_industry"]
            ticker = f"SPYM{index}"
            if index == 0:
                identifier = ""
                sedol = "BYVY8G0"
                ticker = "GOOGL"
                name = "Alphabet Inc Class A"
                sector = "Communication Services"
                industry = "Interactive Media"
            weight = holding["market_weight"] * 100
            cross_rows.append(
                [
                    identifier,
                    sedol,
                    ticker,
                    name,
                    sector,
                    industry,
                    "Equity",
                    weight,
                    weight * 1_000_000,
                    weight * 1_000_000,
                ]
            )
        spym_source = packet_path.parent / spym_fund["source_file"]
        spym_fund["source_sha256"] = validator.write_xlsx_fixture(
            spym_source, cross_rows
        )
        spym_fund["holdings"] = parser.parse_source(
            "SPYM", spym_source, "ssga-xlsx-v1"
        )["holdings"]
        metrics, gates, verdict = validator.evaluate(
            cross_identifier, packet_path, allow_test=True
        )
        cross_identifier["metrics"] = metrics
        cross_identifier["gates"] = gates
        cross_identifier["verdict"] = verdict
        cross_identifier["packet_sha256"] = validator.canonical_sha256(
            cross_identifier
        )
        validator.validate(cross_identifier, packet_path, allow_test=True)
        assert metrics["max_issuer_known_weight"] > 0.10
        assert gates["issuer_at_or_below_10"] is False
        assert verdict == "POLICY GATE FAIL"
        spym_source.write_bytes(original_spym_source)

        unrelated_holdings = copy.deepcopy(good)
        unrelated_holdings["funds"][0]["holdings"][0]["raw_name"] = "UNRELATED MANUAL ROW"
        reject("packet holdings unrelated to archived bytes", unrelated_holdings, packet_path)

        hidden_soxx = copy.deepcopy(good)
        for holding in hidden_soxx["funds"][2]["holdings"]:
            holding["instrument_type"] = "other"
            holding["exposure_weight"] = 0.0
        reject("SOXX erased as zero-exposure other instruments", hidden_soxx, packet_path)

        wrong_source_path = copy.deepcopy(good)
        wrong_source_path["funds"][0]["source_file"] = "account.json"
        wrong_source_path["funds"][0]["source_sha256"] = good["account_snapshot_sha256"]
        reject("account file reused as manager source", wrong_source_path, packet_path)

        mapping_path = packet_path.parent / good["mapping_path"]
        original_mapping = mapping_path.read_bytes()
        mapping = validator.read_json(
            mapping_path, validator.MAX_MAPPING_BYTES, "adversarial mapping"
        )
        mapping["records"][0]["issuer_group_id"] = "cik:0000000001"
        alias_packet = copy.deepcopy(good)
        alias_packet["mapping_sha256"] = rewrite_json(mapping_path, mapping)
        reject("mapping bypasses issuer registry", alias_packet, packet_path)
        mapping_path.write_bytes(original_mapping)

        original_registry = registry_path.read_bytes()
        registry = validator.read_json(
            registry_path, validator.MAX_MAPPING_BYTES, "adversarial issuer registry"
        )
        alphabet = next(
            item
            for item in registry["issuers"]
            if item["issuer_group_id"] == "cik:0001652044"
        )
        registry["issuers"].append(
            {
                "issuer_group_id": "cik:9999999999",
                "canonical_name": f"{alphabet['canonical_name']} Class C",
                "evidence_url": "https://example.invalid/cik/9999999999",
            }
        )
        alphabet_c = next(
            item
            for item in registry["securities"]
            if item["security_id"] == "CUSIP:02079K107"
        )
        alphabet_c["issuer_group_id"] = "cik:9999999999"
        split_packet = copy.deepcopy(good)
        split_packet["issuer_registry_sha256"] = rewrite_json(registry_path, registry)
        reject("Alphabet A and C split across issuer identities", split_packet, packet_path)
        registry_path.write_bytes(original_registry)

        registry = validator.read_json(
            registry_path, validator.MAX_MAPPING_BYTES, "adversarial issuer registry"
        )
        registry["issuers"].append(
            {
                "issuer_group_id": "cik:9999999999",
                "canonical_name": "False SEDOL Alias Issuer",
                "evidence_url": "https://example.invalid/cik/9999999999",
            }
        )
        sedol_alias = next(
            item
            for item in registry["securities"]
            if item["security_id"] == "SEDOL:BYVY8G0"
        )
        sedol_alias["issuer_group_id"] = "cik:9999999999"
        cross_id_split = copy.deepcopy(good)
        cross_id_split["issuer_registry_sha256"] = rewrite_json(
            registry_path, registry
        )
        reject(
            "SEDOL and canonical CUSIP split across issuer identities",
            cross_id_split,
            packet_path,
        )
        registry_path.write_bytes(original_registry)

        qqqm_source = packet_path.parent / good["funds"][1]["source_file"]
        original_qqqm_source = qqqm_source.read_bytes()
        qqqm_payload = json.loads(qqqm_source.read_text(encoding="utf-8"))
        for holding in qqqm_payload["holdings"]:
            holding.pop("sectorName", None)
        qqqm_source.write_text(json.dumps(qqqm_payload), encoding="utf-8")
        false_classification = copy.deepcopy(good)
        false_classification["funds"][1]["source_sha256"] = validator.digest_file(
            qqqm_source, validator.MAX_SOURCE_BYTES, "QQQM missing-classification fixture"
        )
        false_classification["funds"][1]["holdings"] = parser.parse_source(
            "QQQM", qqqm_source, "invesco-json-v1"
        )["holdings"]
        mapping = validator.read_json(
            mapping_path, validator.MAX_MAPPING_BYTES, "adversarial mapping"
        )
        semiconductor = next(
            item
            for item in mapping["records"]
            if item["normalized_industry"] == validator.SEMI
        )
        semiconductor["normalized_sector"] = "Industrials"
        false_classification["mapping_sha256"] = rewrite_json(mapping_path, mapping)
        reject(
            "bundle mapping cannot violate controlled GICS semantics",
            false_classification,
            packet_path,
        )
        mapping_path.write_bytes(original_mapping)
        qqqm_source.write_bytes(original_qqqm_source)

        mapping = validator.read_json(
            mapping_path, validator.MAX_MAPPING_BYTES, "adversarial mapping"
        )
        derivative = next(
            item for item in mapping["records"] if item["derivative_components"] is not None
        )
        derivative["derivative_components"][0]["issuer_group_id"] = "cik:9999999999"
        free_issuer_packet = copy.deepcopy(good)
        free_issuer_packet["mapping_sha256"] = rewrite_json(mapping_path, mapping)
        reject("derivative component uses a free issuer id", free_issuer_packet, packet_path)
        mapping_path.write_bytes(original_mapping)

        account_path = packet_path.parent / good["account_scenario_path"]
        original_account = account_path.read_bytes()
        account = validator.read_json(
            account_path, validator.MAX_ACCOUNT_BYTES, "adversarial account"
        )
        account["observed_at"] = "2026-07-30T12:30:00+09:00"
        late_account = copy.deepcopy(good)
        late_account["account_snapshot_sha256"] = rewrite_json(account_path, account)
        reject("account snapshot later than packet", late_account, packet_path)
        account_path.write_bytes(original_account)

        missing_candidate = copy.deepcopy(good)
        missing_candidate["candidate_path"] = "missing-candidate.json"
        reject("candidate bound only by an unresolvable string", missing_candidate, packet_path)

        future = copy.deepcopy(good)
        future["packet_id"] = "lookthrough-2099-01-01-future"
        future["review_date"] = "2099-01-01"
        future["observed_at"] = "2099-01-01T12:00:00+09:00"
        future_path = (
            Path(tmp)
            / "2099-01-01"
            / "lookthrough-2099-01-01-future"
            / "packet.json"
        )
        future_path.parent.mkdir(parents=True)
        reject("future-dated 2099 bundle", future, future_path)

        test_history_checker(tmp_path)

    print("Look-through Bundle v1.5 adversarial tests passed.")


if __name__ == "__main__":
    main()
