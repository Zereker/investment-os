"""Synthetic regression coverage for bounded, read-only Daily validation."""
import copy
import datetime as dt
import json
import subprocess
import sys
import unittest

from test_runtime import fixture, helper, NOW, SCRIPT


def daily_fixture():
    payload = fixture()
    payload['task'] = 'daily'
    del payload['capabilities']['cash_transactions']
    del payload['capabilities']['market_inputs']
    del payload['schedule']
    return payload


def pending_order():
    return dict(order_id=7, side='BUY', order_status='NEW', order_type='LIMIT',
                limit_price='25.00', total_shares_qty='12', cum_shares_qty='0',
                remaining_shares_qty='12')


class DailyTests(unittest.TestCase):
    def test_known_working_orders_are_complete_daily_data_not_authority(self):
        payload = daily_fixture()
        payload['capabilities']['open_orders']['data']['orders'] = [pending_order()]
        before = copy.deepcopy(payload)
        result = helper.check(payload, NOW)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['open_orders_status'], 'pending')
        self.assertTrue(result['has_open_orders'])
        self.assertTrue(result['order_constraints'])
        self.assertTrue(result['read_only'])
        self.assertTrue(result['execution_check_required'])
        self.assertFalse(result['execution_authorized'])
        self.assertIsNone(result['deployment'])
        self.assertIn('weights', result)
        self.assertEqual(payload, before)

    def test_known_orders_still_close_every_existing_deployment_preflight(self):
        for task in ('account', 'monthly', 'drawdown'):
            with self.subTest(task=task):
                payload = fixture()
                payload['task'] = task
                payload['capabilities']['open_orders']['data']['orders'] = [pending_order()]
                result = helper.check(payload, NOW)
                self.assertEqual(result['status'], 'DATA INCOMPLETE')
                self.assertEqual(result['open_orders_status'], 'pending')
                self.assertIsNone(result['deployment'])
                self.assertFalse(result['execution_authorized'])

    def test_empty_orders_and_no_funding_or_market_inputs_complete_daily(self):
        result = helper.check(daily_fixture(), NOW)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['open_orders_status'], 'clear')
        self.assertFalse(result['has_open_orders'])
        self.assertEqual(result['order_constraints'], [])
        self.assertIsNone(result['deployment'])

    def test_partial_fill_is_pending_but_completed_order_is_not_a_working_order(self):
        order = pending_order()
        order.update(order_status='PARTIALLY_FILLED', cum_shares_qty='2', remaining_shares_qty='10')
        self.assertEqual(helper.working_order_status([order]), 'pending')
        order.update(order_status='FILLED', cum_shares_qty='12', remaining_shares_qty='0')
        self.assertEqual(helper.working_order_status([order]), 'unknown')

    def test_unknown_or_malformed_orders_never_become_clear_daily_data(self):
        bad = [None, {}, [None], [{}], [pending_order(), pending_order()]]
        for key, value in (('side', 'OTHER'), ('order_status', 'UNRECOGNIZED'), ('order_status', []),
                           ('remaining_shares_qty', 'NaN'), ('cum_shares_qty', True),
                           ('total_shares_qty', '13'), ('limit_price', '-1'),
                           ('order_id', True), ('order_type', 'UNRECOGNIZED')):
            order = pending_order()
            order[key] = value
            bad.append([order])
        for orders in bad:
            with self.subTest(orders=orders):
                payload = daily_fixture()
                payload['capabilities']['open_orders']['data']['orders'] = orders
                result = helper.check(payload, NOW)
                self.assertEqual(result['status'], 'DATA INCOMPLETE')
                self.assertEqual(result['open_orders_status'], 'unknown')
                self.assertIsNone(result['has_open_orders'])
                self.assertIsNone(result['deployment'])

    def test_unavailable_orders_are_not_an_empty_list(self):
        payload = daily_fixture()
        payload['capabilities']['open_orders'] = dict(status='unavailable', data=None)
        result = helper.check(payload, NOW)
        self.assertEqual(result['status'], 'DATA INCOMPLETE')
        self.assertEqual(result['open_orders_status'], 'unknown')
        self.assertIsNone(result['has_open_orders'])

    def test_reconciliation_failure_preserves_raw_facts_without_weights(self):
        payload = daily_fixture()
        payload['capabilities']['account_summary']['data']['net_liquidation'] = 101000
        result = helper.check(payload, NOW)
        self.assertEqual(result['status'], 'DATA INCOMPLETE')
        self.assertEqual(result['reconciliation']['status'], 'DATA INCOMPLETE')
        self.assertEqual(result['reconciliation']['tolerance'], .005)
        self.assertEqual(result['reconciliation']['component_total'], 100000)
        self.assertIn('balances_by_currency', result)
        self.assertNotIn('weights', result)
        self.assertNotIn('legacy', result)
        self.assertNotIn('usd_cash_weight', result)
        self.assertIsNone(result['deployment'])

    def test_daily_keeps_freshness_source_and_borrowing_checks(self):
        for problem in ('stale', 'manual', 'borrowing'):
            payload = daily_fixture()
            balances = payload['capabilities']['balances']
            if problem == 'stale':
                balances['observed_at'] = (NOW - dt.timedelta(seconds=301)).isoformat()
            elif problem == 'manual':
                balances['source'] = 'manual'
            else:
                balances['data']['balances'][2]['cash_balance'] = -1
            result = helper.check(payload, NOW)
            self.assertEqual(result['status'], 'DATA INCOMPLETE')
            self.assertFalse(result['execution_authorized'])
            self.assertIsNone(result['deployment'])

    def test_snapshot_metadata_preserves_provider_time_and_actual_validation_time(self):
        payload = daily_fixture()
        provider_time = '2026-10-01T14:59:30+00:00'
        payload['capabilities']['positions']['source_as_of'] = provider_time
        payload['captured_at'] = '2099-01-01T00:00:00Z'
        result = helper.check(payload, NOW)
        self.assertEqual(result['validated_at'], NOW.isoformat())
        self.assertEqual(result['observed_at'], NOW.isoformat())
        self.assertEqual(result['source_as_of']['positions'], provider_time)
        self.assertIsNone(result['source_as_of']['balances'])

    def test_render_delay_does_not_mutate_snapshot_or_supply_fresh_preflight(self):
        payload = daily_fixture()
        snapshot = helper.check(payload, NOW)
        saved = copy.deepcopy(snapshot)
        later = NOW + dt.timedelta(minutes=10)
        payload['task'] = 'account'
        payload['validated_at'] = later.isoformat()
        result = helper.check(payload, later)
        self.assertEqual(snapshot, saved)
        self.assertEqual(result['status'], 'DATA INCOMPLETE')
        self.assertTrue(any('stale' in x for x in result['blocking_issues']))
        self.assertIsNone(result['deployment'])
        self.assertFalse(result['execution_authorized'])

    def test_installed_cli_accepts_read_only_daily_with_pending_orders(self):
        payload = daily_fixture()
        observed = dt.datetime.now(dt.timezone.utc).isoformat()
        for capability in payload['capabilities'].values():
            capability['observed_at'] = observed
        payload['capabilities']['open_orders']['data']['orders'] = [pending_order()]
        proc = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(payload),
                              text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result['status'], 'PASS')
        self.assertIsNone(result['deployment'])
        self.assertFalse(result['execution_authorized'])


if __name__ == '__main__':
    unittest.main()
