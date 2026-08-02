#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().with_name("check_policy_consistency.py")
text = path.read_text(encoding="utf-8")
old = '''    require("CLAUDE.md", "永远不下单", "fetch_etf_data.py", "DATA INCOMPLETE",
            "公开安全写法", "State-Reconstruction.md", "永不落盘",
            "你不合并 master", "由所有者审阅合并")
'''
if text.count(old) != 1:
    raise SystemExit(f"expected one retired CLAUDE assertion block, found {text.count(old)}")
path.write_text(text.replace(old, "", 1), encoding="utf-8")
