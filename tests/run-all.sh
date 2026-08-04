#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

python3 -c 'import yaml' 2>/dev/null || {
  echo "PyYAML is required for eval integrity tests: python3 -m pip install pyyaml" >&2
  exit 1
}
python3 tests/test_plugin_installation.py
python3 tests/test_broker_runtime.py
python3 tests/test_execution_runtime.py
python3 tests/test_eval_integrity.py
python3 tests/test_eval_adapters.py
python3 tests/test_eval_sweep.py
python3 tests/test_monthly_contribution_cli.py
python3 tests/test_monthly_dd_cli.py
python3 tests/test_reconciliation_gates.py
python3 scripts/check_policy_consistency.py
python3 skills/investment-os/scripts/monthly_execution.py --self-test
python3 skills/investment-os/scripts/alert_pointer_check.py --self-test

echo "All non-LLM and eval-harness integrity tests passed. Real Harness behavior remains NOT YET VERIFIED."
