#!/usr/bin/env python3
"""Independent adversarial regression tests for Look-through Bundle v1.3."""

from __future__ import annotations

import copy
import csv
import io
import json
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


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="lookthrough-adversarial-") as tmp:
        tmp_path = Path(tmp)
        qqqm_path = tmp_path / "QQQM-real-format.csv"
        qqqm_text = io.StringIO()
        csv.writer(qqqm_text, lineterminator="\n").writerows(
            [
                [
                    "Security Identifier",
                    "Holding Ticker",
                    "Holding Name",
                    "Date",
                    "Holding Type",
                    "Percentage of Fund",
                    "Market Value",
                ],
                ["02079K305", "GOOGL", "Alphabet Inc Class A", "07/29/2026", "Equity", 60, 600],
                ["02079K107", "--", "Alphabet Inc Class C", "07/29/2026", "Equity", 40, 400],
            ]
        )
        qqqm_path.write_text(qqqm_text.getvalue(), encoding="utf-8")
        parsed_qqqm = parser.parse_source("QQQM", qqqm_path, "invesco-csv-v1")
        assert parsed_qqqm["source_as_of"] == "2026-07-29"
        assert [item["security_id"] for item in parsed_qqqm["holdings"]] == [
            "CUSIP:02079K305",
            "CUSIP:02079K107",
        ]
        missing_id_path = tmp_path / "QQQM-placeholder-only.csv"
        missing_id_path.write_text(
            qqqm_text.getvalue().replace("02079K305,GOOGL", ",--"),
            encoding="utf-8",
        )
        try:
            parser.parse_source("QQQM", missing_id_path, "invesco-csv-v1")
        except parser.SourceParseError:
            pass
        else:
            raise AssertionError("parser accepted a placeholder ticker without a stable ID")

        good, packet_path = validator.sample(Path(tmp))
        validator.validate(good, packet_path, allow_test=True)

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

        registry_path = packet_path.parent / good["issuer_registry_path"]
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

    print("Independent Look-through Bundle v1.3 adversarial tests passed.")


if __name__ == "__main__":
    main()
