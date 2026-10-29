import copy
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import momentum_core as core
import run_momentum_core as base
from momentum_core_data import atomic_json
from run_portfolio_forward import run,paper_engine,require_fresh,fingerprint
from research_portfolio_regime import MODEL,PortfolioLedger,select_targets
from run_core_normalized_research import candidate_selection
from run_core_risk_research import DailyEvents,replay
from test_momentum_core import long_data


class PortfolioForwardTests(unittest.TestCase):
    def test_financially_unqualified_source_cannot_start_a_forward_identity(self):
        with tempfile.TemporaryDirectory() as name,patch('run_portfolio_forward.qualify',side_effect=core.DataBlocked('not qualified')):
            with self.assertRaises(core.DataBlocked):run('2026-10-28',name,name,offline=True)
            self.assertFalse((Path(name)/'Momentum_core_paper_identity.json').exists())
            orders=json.loads((Path(name)/'Momentum_core_paper_orders.json').read_text())
            self.assertIsNone(orders['intentions_for_next_observed_session'])

    def test_waiting_freezes_source_without_data_or_synthetic_returns(self):
        with tempfile.TemporaryDirectory() as name,patch('run_portfolio_forward.qualify',return_value='verified'),patch('run_portfolio_forward._CORE_DATA',side_effect=AssertionError('No market data')):
            result=run('2026-10-28',name,name,offline=True)
            self.assertEqual(result['status'],'PAPER_WAITING_FOR_SESSIONS')
            self.assertEqual(result['model'],MODEL)
            self.assertFalse((Path(name)/'Momentum_core_paper_checkpoint.json').exists())
            identity=json.loads((Path(name)/'Momentum_core_paper_identity.json').read_text())
            self.assertEqual(identity['source_fingerprint'],fingerprint())
            self.assertFalse(identity['broker_orders_enabled'])

    def test_changed_source_blocks_even_while_waiting_and_clears_intentions(self):
        with tempfile.TemporaryDirectory() as name,patch('run_portfolio_forward.qualify',return_value='verified'):
            atomic_json(Path(name)/'Momentum_core_paper_identity.json',{'source_fingerprint':'old'})
            with self.assertRaises(core.DataBlocked):run('2026-10-28',name,name,offline=True)
            orders=json.loads((Path(name)/'Momentum_core_paper_orders.json').read_text())
            self.assertIsNone(orders['intentions_for_next_observed_session'])

    def test_missed_sessions_and_late_intentions_block_instead_of_rebuilding_history(self):
        with self.assertRaises(core.DataBlocked):require_fresh(SimpleNamespace(sessions=['a','b']))
        with patch('run_portfolio_forward.datetime') as clock:
            clock.now.return_value=datetime(2026,10,30,12,tzinfo=timezone.utc)
            with self.assertRaises(core.DataBlocked):require_fresh(SimpleNamespace(sessions=['a']))
            require_fresh(SimpleNamespace(sessions=[]))

    def test_bindings_restore_after_interruption_without_changing_original_core(self):
        before=(base.MODEL,base.source_fingerprint,core.select_targets)
        with self.assertRaises(RuntimeError):
            with paper_engine():
                self.assertEqual(base.MODEL,MODEL)
                self.assertIs(core.select_targets,select_targets)
                raise RuntimeError('interrupted')
        self.assertEqual(before,(base.MODEL,base.source_fingerprint,core.select_targets))

    def test_daily_serialized_paper_matches_batch_at_both_costs_with_all_prefixes_intact(self):
        source=long_data();source.first_is_month_boundary=lambda:True
        days=source.days[253:295];data=DailyEvents(source)
        data.distributions=[];data.halt_marks={}
        config=replace(core.CONFIG,model=MODEL)
        with candidate_selection(select_targets):
            data.sessions=days
            full,full_spy,_,_=replay(data,config,cls=PortfolioLedger)
            stress,stress_spy,_,_=replay(data,replace(config,one_way_cost=.003),cls=PortfolioLedger)
        with paper_engine(),patch('run_portfolio_forward.require_fresh'):
            data.sessions=days[:1]
            s,b,_,_=base.replay(data)
            ss,bb,_,_=base.replay(data,replace(config,one_way_cost=.003))
            for day in days[1:]:
                prior={'strategy':s.to_dict(),'benchmark':b.to_dict(),'stress_strategy':ss.to_dict(),'stress_benchmark':bb.to_dict()}
                original=copy.deepcopy(prior);data.sessions=[day]
                s,b,_,_=base.resume_paper(data,prior)
                ss,bb,_,_=base.resume_paper(data,prior,replace(config,one_way_cost=.003),stress=True)
                self.assertEqual(prior,original)
        for actual,expected in ((s,full),(b,full_spy),(ss,stress),(bb,stress_spy)):
            self.assertEqual(actual.to_dict(),expected.to_dict())
