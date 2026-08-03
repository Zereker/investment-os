#!/usr/bin/env python3
"""Prevent entry documents from drifting behind the runtime architecture.

Rules-first scope (v0.5.0): structural checks only — the consolidated rule
files exist, titles carry no policy version, and the honest-verification
declaration survives everywhere it is required. Prose-preservation needles
were retired with the 29->9 rule consolidation.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = "plugins/investment-os/skills/using-investment-os/references"

REQUIRED_REFERENCES = (
    "00-constitution.md",
    "01-operating-manual.md",
    "02-data-contract.md",
    "03-journal.md",
    "product-contract.md",
    "agent-execution-contract.md",
    "claude-code-entry.md",
    "claude-code-tools.md",
    "codex-tools.md",
)

# run-all.sh phrases it as "remains NOT YET VERIFIED", so match the two parts
NOT_YET_VERIFIED = ("Real Harness behavior", "NOT YET VERIFIED")
NOT_YET_VERIFIED_PATHS = (
    "README.md",
    f"{REFERENCES}/product-contract.md",
    f"{REFERENCES}/claude-code-entry.md",
    "tests/run-all.sh",
    # docs/SKILL-DISTRIBUTION.md carries its own form of the declaration,
    # already enforced by check_skill_distribution.py
)


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def versionless_title(path: str) -> None:
    first = text(path).splitlines()[0]
    if re.search(r"\bv\d+(?:\.\d+)+\b", first, re.I):
        raise AssertionError(f"{path}: policy version must not appear in title: {first}")


def main() -> None:
    missing = [name for name in REQUIRED_REFERENCES
               if not (ROOT / REFERENCES / name).is_file()]
    if missing:
        raise AssertionError("missing consolidated rule files: " + ", ".join(missing))

    for path in ("README.md", f"{REFERENCES}/product-contract.md",
                 f"{REFERENCES}/00-constitution.md", f"{REFERENCES}/01-operating-manual.md",
                 f"{REFERENCES}/02-data-contract.md"):
        versionless_title(path)

    for path in NOT_YET_VERIFIED_PATHS:
        value = text(path)
        if any(part not in value for part in NOT_YET_VERIFIED):
            raise AssertionError(f"{path}: must carry the declaration {' … '.join(NOT_YET_VERIFIED)!r}")

    # a claim of behavior coverage from green CI is the one dishonest sentence
    # this checker still patrols for
    for path in NOT_YET_VERIFIED_PATHS:
        if "Real Harness behavior: VERIFIED" in text(path):
            raise AssertionError(f"{path}: claims verified harness behavior")

    print("Documentation governance checks passed.")


if __name__ == "__main__":
    main()
