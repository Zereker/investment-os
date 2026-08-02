#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().with_name("check_policy_consistency.py")
text = path.read_text(encoding="utf-8")
retired = (
    '    require("README.md", "# Investment OS v4.6")\n',
    '    require("PRODUCTION.md", "# Investment OS v4.6 — Production Contract")\n',
)
removed = 0
for old in retired:
    count = text.count(old)
    if count > 1:
        raise SystemExit(f"retired assertion appears more than once: {old!r}")
    if count == 1:
        text = text.replace(old, "", 1)
        removed += 1
if removed == 0:
    raise SystemExit("no retired policy-version assertion remained to remove")
path.write_text(text, encoding="utf-8")
