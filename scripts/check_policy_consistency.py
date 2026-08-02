#!/usr/bin/env python3
"""Run the complete legacy policy suite without retired release-mirror assertions."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "check_policy_consistency_legacy.py"

source = LEGACY.read_text(encoding="utf-8")
lines = source.splitlines()
filtered: list[str] = []
for line in lines:
    if "07-Releases/" not in line:
        filtered.append(line)
        continue
    stripped = line.strip()
    if stripped.startswith("require(") and stripped.endswith(")"):
        continue
    cleaned = re.sub(r'\s*"07-Releases/[^\"]+",?', "", line)
    if cleaned.strip() not in {"", "(", "):"):
        filtered.append(cleaned)

namespace = {"__name__": "__main__", "__file__": str(LEGACY)}
exec(compile("\n".join(filtered) + "\n", str(LEGACY), "exec"), namespace)
