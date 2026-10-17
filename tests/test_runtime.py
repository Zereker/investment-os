"""Synthetic-only regression tests for the installed skill helper."""
import datetime as dt
import importlib.util
import json
import re
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
        'contract_details': {'contracts': [
            {'contract_id': i, 'symbol': t, 'sec_type': 'STK', 'currency': 'USD'}
            for i, t in enumerate(('SPYM', 'QQQM', 'SOXX', 'LEGACY'))]},
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
        p['task'] = 'drawdown'
        p['capabilities']['market_inputs']['data']['QQQM']['drawdown'] = .20
        p['capabilities']['market_inputs']['data']['QQQM']['tiers_executed'] = ['T1']
        d = self.run_check(p)['deployment']
        self.assertEqual(d['drawdown_allocation']['SPYM'], 0)
        self.assertEqual(d['drawdown_allocation']['SOXX'], 0)
        self.assertEqual(d['candidate_tiers']['QQQM'], ['T2', 'T3'])
        self.assertAlmostEqual(d['drawdown_allocation']['QQQM'], 3000)

    def test_zero_gap_does_not_consume_tiers(self):
        p = fixture()
        p['task'] = 'drawdown'
        rows = p['capabilities']['positions']['data']['positions']
        rows[0]['market_value'] = 35000
        rows[1]['market_value'] = 30000
        p['capabilities']['market_inputs']['data']['QQQM']['drawdown'] = .25
        d = self.run_check(p)['deployment']
        self.assertEqual(d['candidate_tiers']['QQQM'], [])
        self.assertEqual(d['drawdown_allocation']['QQQM'], 0)

    def test_bad_market_state_is_local_to_its_ladder(self):
        for dd, tiers in [(10, []), (.1, None), (.1, ['T5'])]:
            p = fixture(); m = p['capabilities']['market_inputs']['data']['SPYM']
            m['drawdown'], m['tiers_executed'] = dd, tiers
            self.assertEqual(self.run_check(p)['status'], 'PASS')
            p['task'] = 'drawdown'
            r = self.run_check(p)
            self.assertEqual(r['paths']['SPYM']['status'], 'DATA INCOMPLETE')
            self.assertEqual(r['paths']['QQQM']['status'], 'PASS')
            self.assertIsNone(r['deployment']['drawdown_allocation']['SPYM'])

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

    def fx_fixture(self):
        p = fixture()
        del p['capabilities']['cash_transactions']
        p['funding_confirmation'] = dict(source_currency='CNH', confirmed_new_funding=True,
            allocation_period='2026-10', trade_ids=['synthetic-fx'])
        p['funding_ledger'] = dict(schema_version=1, ledger_id='synthetic-ledger',
            revision=0, history_scope='verified_full_history', entries=[])
        p['capabilities']['fx_funding'] = dict(status='available', source='IBKR',
            observed_at=NOW.isoformat(), data=dict(trades=[dict(trade_id='synthetic-fx',
                sec_type='CASH', symbol='USD', currency='CNH', side='BUY', size=2000,
                trade_time='2026-09-30T15:00:00Z')], usd_fees_total=2,
                fee_currency_verified=True, usd_settlement_verified=True))
        return p

    def test_confirmed_cnh_funding_keeps_contribution_first(self):
        out = self.run_check(self.fx_fixture())
        self.assertEqual(out['status'], 'PASS')
        self.assertEqual(out['deployment']['F'], 1998)
        self.assertEqual(out['deployment']['D'], 1998)
        self.assertFalse(out['execution_authorized'])

    def test_confirmed_fx_rejects_missing_source_reuse_and_fees(self):
        for key,value in [('confirmed_new_funding',False),('allocation_period','2026-09'),
                          ('trade_ids',['synthetic-fx','synthetic-fx'])]:
            p=self.fx_fixture();p['funding_confirmation'][key]=value
            self.assertIsNone(self.run_check(p)['deployment'])
        for key in ('fee_currency_verified','usd_settlement_verified'):
            p=self.fx_fixture();p['capabilities']['fx_funding']['data'][key]=False
            self.assertIsNone(self.run_check(p)['deployment'])
        p=self.fx_fixture();p['capabilities']['fx_funding']['data']['trades'][0]['currency']='EUR'
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_drawdown_works_midmonth_without_funding_or_schedule(self):
        p = fixture()
        p['task'] = 'drawdown'
        del p['schedule']
        del p['capabilities']['cash_transactions']
        p['capabilities']['market_inputs']['data']['QQQM']['drawdown'] = .10
        now = NOW + dt.timedelta(days=14)
        for item in p['capabilities'].values():
            item['observed_at'] = now.isoformat()
        for item in p['capabilities']['market_inputs']['data'].values():
            item['close_as_of'] = '2026-10-14'
        r = helper.check(p, now)
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['deployment']['candidate_tiers']['QQQM'], ['T1'])
        self.assertAlmostEqual(r['deployment']['drawdown_allocation']['QQQM'], 600)
        self.assertEqual(r['deployment']['drawdown_allocation']['SPYM'], 0)

    def test_missing_one_ladder_preserves_other_and_monthly(self):
        p = fixture()
        del p['capabilities']['market_inputs']['data']['SPYM']
        p['capabilities']['market_inputs']['data']['QQQM']['drawdown'] = .1
        self.assertEqual(self.run_check(p)['status'], 'PASS')
        p['task'] = 'drawdown'
        r = self.run_check(p)
        self.assertEqual(r['status'], 'DATA INCOMPLETE')
        self.assertAlmostEqual(r['deployment']['drawdown_allocation']['QQQM'], 600)
        self.assertIsNone(r['deployment']['drawdown_allocation']['SPYM'])
        del p['capabilities']['market_inputs']
        self.assertIsNone(self.run_check(p)['deployment'])
        p['task'] = 'monthly'
        self.assertEqual(self.run_check(p)['status'], 'PASS')

    def test_contract_identity_survives_description_and_blocks_unknown_mapping(self):
        p = fixture()
        p['capabilities']['positions']['data']['positions'][0]['contract_description'] = 'Human readable fund name'
        self.assertEqual(self.run_check(p)['deployment']['gaps']['SPYM'], 10000)
        for key, value in [('sec_type', 'OPT'), ('currency', 'CNH')]:
            p = fixture()
            p['capabilities']['contract_details']['data']['contracts'][0][key] = value
            self.assertIsNone(self.run_check(p)['deployment'])
        p = fixture()
        p['capabilities']['contract_details']['data']['contracts'].pop(0)
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_funding_ledger_required_and_reserved_or_used_fills_rejected(self):
        p = self.fx_fixture()
        del p['funding_ledger']
        self.assertIsNone(self.run_check(p)['deployment'])
        p = self.fx_fixture()
        p['funding_ledger']['history_scope'] = 'unknown'
        self.assertIsNone(self.run_check(p)['deployment'])
        for state in ('reserved', 'partial', 'consumed'):
            p = self.fx_fixture()
            p['funding_ledger']['entries'] = [dict(reservation_id='synthetic-r',
                allocation_period='2026-09', trade_ids=['synthetic-fx'], status=state,
                dca_usd=500, broker_fill_ids=['synthetic-buy'])]
            self.assertIsNone(self.run_check(p)['deployment'])

    def test_private_ledger_reservation_partial_receipt_and_revision(self):
        p = self.fx_fixture()
        request = dict(task='funding_ledger', funding_ledger=p['funding_ledger'],
            expected_revision=0, change=dict(action='reserve', reservation_id='synthetic-r',
                allocation_period='2026-10', trade_ids=['synthetic-fx']))
        r = self.run_check(request)
        self.assertTrue(r['persistence_required'])
        self.assertFalse(r['runtime_data_persisted'])
        self.assertEqual(p['funding_ledger']['entries'], [])
        request['funding_ledger'] = r['funding_ledger']
        with self.assertRaisesRegex(ValueError, 'revision'):
            self.run_check(request)
        request['expected_revision'] = 1
        request['change'] = dict(action='settle', reservation_id='synthetic-r',
            receipt=dict(status='partial', dca_usd=500, broker_fill_ids=['synthetic-buy'],
                broker_readback_verified=True, broker_orders_clear=True))
        r = self.run_check(request)
        p['funding_ledger'] = r['funding_ledger']
        self.assertEqual(p['funding_ledger']['entries'][0]['dca_usd'], 500)
        self.assertIsNone(self.run_check(p)['deployment'])
        request['funding_ledger'] = r['funding_ledger']
        request['expected_revision'] = 2
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            self.run_check(request)

    def test_release_requires_verified_no_fill(self):
        ledger = self.fx_fixture()['funding_ledger']
        ledger['entries'] = [dict(reservation_id='synthetic-r', allocation_period='2026-10',
            trade_ids=['synthetic-fx'], status='reserved')]
        receipt = dict(status='released', dca_usd=0, broker_fill_ids=[],
            broker_readback_verified=False, broker_orders_clear=True)
        p = dict(task='funding_ledger', funding_ledger=ledger, expected_revision=0,
            change=dict(action='settle', reservation_id='synthetic-r', receipt=receipt))
        with self.assertRaisesRegex(ValueError, 'verified'):
            self.run_check(p)
        receipt['broker_readback_verified'] = True
        out = self.run_check(p)
        fx = self.fx_fixture()
        fx['funding_ledger'] = out['funding_ledger']
        self.assertEqual(self.run_check(fx)['status'], 'PASS')

    def test_drawdown_shared_failure_and_cash_budget(self):
        p = fixture()
        p['task'] = 'drawdown'
        for item in p['capabilities']['market_inputs']['data'].values():
            item['drawdown'] = .25
        p['capabilities']['balances']['data']['balances'][1]['settled_cash'] = 1000
        d = self.run_check(p)['deployment']
        self.assertEqual(d['final_cash'], 0)
        self.assertEqual(sum(d['drawdown_allocation'].values()), 1000)
        self.assertEqual(d['drawdown_allocation']['SOXX'], 0)
        p['capabilities']['open_orders']['data']['orders'] = [{}]
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_stale_and_null_market_do_not_become_zero(self):
        p = fixture()
        p['task'] = 'drawdown'
        p['capabilities']['market_inputs']['data']['SPYM'] = None
        r = self.run_check(p)
        self.assertIsNone(r['deployment']['drawdown_allocation']['SPYM'])
        self.assertEqual(r['paths']['QQQM']['status'], 'PASS')
        p['capabilities']['market_inputs']['observed_at'] = '2026-10-01T14:00:00Z'
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_unknown_contract_does_not_report_false_weights(self):
        p = fixture()
        p['capabilities']['contract_details']['data']['contracts'] = []
        r = self.run_check(p)
        self.assertIsNone(r['deployment'])
        self.assertNotIn('weights', r)
        p = fixture()
        rows = p['capabilities']['contract_details']['data']['contracts']
        rows.append(dict(rows[0]))
        self.assertIsNone(self.run_check(p)['deployment'])

    def test_ledger_rejects_overlapping_reservations_and_unfinished_orders(self):
        ledger = self.fx_fixture()['funding_ledger']
        ledger['entries'] = [dict(reservation_id='synthetic-r', allocation_period='2026-10',
            trade_ids=['synthetic-fx'], status='reserved')]
        p = dict(task='funding_ledger', funding_ledger=ledger, expected_revision=0,
            change=dict(action='reserve', reservation_id='synthetic-r2',
                allocation_period='2026-10', trade_ids=['synthetic-fx']))
        with self.assertRaisesRegex(ValueError, 'duplicate active'):
            self.run_check(p)
        p['change'] = dict(action='settle', reservation_id='synthetic-r',
            receipt=dict(status='released', dca_usd=0, broker_fill_ids=[],
                broker_readback_verified=True, broker_orders_clear=False))
        with self.assertRaisesRegex(ValueError, 'verified'):
            self.run_check(p)

    def test_dca_does_not_force_existing_low_cash_to_fifteen_percent(self):
        p = fixture()
        p['capabilities']['balances']['data']['balances'][1]['settled_cash'] = 14000
        d = self.run_check(p)['deployment']
        self.assertEqual(d['D'], 2000)
        self.assertEqual(d['B'], 0)
        self.assertEqual(d['final_cash'], 12000)

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
        table = dict((ticker, int(weight) / 100) for ticker, weight in
                     re.findall(r'\| (SPYM|QQQM|SOXX) \| (\d+)% \|', text))
        self.assertEqual(helper.TARGETS, table)
        version = (ROOT / '.plugin-version').read_text().strip()
        for path in ('.codex-plugin/plugin.json', '.claude-plugin/plugin.json'):
            self.assertEqual(json.loads((ROOT / path).read_text())['version'], version)
        self.assertEqual(json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())['plugins'][0]['version'], version)
        self.assertNotIn('mcpServers', json.loads((ROOT / '.codex-plugin/plugin.json').read_text()))
        self.assertFalse((ROOT / '.mcp.json').exists())
        self.assertFalse((ROOT / '.github/workflows/remote-mcp-smoke.yml').exists())
        self.assertTrue((ROOT / 'archive/mcp/cloudflare/server.ts').exists())


if __name__ == '__main__':
    unittest.main()
