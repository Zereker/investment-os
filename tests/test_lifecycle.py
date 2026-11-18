"""Synthetic coverage for monthly plans and individual drawdown tiers."""
import copy
import datetime as dt
import unittest

from test_runtime import fixture, helper, NOW


def legacy_ledger():
    return dict(schema_version=1, ledger_id='synthetic-ledger', revision=0,
                history_scope='verified_full_history', entries=[])


def transition(ledger, action, **change):
    return helper.check(dict(task='funding_ledger', funding_ledger=ledger,
                             expected_revision=ledger['revision'], change=dict(action=action, **change)), NOW)


def upgrade(ledger, months=()):
    return transition(ledger, 'upgrade_monthly_history', monthly_history_verified=True,
                      historical_months=list(months))['funding_ledger']


def reserve(ledger, review, reservation_id='synthetic-plan'):
    return transition(ledger, 'reserve_monthly', reservation_id=reservation_id,
                      monthly_review=review)['funding_ledger']


def fx_review(trade_id):
    payload = fixture()
    payload['funding_confirmation'] = dict(source_currency='CNH', confirmed_new_funding=True,
                                            allocation_period='2026-10', trade_ids=[trade_id])
    payload['capabilities']['fx_funding'] = dict(status='available', source='IBKR',
        observed_at=NOW.isoformat(), data=dict(trades=[dict(trade_id=trade_id, sec_type='CASH',
            symbol='USD', currency='CNH', side='BUY', size=2000, trade_time='2026-09-30T15:00:00Z')],
            usd_fees_total=2, fee_currency_verified=True, usd_settlement_verified=True))
    return payload


class MonthlyPlanTests(unittest.TestCase):
    def test_upgrade_preserves_legacy_entries_and_blocks_verified_historical_month(self):
        ledger = legacy_ledger()
        ledger['entries'] = [dict(reservation_id='synthetic-old', allocation_period='2026-09',
                                  trade_ids=['synthetic-old-fx'], status='reserved')]
        before = copy.deepcopy(ledger)
        with self.assertRaisesRegex(ValueError, 'verified monthly history'):
            transition(ledger, 'upgrade_monthly_history', historical_months=[])
        migrated = upgrade(ledger, ['2026-10'])
        self.assertEqual(ledger, before)
        self.assertEqual(migrated['entries'], before['entries'])
        self.assertEqual(migrated['ledger_id'], before['ledger_id'])
        self.assertEqual((migrated['schema_version'], migrated['revision']), (2, 1))
        result = helper.check(dict(fixture(), funding_ledger=migrated), NOW)
        self.assertFalse(result['monthly_plan_reservable'])
        self.assertIsNone(result['deployment'])

    def test_different_fx_fills_and_cash_path_share_one_month(self):
        ledger = reserve(upgrade(legacy_ledger()), fx_review('synthetic-fx-a'))
        plan = ledger['entries'][0]
        self.assertEqual(plan['planned_dca_usd'], 1998)
        self.assertEqual(plan['trade_ids'], ['synthetic-fx-a'])
        for review in (fx_review('synthetic-fx-b'), fixture()):
            with self.subTest(mode='funding_confirmation' in review):
                result = helper.check(dict(review, funding_ledger=ledger), NOW)
                self.assertIsNone(result['deployment'])
                with self.assertRaisesRegex(ValueError, 'plan already exists'):
                    reserve(ledger, review, 'synthetic-other-plan')

    def test_legacy_reserve_rejects_different_fills_in_same_active_month(self):
        ledger = transition(legacy_ledger(), 'reserve', reservation_id='synthetic-old',
                            allocation_period='2026-10', trade_ids=['synthetic-fx-a'])['funding_ledger']
        with self.assertRaisesRegex(ValueError, 'plan already exists'):
            transition(ledger, 'reserve', reservation_id='synthetic-new',
                       allocation_period='2026-10', trade_ids=['synthetic-fx-b'])

    def test_monthly_reservation_requires_fresh_review_and_revision(self):
        self.assertFalse(helper.check(fixture(), NOW)['monthly_plan_reservable'])
        with self.assertRaisesRegex(ValueError, 'schema 2'):
            reserve(legacy_ledger(), fixture())
        ledger = upgrade(legacy_ledger())
        review = fixture()
        review['capabilities']['open_orders']['observed_at'] = (NOW - dt.timedelta(minutes=6)).isoformat()
        with self.assertRaisesRegex(ValueError, 'stale observed_at'):
            reserve(ledger, review)
        with self.assertRaisesRegex(ValueError, 'revision mismatch'):
            helper.check(dict(task='funding_ledger', funding_ledger=ledger, expected_revision=0,
                              change=dict(action='reserve_monthly', monthly_review=fixture())), NOW)

    def test_baseline_only_partial_and_no_fill_paths_close_month(self):
        review = fixture()
        review['capabilities']['cash_transactions']['data']['external_contribution_usd'] = 0
        ledger = reserve(upgrade(legacy_ledger()), review)
        plan = ledger['entries'][0]
        self.assertEqual((plan['planned_dca_usd'], plan['trade_ids']), (0, []))
        self.assertGreater(plan['planned_baseline_usd'], 0)
        self.assertAlmostEqual(sum(plan['baseline_allocation'].values()), plan['planned_baseline_usd'])
        receipt = dict(status='partial', dca_usd=0, baseline_usd=1, broker_fill_ids=['synthetic-fill'],
                       broker_readback_verified=True, broker_orders_clear=True)
        with self.assertRaisesRegex(ValueError, 'reserved plan'):
            transition(ledger, 'settle', reservation_id='synthetic-plan',
                       receipt=dict(receipt, baseline_usd=plan['planned_baseline_usd'] + 1))
        for outcome in (receipt, dict(receipt, status='released', baseline_usd=0, broker_fill_ids=[])):
            settled = transition(ledger, 'settle', reservation_id='synthetic-plan', receipt=outcome)
            self.assertTrue(settled['persistence_required'])
            self.assertFalse(settled['execution_authorized'])
            self.assertEqual(settled['funding_ledger']['entries'][0]['status'], outcome['status'])
            with self.assertRaisesRegex(ValueError, 'plan already exists'):
                reserve(settled['funding_ledger'], fx_review('another-fx'), 'synthetic-second-plan')

    def test_saved_plan_only_blocks_its_new_york_month(self):
        ledger = reserve(upgrade(legacy_ledger()), fixture())
        review = fixture()
        review['funding_ledger'] = ledger
        next_date = dt.datetime(2026, 11, 2, 15, tzinfo=dt.timezone.utc)
        review['schedule']['monthly_execution_date'] = '2026-11-02'
        for capability in review['capabilities'].values():
            capability['observed_at'] = next_date.isoformat()
        result = helper.check(review, next_date)
        self.assertEqual(result['allocation_period'], '2026-11')
        self.assertTrue(result['monthly_plan_reservable'])


class DrawdownTierTests(unittest.TestCase):
    def test_crossing_maximum_leaves_unused_tiers_intact_and_peer_eligible(self):
        payload = fixture()
        payload['task'] = 'drawdown'
        items = payload['capabilities']['market_inputs']['data']
        items['QQQM'].update(drawdown=.27, tiers_executed=['T1'])
        items['SPYM']['drawdown'] = .10
        result = helper.check(payload, NOW)['deployment']
        self.assertEqual(result['candidate_tiers'], {'QQQM': [], 'SPYM': ['T1']})
        self.assertEqual([tier['state'] for tier in result['tier_allocations']['QQQM']],
                         ['executed', 'above_maximum', 'above_maximum', 'above_maximum'])
        items['QQQM']['drawdown'] = .25
        result = helper.check(payload, NOW)['deployment']
        self.assertIn('T4', result['candidate_tiers']['QQQM'])

    def test_partial_tier_allocation_and_verified_fills(self):
        payload = fixture()
        payload['task'] = 'drawdown'
        item = payload['capabilities']['market_inputs']['data']['QQQM']
        item['drawdown'] = .21
        payload['capabilities']['balances']['data']['balances'][1]['settled_cash'] = 900
        result = helper.check(payload, NOW)['deployment']
        tiers = result['tier_allocations']['QQQM']
        self.assertEqual([tier['allocation_usd'] for tier in tiers], [600, 300, 0, 0])
        self.assertEqual(tiers[1]['budget_usd'], 1200)
        self.assertEqual(tiers[2]['state'], 'no_capacity')
        self.assertTrue(all(tier['receipt'] is None for tier in tiers))
        peak = '2026-09-01'
        receipt = dict(cycle_peak_date=peak, allocation_usd=600, filled_usd=500,
                       broker_fill_ids=['synthetic-fill'])
        item.update(tiers_executed=['T1'], cycle_peak_date=peak, tier_receipts={'T1': receipt})
        result = helper.check(payload, NOW)['deployment']
        self.assertEqual(result['tier_allocations']['QQQM'][0]['receipt'], receipt)
        self.assertNotIn('T1', result['candidate_tiers']['QQQM'])
        item['tier_receipts']['T1'] = dict(receipt, cycle_peak_date='2026-08-01')
        blocked = helper.check(payload, NOW)
        self.assertIsNone(blocked['deployment']['tier_allocations']['QQQM'])
        self.assertEqual(blocked['paths']['SPYM']['status'], 'PASS')

    def test_fill_cannot_be_claimed_by_two_ladders(self):
        payload = fixture()
        payload['task'] = 'drawdown'
        peak = '2026-09-01'
        for item in payload['capabilities']['market_inputs']['data'].values():
            item.update(drawdown=.17, tiers_executed=['T1'], cycle_peak_date=peak,
                        tier_receipts={'T1': dict(cycle_peak_date=peak, allocation_usd=500,
                            filled_usd=500, broker_fill_ids=['synthetic-shared-fill'])})
        result = helper.check(payload, NOW)
        self.assertEqual(result['status'], 'DATA INCOMPLETE')
        self.assertIsNone(result['deployment'])
        self.assertTrue(all(path['status'] == 'DATA INCOMPLETE' for path in result['paths'].values()))


if __name__ == '__main__':
    unittest.main()
