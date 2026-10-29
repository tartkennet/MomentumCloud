import copy
import math
import unittest
from dataclasses import replace

import momentum_core as core
from research_portfolio_risk import risk_budget, select_targets, MODEL
from research_core_formation import select_targets as original
from audit_portfolio_risk import expected_risk, audit_targets
from run_core_normalized_research import candidate_selection
from test_momentum_core import long_data


class PortfolioRiskTests(unittest.TestCase):
    def test_budget_matches_benchmark_risk_without_changing_rank_or_proportions(self):
        d=long_data(); day=d.days[-1]
        old,n=original(d,day); frozen=copy.deepcopy(old)
        new,count=select_targets(d,day)
        self.assertEqual(n,count); self.assertEqual(old,frozen)
        self.assertEqual([r['ticker'] for r in old],[r['ticker'] for r in new])
        _,scale,pvol,svol=expected_risk(d,day,old,core.CONFIG)
        self.assertLess(scale,1)
        self.assertAlmostEqual(scale*pvol,svol)
        for a,b in zip(new,old):
            self.assertAlmostEqual(a['weight'],b['weight']*scale)
            self.assertLessEqual(a['weight'],.1)

    def test_same_past_signal_after_future_price_or_cost_changes(self):
        d=long_data();day=d.days[-2];before=select_targets(d,day)
        d.by_day[d.days[-1]]['S19']=[1e9,1e-9,1]
        self.assertEqual(before,select_targets(d,day,replace(core.CONFIG,one_way_cost=.003)))

    def test_missing_risk_history_blocks_and_empty_target_stays_cash(self):
        d=long_data(); day=d.days[-1]; rows,_=original(d,day)
        self.assertEqual(risk_budget(d,day,[]),[])
        del d.by_day[d.days[-2]]['SPY']
        with self.assertRaises(core.DataBlocked): risk_budget(d,day,rows)

    def test_no_leverage_when_basket_is_less_risky_than_benchmark(self):
        d=long_data();day=d.days[-1]
        rows,_=original(d,day)
        for i,stamp in enumerate(d.days): d.by_day[stamp]['SPY'][1]*=math.exp(.1*math.sin(i))
        new=risk_budget(d,day,rows)
        self.assertEqual([r['weight'] for r in new],[r['weight'] for r in rows])
        self.assertEqual(new[0]['portfolio_risk_scale'],1)

    def test_independent_covariance_audit_rejects_overallocation(self):
        d=long_data();d.sessions=d.days[253:]; config=replace(core.CONFIG,model=MODEL)
        previous=core.Ledger();references={}
        with candidate_selection(original):
            for day in d.sessions: previous.step(d,day,config)
        references={s['date']:s for s in previous.targets}
        ledger=core.Ledger()
        with candidate_selection(select_targets):
            for day in d.sessions: ledger.step(d,day,config)
        self.assertEqual(audit_targets(d,config,ledger.targets,references,ledger.trades)['status'],'PASS')
        broken=copy.deepcopy(ledger.targets); next(s for s in broken if s['targets'])['targets'][0]['weight']*=1.01
        with self.assertRaises(AssertionError): audit_targets(d,config,broken,references)
