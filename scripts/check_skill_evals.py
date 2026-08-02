#!/usr/bin/env python3
"""Validate Investment OS behavior scenario definitions and eval integrity."""

from pathlib import Path
import re
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
SCENARIOS = ROOT / "evals" / "scenarios"
CONTRACT = ROOT / "behavior" / "contract" / "behavior-contract.yaml"

COMMON_FIELDS = ("name:", "skills:", "required:", "forbidden:", "reason:", "synthetic: true")
REQUIRED_SCENARIOS = {
    "manual-figures-are-not-authority",
    "no-inherited-agent-approval",
    "rewording-does-not-reset-intent",
    "research-cannot-enter-production",
    "missing-orders-fails-closed",
    "stale-drawdown-alert-tier",
    "incomplete-data-no-estimation",
}
FORBIDDEN_PRIVATE = re.compile(
    r"\b(?:U\d{5,}|DU\d+|account\s*id|alert\s*id)\b|\$\s*\d|\b\d[\d,]*(?:\.\d+)?\s*USD\b",
    re.I,
)


def skill_names() -> set[str]:
    return {path.parent.name for path in SKILLS.glob("*/SKILL.md")}


def parse_list(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []
    values: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith(" "):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            values.append(stripped[2:])
    return values


def main() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("schema_version") != 1:
        raise AssertionError("behavior contract schema version must be 1")
    verifier = contract.get("verifier", {})
    if verifier.get("semantic_judgment_required") is not True:
        raise AssertionError("behavior verifier must require semantic judgment")
    if verifier.get("keyword_matching_is_sufficient") is not False:
        raise AssertionError("keyword matching must not be sufficient")

    available = skill_names()
    found: set[str] = set()
    for path in sorted(SCENARIOS.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        for field in COMMON_FIELDS:
            if field not in text:
                raise AssertionError(f"{path}: missing {field}")
        has_prompt = re.search(r"^prompt:\s*\|", text, re.M) is not None
        has_turns = re.search(r"^turns:\s*$", text, re.M) is not None
        if has_prompt == has_turns:
            raise AssertionError(f"{path}: define exactly one top-level prompt or turns field")
        name = text.splitlines()[0].partition(":")[2].strip()
        if name in found:
            raise AssertionError(f"duplicate eval scenario name: {name}")
        found.add(name)
        if path.stem != name:
            raise AssertionError(f"{path}: filename must match scenario name {name!r}")
        if FORBIDDEN_PRIVATE.search(text):
            raise AssertionError(f"{path}: scenario may contain private runtime data")
        referenced = parse_list(text, "skills:")
        if not referenced:
            raise AssertionError(f"{path}: no skills referenced")
        missing = sorted(set(referenced) - available)
        if missing:
            raise AssertionError(f"{path}: unknown skills: {', '.join(missing)}")
        if not parse_list(text, "required:") or not parse_list(text, "forbidden:"):
            raise AssertionError(f"{path}: required and forbidden behavior lists must be non-empty")

    missing_scenarios = REQUIRED_SCENARIOS - found
    unexpected_scenarios = found - REQUIRED_SCENARIOS
    if missing_scenarios:
        raise AssertionError("missing required eval scenarios: " + ", ".join(sorted(missing_scenarios)))
    if unexpected_scenarios:
        raise AssertionError("unregistered eval scenarios: " + ", ".join(sorted(unexpected_scenarios)))

    rewording = (SCENARIOS / "rewording-does-not-reset-intent.yaml").read_text(encoding="utf-8")
    if "behavior_contract: behavior/contract/behavior-contract.yaml" not in rewording:
        raise AssertionError("rewording scenario must reference the canonical behavior contract")
    if rewording.count("  - role: user") < 4:
        raise AssertionError("rewording scenario must cover at least four adversarial user turns")
    for needle in ("entity aliases", "changed rationale", "unrelated intervening request", "split order request", "full transcript"):
        if needle not in rewording:
            raise AssertionError(f"rewording scenario missing adversarial control: {needle}")
    if "same purchase" in rewording.lower() or "stopped earlier" in rewording.lower():
        raise AssertionError("rewording scenario must not disclose that a later request repeats the first")

    corpus = yaml.safe_load((ROOT / "behavior/corpus/intent-continuity.yaml").read_text(encoding="utf-8"))
    replay = yaml.safe_load((ROOT / "behavior/replay/known-failure-patterns.yaml").read_text(encoding="utf-8"))
    if corpus.get("contract") != "behavior/contract/behavior-contract.yaml":
        raise AssertionError("behavior corpus must reference the canonical contract")
    if replay.get("contract") != "behavior/contract/behavior-contract.yaml" or replay.get("immutable_expectations") is not True:
        raise AssertionError("behavior replay must have canonical contract and immutable expectations")

    runner = (ROOT / "evals" / "run.py").read_text(encoding="utf-8")
    for needle in (
        "NOT VERIFIED: no verifier configured",
        "--actor-only",
        "validate_verifier_result",
        "separate_session",
        "verifier_session_id",
        "VERIFIED PASS",
        "VERIFIED FAIL",
    ):
        if needle not in runner:
            raise AssertionError(f"eval runner missing integrity control: {needle}")

    print("Skill behavior eval scenario and Behavior Runtime integrity checks passed.")


if __name__ == "__main__":
    main()
