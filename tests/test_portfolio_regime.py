import copy
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

import momentum_core as core
from research_portfolio_regime import MODEL,PortfolioLedger,select_targets
from research_portfolio_diversified import select_targets as h2_targets
from research_core_formation import select_targets as original
from audit_portfolio_regime import audit_targets
from run_core_normalized_research import candidate_selection
from test_momentum_core import long_data


class PortfolioRegimeTests(unittest.TestCase):
    def test_risk_on_weights_are_exactly_frozen_h2_without_new_parameters(self):
        d=long_data();day=d.days[-2]
        self.assertEqual(select_targets(d,day),h2_targets(d,day))
        before=select_targets(d,day);d.by_day[d.days[-1]]['SPY']=[1e9,.01,1]
        self.assertEqual(before,select_targets(d,day,replace(core.CONFIG,one_way_cost=.003)))

    def test_risk_off_liquidates_both_sleeves_at_next_open_not_signal_close(self):
        d=long_data();days=d.days[253:258];l=PortfolioLedger()
        with candidate_selection(select_targets),patch('momentum_core.risk_on',side_effect=lambda _,day:day<days[2]):
            for day in days[:3]:l.step(d,day)
            self.assertIn('SPY',l.shares);self.assertGreater(len(l.shares),1)
            self.assertEqual(l.pending['targets'],[])
            old=copy.deepcopy(l.to_dict());resumed=PortfolioLedger(**json.loads(json.dumps(old)))
            for day in days[3:]:l.step(d,day);resumed.step(d,day)
        self.assertEqual(l.shares,{})
        self.assertEqual(l.to_dict(),resumed.to_dict())
        self.assertTrue(any(t['side']=='SELL' and t['ticker']=='SPY' and t['date']==days[3] and t['signal_date']==days[2] for t in l.trades))
        self.assertEqual(old['equity'],l.equity[:3])

    def test_independent_auditor_rejects_a_passive_core_during_risk_off(self):
        d=long_data();d.sessions=d.days[253:]
        for day in d.days[-5:]:d.by_day[day]['SPY'][1]=1
        cfg=replace(core.CONFIG,model=MODEL);old=core.Ledger();new=PortfolioLedger()
        with candidate_selection(original):
            for day in d.sessions:old.step(d,day,cfg)
        with candidate_selection(select_targets):
            for day in d.sessions:new.step(d,day,cfg)
        refs={s['date']:s for s in old.targets}
        self.assertEqual(audit_targets(d,cfg,new.targets,refs,new.trades)['status'],'PASS')
        bad=copy.deepcopy(new.targets);next(s for s in bad if not s['risk_on'])['targets']=[{'ticker':'SPY','weight':.7,'benchmark_core':True}]
        with self.assertRaises(AssertionError):audit_targets(d,cfg,bad,refs)

    def test_stress_account_resumes_without_changing_any_prior_observation(self):
        d=long_data();days=d.days[253:];cfg=replace(core.CONFIG,one_way_cost=.003)
        full=PortfolioLedger();split=PortfolioLedger()
        with candidate_selection(select_targets):
            for day in days:full.step(d,day,cfg)
            for day in days[:22]:split.step(d,day,cfg)
            split=PortfolioLedger(**json.loads(json.dumps(split.to_dict())))
            for day in days[22:]:split.step(d,day,cfg)
        self.assertEqual(full.to_dict(),split.to_dict())
