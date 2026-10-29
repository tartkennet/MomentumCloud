import copy
import math
import statistics
import unittest
from dataclasses import replace

import momentum_core as core
from audit_core_normalized import audit_targets
from research_core_formation import MODEL, select_targets
from research_core_normalized import select_targets as original
from run_core_normalized_research import candidate_selection
from test_momentum_core import long_data


class FormationRiskTests(unittest.TestCase):
    def data(self):
        d = long_data()
        # A past announcement jump followed by stable quotes. Both numerator
        # and matched denominator contain the jump; the recent 63 days do not.
        for i, day in enumerate(d.days):
            price = (40 if i < 170 else 80) * math.exp(.00001 * i + .0002 * math.sin(i))
            d.by_day[day]['S00'] = [price, price, 1_000_000]
        return d

    def test_past_jump_cannot_disappear_only_from_the_rank_denominator(self):
        d = self.data()
        old, n0 = original(d, d.days[-1])
        new, n1 = select_targets(d, d.days[-1])
        self.assertEqual(n0, n1)
        self.assertEqual(old[0]['ticker'], 'S00')
        self.assertNotEqual(new[0]['ticker'], 'S00')
        history = core.adjusted_history(d, d.days[-1], new[0]['ticker'], 253)
        expected = statistics.stdev(history[i]/history[i+1]-1 for i in range(21,252))
        self.assertAlmostEqual(new[0]['formation_volatility'], expected)
        self.assertAlmostEqual(sum(r['weight'] for r in new), 1)
        for row in new:
            self.assertLessEqual(row['weight'], .1)

    def test_recent_price_changes_affect_sizing_but_not_formation_rank(self):
        d = self.data()
        before, _ = select_targets(d, d.days[-1])
        for day in d.days[-21:]:
            for ticker, bar in d.by_day[day].items():
                if ticker != 'SPY':
                    bar[1] *= 1.02
        after, _ = select_targets(d, d.days[-1])
        self.assertEqual([r['ticker'] for r in before], [r['ticker'] for r in after])
        for a,b in zip(before,after):
            self.assertEqual(a['formation_volatility'],b['formation_volatility'])
            self.assertEqual(a['risk_normalized_score'],b['risk_normalized_score'])

    def test_independent_formation_audit_and_wrong_denominator_rejection(self):
        d = self.data(); d.sessions = d.days[252:]
        config = replace(core.CONFIG, model=MODEL)
        l = core.Ledger()
        with candidate_selection(select_targets):
            for day in d.sessions:
                l.step(d, day, config)
        self.assertEqual(audit_targets(d, config, l.targets, l.trades, formation=True)['status'], 'PASS')
        targets = copy.deepcopy(l.targets)
        row = targets[0]['targets'][0]
        row['risk_normalized_score'] = row['momentum_12_2'] / row['daily_volatility']
        with self.assertRaises(AssertionError):
            audit_targets(d, config, targets, l.trades, formation=True)

    def test_cost_and_future_prices_cannot_select_different_stocks(self):
        d = self.data(); day = d.days[-2]
        before = select_targets(d, day)
        d.by_day[d.days[-1]]['S19'] = [1,1,1]
        self.assertEqual(before, select_targets(d, day, replace(core.CONFIG, one_way_cost=.003)))
