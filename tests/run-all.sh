#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
python3 -c 'import yaml' 2>/dev/null || {
  echo "PyYAML is required for eval integrity tests: python3 -m pip install pyyaml" >&2
  exit 1
}
python3 tests/test_skill_system.py
python3 tests/test_eval_integrity.py
python3 tests/test_monthly_contribution_cli.py
python3 scripts/check_skill_distribution.py
python3 scripts/check_skill_evals.py
python3 scripts/check_product_contract.py
python3 scripts/check_release_governance.py
python3 scripts/check_policy_consistency.py
python3 scripts/daily_brief.py --self-test
python3 scripts/alert_pointer_check.py --self-test

echo "All non-LLM and eval-harness integrity tests passed. Real Harness behavior remains NOT YET VERIFIED."
