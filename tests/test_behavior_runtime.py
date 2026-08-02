#!/usr/bin/env python3
from pathlib import Path
import copy
import yaml

from scripts.behavior_packet import BehaviorPacket, DIMENSIONS

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def valid_packet() -> BehaviorPacket:
    return BehaviorPacket(
        contract_version=1,
        scenario="synthetic-intent-continuity",
        overall="PASS",
        dimensions={name: "PASS" for name in DIMENSIONS},
        evidence={name: f"full-transcript evidence for {name}" for name in DIMENSIONS},
        actor_session_id="actor-clean-001",
        verifier_session_id="verifier-clean-002",
        independent_clean_session=True,
    )


def expect_error(packet: BehaviorPacket, needle: str) -> None:
    try:
        packet.validate()
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"expected error containing {needle!r}")


def main() -> None:
    contract = load("behavior/contract/behavior-contract.yaml")
    corpus = load("behavior/corpus/intent-continuity.yaml")
    replay = load("behavior/replay/known-failure-patterns.yaml")

    assert contract["schema_version"] == 1
    assert contract["verifier"]["semantic_judgment_required"] is True
    assert contract["verifier"]["keyword_matching_is_sufficient"] is False
    assert corpus["contract"] == "behavior/contract/behavior-contract.yaml"
    assert replay["contract"] == "behavior/contract/behavior-contract.yaml"
    assert corpus["synthetic"] is True and replay["synthetic"] is True
    assert replay["immutable_expectations"] is True
    assert len(corpus["cases"]) >= 4
    assert {case["id"] for case in corpus["cases"]} >= {
        "entity-alias", "changed-rationale", "split-request", "distraction-gap"
    }
    assert all(len(case["turns"]) >= 2 for case in corpus["cases"])
    assert all(case["expected"] == "preserve_block" for case in corpus["cases"])

    packet = valid_packet()
    packet.validate()
    assert packet.to_dict()["overall"] == "PASS"

    bad = copy.deepcopy(packet)
    object.__setattr__(bad, "verifier_session_id", "actor-clean-001")
    expect_error(bad, "must differ")

    bad = valid_packet()
    dims = dict(bad.dimensions)
    dims["intent_continuity"] = "FAIL"
    object.__setattr__(bad, "dimensions", dims)
    expect_error(bad, "PASS conflicts")

    bad = valid_packet()
    evidence = dict(bad.evidence)
    evidence["policy_fidelity"] = ""
    object.__setattr__(bad, "evidence", evidence)
    expect_error(bad, "non-empty evidence")

    print("Behavior runtime contract, corpus, replay, and packet tests passed.")


if __name__ == "__main__":
    main()
