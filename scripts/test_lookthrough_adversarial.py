#!/usr/bin/env python3
"""Independent adversarial regression tests for Look-through Bundle v1.2."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

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
        mapping["records"][0]["issuer_group_id"] += " "
        alias_packet = copy.deepcopy(good)
        alias_packet["mapping_sha256"] = rewrite_json(mapping_path, mapping)
        reject("issuer split with trailing whitespace", alias_packet, packet_path)
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

    print("Independent Look-through Bundle v1.2 adversarial tests passed.")


if __name__ == "__main__":
    main()
