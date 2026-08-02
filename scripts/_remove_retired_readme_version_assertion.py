#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().with_name("check_policy_consistency.py")
text = path.read_text(encoding="utf-8")
old = '    require("README.md", "# Investment OS v4.6")\n'
if text.count(old) != 1:
    raise SystemExit(f"expected exactly one retired README version assertion, found {text.count(old)}")
path.write_text(text.replace(old, "", 1), encoding="utf-8")
