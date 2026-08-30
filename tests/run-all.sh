#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

python3 tests/test_plugin_installation.py
python3 tests/test_broker_runtime.py
python3 tests/test_execution_runtime.py
python3 tests/test_monthly_contribution_cli.py
python3 tests/test_monthly_dd_cli.py
python3 tests/test_reconciliation_gates.py
python3 scripts/check_policy_consistency.py
python3 skills/investment-os/scripts/monthly_execution.py --self-test

echo "All tests passed."
