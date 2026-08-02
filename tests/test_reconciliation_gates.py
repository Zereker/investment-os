#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from runtime_paths import SCRIPT_DIRS
from broker_runtime import validate_runtime

ROOT = Path(__file__).resolve().parents[1]
MONTHLY = SCRIPT_DIRS["monthly"] / "monthly_execution.py"


def monthly(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(MONTHLY), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    impossible = monthly(
        "--nav", "100000", "--cash", "95000", "--spym", "200000",
        "--qqqm", "0", "--soxx", "0", "--dd", "0.26",
        "--tiers-executed", "none", "--contribution", "1000",
        "--lookthrough-current", "--open-orders-status", "clear",
        "--today", "2026-08-02",
    )
    assert impossible.returncode != 0
    assert "does not reconcile to NAV" in impossible.stderr
    assert "BUY CANDIDATE" not in impossible.stdout

    physically_valid_but_orders_unknown = monthly(
        "--nav", "100000", "--cash", "20000", "--spym", "46000",
        "--qqqm", "28000", "--soxx", "6000", "--dd", "0",
        "--tiers-executed", "none", "--contribution", "0",
        "--today", "2026-08-02",
    )
    assert physically_valid_but_orders_unknown.returncode != 0
    assert "open orders status is unknown" in physically_valid_but_orders_unknown.stderr

    now = datetime(2026, 8, 2, 10, 0, tzinfo=timezone.utc)
    self_declared_pass = {
        "identity": {"account_id": "SYNTHETIC"},
        "snapshot": {
            "as_of": now.isoformat(), "source": "synthetic",
            "timezone": "UTC", "currency_basis": "USD",
        },
        "capabilities": {
            "account_summary": "available", "balances": "available",
            "positions": "available", "open_orders": "available",
            "cash_transactions": "available", "market_inputs": "available",
        },
        "account_summary": {"net_liquidation": 100000},
        "balances": {"cash": 95000},
        "positions": [{"symbol": "SYNTHETIC", "market_value": 200000}],
        "open_orders": [], "cash_transactions": [], "market_inputs": {},
        "reconciliation": {"status": "PASS", "issues": []},
    }
    result = validate_runtime(
        self_declared_pass,
        ["positions", "balances"],
        now=now,
        max_age_seconds=300,
    )
    assert result.status == "DATA INCOMPLETE"
    assert any("does not reconcile to NAV" in issue for issue in result.blocking_issues)

    print("Shared reconciliation and order-gate tests passed.")


if __name__ == "__main__":
    main()
