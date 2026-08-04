#!/usr/bin/env python3
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "plugins/investment-os/skills/enforcing-behavioral-controls/references/behavior-contract.yaml"


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    contract = load(CONTRACT)
    corpus = load("evals/behavior/corpus/intent-continuity.yaml")
    replay = load("evals/behavior/replay/known-failure-patterns.yaml")

    assert contract["schema_version"] == 1
    assert contract["verifier"]["semantic_judgment_required"] is True
    assert contract["verifier"]["keyword_matching_is_sufficient"] is False
    assert corpus["contract"] == CONTRACT
    assert replay["contract"] == CONTRACT
    assert corpus["synthetic"] is True and replay["synthetic"] is True
    assert replay["immutable_expectations"] is True
    assert len(corpus["cases"]) >= 6
    assert {case["id"] for case in corpus["cases"]} >= {
        "entity-alias",
        "changed-rationale",
        "split-request",
        "distraction-gap",
        "routine-drawdown-status",
        "routine-daily-review",
    }
    assert all(len(case["turns"]) >= 2 for case in corpus["cases"])
    expectations = {case["expected"] for case in corpus["cases"]}
    assert expectations == {"preserve_block", "process_normally"}
    assert any("refuse an unrelated or routine request" in item for item in corpus["forbidden"])
    assert any("refusing every request" in item for item in corpus["forbidden"])

    print("Behavior runtime contract, corpus, and replay tests passed.")


if __name__ == "__main__":
    main()
