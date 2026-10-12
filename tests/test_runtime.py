"""Synthetic-only regression tests for the installed skill helper."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/investment-os/scripts/check_runtime.py'
spec = importlib.util.spec_from_file_location('check_runtime', SCRIPT)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
NOW = dt.datetime(2026, 10, 1, 15, tzinfo=dt.timezone.utc)


def fixture():
    data = {
        'account_summary': {'currency': 'USD', 'net_liquidation': 100000},
        'balances': {'balances': [
            {'currency': 'BASE', 'cash_balance': 30000},
            {'currency': 'USD', 'cash_balance': 25000, 'settled_cash': 25000},
            {'currency': 'CNH', 'cash_balance': 35000}]},
        'positions': {'positions': [
            {'contract_description': t, 'contract_id': i, 'market_value': v,
             'position': 10, 'currency': 'USD'}
            for i, (t, v) in enumerate([('SPYM', 40000), ('QQQM', 25000), ('SOXX', 4000), ('LEGACY', 1000)])]},
        'open_orders': {'orders': []},
        'cash_transactions': {'external_contribution_usd': 2000},
        'market_inputs': {t: {'drawdown': .01, 'close_as_of': '2026-09-30',
                              'tiers_executed': []} for t in ('SPYM', 'QQQM')},
    }
    return {'task': 'monthly', 'capabilities': {
        k: {'status': 'available', 'source': 'IBKR', 'observed_at': NOW.isoformat(),
            'source_as_of': None, 'data': v} for k, v in data.items()},
        'schedule': {'source': 'NYSE', 'monthly_execution_date': '2026-10-01',
                     'calculation_already_run': False}}


class RuntimeTests(unittest.TestCase):
    def run_check(self, p):
        return helper.check(p, NOW)

    def test_valid_monthly_uses_only_usd_for_deployment(self):
        r = self.run_check(fixture())
        self.assertEqual(r['status'], 'PASS')
        d = r['deployment']
        self.assertEqual(d['C0'], 25000)
        self.assertEqual(d['D'], 2000)
        self.assertAlmostEqual(d['B'], 8000 / 3)
        self.assertEqual(d['gaps'], {'SPYM': 10000, 'QQQM': 5000, 'SOXX': 1000})
        self.assertFalse(r['execution_authorized'])

    def test_missing_contribution_blocks_amounts(self):
        p = fixture()
        p['capabilities']['cash_transactions'] = {'status': 'unavailable', 'data': None}
        r = self.run_check(p)
        self.assertEqual(r['status'], 'DATA INCOMPLETE')
        self.assertIsNone(r['deployment'])
        self.assertIn('weights', r)

    def test_explicit_zero_contribution_preserves_baseline(self):
        p = fixture()
        p['capabilities']['cash_transactions']['data']['external_contribution_usd'] = 0
        d = self.run_check(p)['deployment']
        self.assertAlmostEqual(d['B'], 10000 / 3)

    def test_account_review_does_not_require_funding_capability(self):
        p = fixture()
        p['task'] = 'account'
        del p['capabilities']['cash_transactions']
        del p['capabilities']['market_inputs']
        self.assertEqual(self.run_check(p)['status'], 'PASS')

    def test_nav_tolerance_and_legacy_are_included(self):
        p = fixture()
        p['capabilities']['account_summary']['data']['net_liquidation'] = 100400
        r = self.run_check(p)
        self.assertEqual(r['reconciliation']['status'], 'PASS')
        self.assertEqual(r['reconciliation']['component_total'], 100000)
        p['capabilities']['account_summary']['data']['net_liquidation'] = 101000
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_orders_stale_input_borrowing_duplicate_contract(self):
        cases = []
        p = fixture(); p['capabilities']['open_orders']['data']['orders'] = [{}]; cases.append(p)
        p = fixture(); p['capabilities']['balances']['observed_at'] = '2026-10-01T14:00:00Z'; cases.append(p)
        p = fixture(); p['capabilities']['balances']['data']['balances'][2]['cash_balance'] = -1; cases.append(p)
        p = fixture(); p['capabilities']['positions']['data']['positions'][1]['contract_id'] = 0; cases.append(p)
        for p in cases:
            with self.subTest(p=p):
                self.assertIsNone(self.run_check(p)['deployment'])

    def test_no_catchup_or_repeated_monthly_calculation(self):
        for key, value in [('monthly_execution_date', '2026-10-02'),
                           ('calculation_already_run', True),
                           ('calculation_already_run', None)]:
            p = fixture(); p['schedule'][key] = value
            self.assertIsNone(self.run_check(p)['deployment'])

    def test_independent_tiers_and_no_soxx_ladder(self):
        p = fixture()
        p['capabilities']['market_inputs']['data']['QQQM']['drawdown'] = .20
        p['capabilities']['market_inputs']['data']['QQQM']['tiers_executed'] = ['T1']
        d = self.run_check(p)['deployment']
        self.assertEqual(d['drawdown_allocation']['SPYM'], 0)
        self.assertEqual(d['drawdown_allocation']['SOXX'], 0)
        self.assertEqual(d['candidate_tiers']['QQQM'], ['T2', 'T3'])
        self.assertAlmostEqual(d['drawdown_allocation']['QQQM'], 3000)

    def test_zero_gap_does_not_consume_tiers(self):
        p = fixture()
        rows = p['capabilities']['positions']['data']['positions']
        rows[0]['market_value'] = 35000
        rows[1]['market_value'] = 30000
        p['capabilities']['market_inputs']['data']['QQQM']['drawdown'] = .25
        d = self.run_check(p)['deployment']
        self.assertEqual(d['candidate_tiers']['QQQM'], [])
        self.assertEqual(d['drawdown_allocation']['QQQM'], 0)

    def test_unknown_tiers_and_invalid_decimal_block_monthly(self):
        for dd, tiers in [(10, []), (.1, None), (.1, ['T5'])]:
            p = fixture(); m = p['capabilities']['market_inputs']['data']['SPYM']
            m['drawdown'], m['tiers_executed'] = dd, tiers
            self.assertIsNone(self.run_check(p)['deployment'])

    def test_settled_cash_limits_and_missing_settlement(self):
        p = fixture()
        p['capabilities']['balances']['data']['balances'][1]['settled_cash'] = 16000
        d = self.run_check(p)['deployment']
        self.assertEqual(d['C0'], 16000)
        self.assertEqual(d['B'], 0)
        p['capabilities']['balances']['data']['balances'][1]['settled_cash'] = 14000
        self.assertEqual(self.run_check(p)['deployment']['B'], 0)
        del p['capabilities']['balances']['data']['balances'][1]['settled_cash']
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_dca_precedes_baseline_and_requires_contribution(self):
        p = fixture()
        out = self.run_check(p)['deployment']
        self.assertEqual(out['D'], 2000)
        self.assertEqual(out['routine_allocation']['SPYM'], 2000)
        self.assertEqual(out['C'], 23000)
        self.assertAlmostEqual(out['B'], 8000 / 3)
        p['capabilities']['cash_transactions']['data']['external_contribution_usd'] = None
        self.assertIsNone(self.run_check(p)['deployment'])
        del p['capabilities']['cash_transactions']
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_cnh_settled_disclosure_is_not_conversion_authority(self):
        p = fixture()
        row = p['capabilities']['balances']['data']['balances'][2]
        row['settled_cash'] = 30000
        out = self.run_check(p)
        prep = out['funding_preparation']
        self.assertEqual(prep['status'], 'AWAIT_OWNER_REVIEW')
        self.assertEqual(prep['settled_balance_limit'], 30000)
        self.assertIsNone(prep['amount_to_convert'])
        self.assertIsNone(prep['expected_usd_proceeds'])
        self.assertFalse(prep['execution_authorized'])
        self.assertEqual(out['deployment'], self.run_check(fixture())['deployment'])

    def test_unsettled_cnh_waits_without_affecting_usd(self):
        p = fixture()
        p['capabilities']['balances']['data']['balances'][2]['settled_cash'] = 0
        out = self.run_check(p)
        self.assertEqual(out['status'], 'PASS')
        self.assertEqual(out['funding_preparation']['status'], 'WAIT')

    def test_missing_cnh_settlement_is_localized(self):
        out = self.run_check(fixture())
        self.assertEqual(out['funding_preparation']['status'], 'DATA INCOMPLETE')
        self.assertEqual(out['status'], 'PASS')

    def test_missing_or_duplicate_cnh_is_not_an_assumed_deposit(self):
        p = fixture()
        rows = p['capabilities']['balances']['data']['balances']
        rows.append(dict(rows[2], settled_cash=35000))
        self.assertEqual(self.run_check(p)['funding_preparation']['status'], 'DATA INCOMPLETE')
        del rows[2:]
        self.assertEqual(self.run_check(p)['funding_preparation']['status'], 'NOT_APPLICABLE')

    def test_cli_bad_input_fails_without_traceback_or_execution(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input='{"task":"monthly"}',
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, '')
        self.assertIsNone(json.loads(result.stdout)['deployment'])

    def test_policy_and_packaging_mirrors(self):
        text = (ROOT / 'skills/investment-os/references/00-constitution.md').read_text()
        for fragment in ('15%', '50%', '30%', '5%', '9.00pp', '6.00pp'):
            self.assertIn(fragment, text)
        self.assertEqual(helper.TARGETS, {'SPYM': .50, 'QQQM': .30, 'SOXX': .05})
        self.assertNotIn('mcpServers', json.loads((ROOT / '.codex-plugin/plugin.json').read_text()))
        self.assertFalse((ROOT / '.mcp.json').exists())
        self.assertFalse((ROOT / '.github/workflows/remote-mcp-smoke.yml').exists())
        self.assertTrue((ROOT / 'archive/mcp/cloudflare/server.ts').exists())


if __name__ == '__main__':
    unittest.main()
