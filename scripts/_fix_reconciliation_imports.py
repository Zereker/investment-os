#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for rel in ("scripts/broker_runtime.py", "scripts/daily_brief.py", "scripts/monthly_execution.py"):
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    old = "from account_reconciliation import reconcile_nav\n"
    new = (
        "try:\n"
        "    from scripts.account_reconciliation import reconcile_nav\n"
        "except ModuleNotFoundError:  # direct script execution\n"
        "    from account_reconciliation import reconcile_nav\n"
    )
    if old not in text:
        raise SystemExit(f"expected import not found in {rel}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
