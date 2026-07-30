#!/usr/bin/env python3
"""Enforce immutable bundles and append-only reviewed look-through authorities."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = "08-Data/SNAPSHOTS/lookthrough/"
AUTHORITIES = {
    "08-Data/REGISTRIES/LOOKTHROUGH_ISSUER_AUTHORITY.json": (
        "issuers",
        "securities",
    ),
    "08-Data/REGISTRIES/LOOKTHROUGH_CLASSIFICATION_AUTHORITY.json": ("records",),
}
ZERO_SHA = re.compile(r"^0+$")


def authority_at(revision: str, path: str) -> dict | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        return None
    return json.loads(result.stdout)


def check_authorities(base_sha: str) -> list[str]:
    violations = []
    for path, arrays in AUTHORITIES.items():
        previous = authority_at(base_sha, path)
        if previous is None:
            continue
        current = json.loads(Path(path).read_text(encoding="utf-8"))
        metadata = set(previous) - set(arrays)
        if set(current) != set(previous) or any(
            current.get(key) != previous.get(key) for key in metadata
        ):
            violations.append(f"{path}: authority metadata changed")
            continue
        for key in arrays:
            old_records = previous.get(key)
            new_records = current.get(key)
            if (
                not isinstance(old_records, list)
                or not isinstance(new_records, list)
                or len(new_records) < len(old_records)
                or new_records[: len(old_records)] != old_records
            ):
                violations.append(f"{path}: {key} is not append-only")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_sha")
    args = parser.parse_args()
    if ZERO_SHA.fullmatch(args.base_sha):
        print("No prior commit exists; immutability comparison skipped.")
        return 0
    result = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", args.base_sha, "HEAD", "--", ROOT],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        return result.returncode
    violations = []
    for line in result.stdout.splitlines():
        status, *_ = line.split("\t")
        if status != "A":
            violations.append(line)
    violations.extend(check_authorities(args.base_sha))
    if violations:
        print("Historical look-through evidence is append-only; rejected changes:", file=sys.stderr)
        for line in violations:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("Look-through evidence history is append-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
