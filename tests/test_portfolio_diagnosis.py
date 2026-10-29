import unittest
from analyze_formation_portfolio import concentration, episodes, risk_snapshot
from test_momentum_core import long_data


class PortfolioDiagnosisTests(unittest.TestCase):
    def test_effective_diversification_does_not_count_cash_as_a_stock(self):
        r=concentration({'A':25000,'B':25000},100000)
        self.assertEqual(r['effective_stock_count'],2)
        self.assertEqual(r['gross_exposure'],.5)
        self.assertEqual(concentration({},100000)['effective_stock_count'],0)

    def test_drawdown_episodes_do_not_double_count_nested_losses(self):
        rows=[{'nav':n} for n in (100,120,90,100,80,120,100,130,120)]
        self.assertEqual(episodes(rows),[(1,4,5),(5,6,7),(7,8,None)])

    def test_covariance_includes_correlated_position_risk_and_ignores_future(self):
        d=long_data(); day=d.days[-2]
        t=[{'ticker':'S18','weight':.5},{'ticker':'S19','weight':.5}]
        before=risk_snapshot(d,day,t)
        self.assertAlmostEqual(sum(r['fraction'] for r in before['variance_contributions']),1)
        self.assertGreater(before['weighted_pair_correlation'],.99)
        d.by_day[d.days[-1]]['S19']=[999999,1,1]
        self.assertEqual(before,risk_snapshot(d,day,t))
        self.assertEqual(risk_snapshot(d,day,[])['status'],'INSUFFICIENT_HISTORY')
