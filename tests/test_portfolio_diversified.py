import copy
import json
import unittest
from dataclasses import replace
from unittest.mock import patch

import momentum_core as core
from research_portfolio_diversified import MODEL,DiversifiedLedger,select_targets,risk_budget
from research_core_formation import select_targets as original
from audit_portfolio_diversified import audit_targets
from audit_portfolio_risk import expected_risk
from run_core_normalized_research import candidate_selection
from test_momentum_core import long_data


class DiversifiedPortfolioTests(unittest.TestCase):
    def test_equal_risk_between_two_sleeves_without_a_selected_percentage(self):
        d=long_data();day=d.days[-1];old,count=original(d,day)
        new,n=select_targets(d,day)
        self.assertEqual(count,n)
        self.assertEqual([r['ticker'] for r in new[:-1]],[r['ticker'] for r in old])
        _,_,pvol,svol=expected_risk(d,day,old,core.CONFIG)
        a,b=new[0]['momentum_sleeve_fraction'],new[-1]['weight']
        self.assertAlmostEqual(a*pvol,b*svol)
        self.assertAlmostEqual(sum(r['weight'] for r in new),1)
        for x,y in zip(new,old):self.assertAlmostEqual(x['weight'],y['weight']*a)
        self.assertTrue(new[-1]['benchmark_core']);self.assertEqual(new[-1]['ticker'],'SPY')

    def test_empty_stock_selection_and_initial_risk_off_keep_only_benchmark_core(self):
        d=long_data();d.sessions=d.days[-2:]
        self.assertEqual(risk_budget(d,d.days[-1],[]),[{'ticker':'SPY','weight':1.,'benchmark_core':True}])
        ledger=DiversifiedLedger()
        with patch('momentum_core.risk_on',return_value=False):
            for day in d.sessions:ledger.step(d,day)
        self.assertEqual(set(ledger.shares),{'SPY'})
        self.assertEqual(ledger.targets[0]['eligible_count'],0)
        self.assertEqual(ledger.trades[0]['signal_date'],d.sessions[0])
        self.assertEqual(ledger.trades[0]['date'],d.sessions[1])

    def test_risk_off_sells_stocks_next_open_and_preserves_serialized_core_fraction(self):
        d=long_data();days=d.days[253:258]
        ledger=DiversifiedLedger()
        with candidate_selection(select_targets),patch('momentum_core.risk_on',side_effect=lambda _,day:day<days[2]):
            for day in days[:3]:ledger.step(d,day)
            fraction=ledger.benchmark_core_weight
            self.assertGreater(len(ledger.shares),1)
            self.assertEqual(ledger.pending['targets'][0]['weight'],fraction)
            old=copy.deepcopy(ledger.to_dict())
            resumed=DiversifiedLedger(**json.loads(json.dumps(old)))
            for day in days[3:]:
                ledger.step(d,day);resumed.step(d,day)
        self.assertEqual(ledger.to_dict(),resumed.to_dict())
        self.assertEqual(set(ledger.shares),{'SPY'})
        self.assertEqual(ledger.benchmark_core_weight,fraction)
        self.assertEqual(old['equity'],ledger.equity[:3])

    def test_independent_audit_rejects_invented_risk_off_core_increase(self):
        d=long_data();d.sessions=d.days[253:]
        # Real fixture close/history regime change, not a patched auditor.
        for day in d.days[-5:]:d.by_day[day]['SPY'][1]=1
        config=replace(core.CONFIG,model=MODEL)
        old=core.Ledger();new=DiversifiedLedger()
        with candidate_selection(original):
            for day in d.sessions:old.step(d,day,config)
        with candidate_selection(select_targets):
            for day in d.sessions:new.step(d,day,config)
        refs={s['date']:s for s in old.targets}
        result=audit_targets(d,config,new.targets,refs,new.trades)
        self.assertEqual(result['status'],'PASS')
        self.assertAlmostEqual(result['last_benchmark_core_weight'],new.benchmark_core_weight)
        bad=copy.deepcopy(new.targets)
        next(s for s in bad if not s['risk_on'])['targets'][0]['weight']=1
        with self.assertRaises(AssertionError):audit_targets(d,config,bad,refs)

    def test_future_prices_and_costs_do_not_select_allocation(self):
        d=long_data();day=d.days[-2];before=select_targets(d,day)
        d.by_day[d.days[-1]]['SPY']=[999999,.01,1]
        self.assertEqual(before,select_targets(d,day,replace(core.CONFIG,one_way_cost=.003)))

    def test_double_cost_checkpoint_resumes_same_strategy_and_spy_core(self):
        d=long_data();days=d.days[253:];cfg=replace(core.CONFIG,one_way_cost=.003)
        full=DiversifiedLedger();split=DiversifiedLedger()
        with candidate_selection(select_targets):
            for day in days:full.step(d,day,cfg)
            for day in days[:22]:split.step(d,day,cfg)
            split=DiversifiedLedger(**json.loads(json.dumps(split.to_dict())))
            for day in days[22:]:split.step(d,day,cfg)
        self.assertEqual(full.to_dict(),split.to_dict())
