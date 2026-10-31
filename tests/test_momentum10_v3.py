import math
import random
import statistics
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from momentum_core import CONFIG
from research_momentum10_v3 import population,choose,SelectionLedger
from audit_momentum10_v3 import population as independent_population,independently_choose


class SelectionTests(unittest.TestCase):
    def data(self,closes):
        stamps=[f'{9999-i:04d}-01-01' for i in range(253)]
        rows=[(d,[p,p,1_000_000]) for d,p in zip(stamps,closes)]
        return SimpleNamespace(universe=lambda day:[dict(ticker='ABC',name='Example',active=True,type='CS',primary_exchange='XNAS')],
            history=lambda day,t,n:rows[:n],signal_splits=lambda d,t:[],splits=[])

    def test_latest_close_and_positive_6m_do_not_require_old_12_2_gain(self):
        closes=[120*math.exp(-.003*i+.003*math.sin(i)) for i in range(253)]
        closes[-1]=200 # old 12-2 return negative, current 6m return positive
        data=self.data(closes)
        with patch('momentum_core.adjusted_history',return_value=closes):a=population(data,'9999-01-01',{},'R')
        b=independent_population(data,'9999-01-01',CONFIG,'R')
        self.assertEqual(len(a),1);self.assertEqual(len(b),1)
        self.assertAlmostEqual(a[0]['risk_normalized_score'],b[0]['risk_normalized_score'])
        closes2=closes[:];closes2[0]*=1.1
        with patch('momentum_core.adjusted_history',return_value=closes2):c=population(data,'9999-01-01',{},'R')
        self.assertNotEqual(a[0]['risk_normalized_score'],c[0]['risk_normalized_score'])

    def test_trend_filter_excludes_declining_path_even_if_1m_3m_positive(self):
        c=[100.]*253
        c[:21]=[100+10*math.sin(i/7)**2 for i in range(21)]
        c[21]=99;c[22:63]=[120.]*41;c[63]=80;c[126]=70
        data=self.data(c)
        with patch('momentum_core.adjusted_history',return_value=c):
            self.assertEqual(len(population(data,'9999-01-01',{},'R')),1)
            self.assertEqual(population(data,'9999-01-01',{},'T'),[])
        self.assertEqual(independent_population(data,'9999-01-01',CONFIG,'T'),[])

    def test_cluster_cap_not_just_pairwise_and_selector_is_independent(self):
        rng=random.Random(17)
        a=[rng.gauss(0,1) for _ in range(63)]
        rows=[dict(ticker=f'S{i}',_returns=a[:]) for i in range(3)]
        rows += [dict(ticker=f'S{i}',_returns=[rng.gauss(0,1) for _ in range(63)]) for i in range(3,14)]
        got=choose(rows,'D');check=independently_choose(rows,'D')
        self.assertEqual([r['ticker'] for r in got],[r['ticker'] for r in check])
        self.assertNotIn('S2',[r['ticker'] for r in got]);self.assertEqual(len(got),10)
        self.assertFalse(any('_returns' in r for r in got))
        self.assertEqual(choose(rows[:3],'D'),[])

    def test_all_three_intervals_and_stops_use_frozen_execution(self):
        from research_momentum10_v2 import RetentionLedger
        for interval in (1,2,3):
            for stop in ('none','fixed10','vol'):
                s=SelectionLedger(interval=interval,stop_mode=stop,stage='D')
                self.assertIs(type(s).execute_open,RetentionLedger.execute_open)
                self.assertIs(type(s).events_before_open,RetentionLedger.events_before_open)
        self.assertFalse(SelectionLedger().risk_budget)

    def test_independent_auditor_does_not_import_candidate(self):
        from pathlib import Path
        text=Path('audit_momentum10_v3.py').read_text()
        self.assertNotIn('from research_momentum10_v3',text)
        self.assertNotIn('import research_momentum10_v3',text)


if __name__=='__main__':unittest.main()
