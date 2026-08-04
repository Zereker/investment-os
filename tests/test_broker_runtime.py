#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from runtime_paths import SCRIPT_DIRS

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SCRIPT_DIRS["broker"] / "broker_runtime.py"
NOW = datetime(2026, 8, 2, 8, 0, tzinfo=timezone.utc)


def runtime() -> dict:
    capabilities = {
        "account_summary": "available",
        "balances": "available",
        "positions": "available",
        "open_orders": "available",
        "cash_transactions": "available",
        "market_inputs": "available",
        "alert_inventory": "available",
        "standing_automations": "available",
    }
    return {
        "identity": {"account_id": "SYNTHETIC", "account_type": "paper"},
        "snapshot": {
            "as_of": NOW.isoformat(),
            "source": "synthetic-adapter",
            "timezone": "UTC",
            "currency_basis": "USD",
        },
        "capabilities": capabilities,
        "observations": {
            name: {"source": "synthetic-adapter", "observed_at": NOW.isoformat()}
            for name in capabilities
        },
        "account_summary": {"net_liquidation": 100000},
        "balances": {"cash": 15000},
        "positions": [{"symbol": "SYNTHETIC", "market_value": 85000}],
        "open_orders": [],
        "cash_transactions": [],
        "market_inputs": {},
        "alert_inventory": [],
        "standing_automations": [],
        "reconciliation": {"status": "PASS", "issues": []},
    }


def check_case(payload: dict, required: list[str], expected_status: str, needle: str | None = None) -> None:
    from broker_runtime import validate_runtime

    result = validate_runtime(payload, required, now=NOW, max_age_seconds=300)
    assert result.status == expected_status, result
    if needle:
        assert any(needle in issue for issue in result.blocking_issues), result.blocking_issues


def main() -> None:
    base = runtime()
    check_case(base, ["positions", "balances", "open_orders"], "PASS")

    missing_positions = runtime()
    missing_positions["capabilities"]["positions"] = "unavailable"
    missing_positions["positions"] = None
    check_case(missing_positions, ["positions", "balances"], "DATA INCOMPLETE", "positions is unavailable")

    missing_orders = runtime()
    missing_orders["capabilities"]["open_orders"] = "unavailable"
    missing_orders["open_orders"] = None
    check_case(missing_orders, ["open_orders"], "DATA INCOMPLETE", "open_orders is unavailable")

    missing_cash_transactions = runtime()
    missing_cash_transactions["capabilities"]["cash_transactions"] = "unavailable"
    missing_cash_transactions["cash_transactions"] = None
    check_case(
        missing_cash_transactions,
        ["cash_transactions"],
        "DATA INCOMPLETE",
        "cash_transactions is unavailable",
    )

    stale = runtime()
    stale["snapshot"]["as_of"] = (NOW - timedelta(minutes=20)).isoformat()
    check_case(stale, ["positions"], "DATA INCOMPLETE", "snapshot is stale")

    conflicting = runtime()
    conflicting["capabilities"]["balances"] = "conflicting"
    conflicting["balances"] = None
    check_case(conflicting, ["balances"], "DATA INCOMPLETE", "balances is conflicting")

    missing_alert_inventory = runtime()
    missing_alert_inventory["capabilities"]["alert_inventory"] = "unavailable"
    missing_alert_inventory["alert_inventory"] = None
    check_case(
        missing_alert_inventory,
        ["alert_inventory"],
        "DATA INCOMPLETE",
        "alert_inventory is unavailable",
    )

    disguised_missing_alerts = runtime()
    disguised_missing_alerts["capabilities"]["alert_inventory"] = "unavailable"
    check_case(
        disguised_missing_alerts,
        ["alert_inventory"],
        "DATA INCOMPLETE",
        "must use null",
    )

    stale_endpoint = runtime()
    stale_endpoint["observations"]["positions"]["observed_at"] = (
        NOW - timedelta(minutes=20)
    ).isoformat()
    check_case(stale_endpoint, ["positions"], "DATA INCOMPLETE", "observation positions is stale")

    skewed = runtime()
    skewed["observations"]["positions"]["observed_at"] = (
        NOW - timedelta(minutes=6)
    ).isoformat()
    check_case(
        skewed,
        ["positions", "balances"],
        "DATA INCOMPLETE",
        "not a coherent snapshot",
    )

    cli = subprocess.run(
        [sys.executable, str(SCRIPT), "--require", "positions", "--max-age-seconds", "999999999"],
        input=json.dumps(base),
        text=True,
        capture_output=True,
        check=False,
    )
    assert cli.returncode == 0, cli.stderr
    output = json.loads(cli.stdout)
    assert output["runtime_status"] == "PASS", output

    print("Broker runtime tests passed.")


if __name__ == "__main__":
    main()
