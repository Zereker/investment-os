#!/usr/bin/env python3
"""Reject modification or deletion of previously committed evidence bundle files."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

ROOT = "08-Data/SNAPSHOTS/lookthrough/"
ZERO_SHA = re.compile(r"^0+$")


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
    if violations:
        print("Historical look-through evidence is append-only; rejected changes:", file=sys.stderr)
        for line in violations:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("Look-through evidence history is append-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
