import json
import tempfile
import unittest
import hashlib
from pathlib import Path
from types import SimpleNamespace

from build_momentum10_v2_view import build


class Momentum10PublicationTests(unittest.TestCase):
    def test_incomplete_study_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder,'results.json').write_text(json.dumps({'completed':False,'attempts':[]}))
            with self.assertRaises(AssertionError):build(SimpleNamespace(evidence=folder))

    def test_changed_strategy_cannot_be_published_as_executed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            r={'completed':True,'attempts':[{}]*20,'variants':[{}],
               'sources':{'research_momentum10_v2.py':'0'*64}}
            Path(folder,'results.json').write_text(json.dumps(r))
            with self.assertRaises(AssertionError):build(SimpleNamespace(evidence=folder))

    def test_published_cases_reconcile_and_keep_go_constraints(self):
        manifest=Path('public/data/momentum10-v2.json')
        if not manifest.exists():self.skipTest('Publication is created only after completed research')
        r=json.loads(manifest.read_text())
        self.assertTrue(r['completed']);self.assertFalse(r['untouched_out_of_sample'])
        self.assertFalse(r['live_approved']);self.assertFalse(r['broker_orders_enabled'])
        self.assertEqual(len(r['attempts']),20*len(r['variants']))
        for f,h in r['sources'].items():self.assertEqual(hashlib.sha256(Path(f).read_bytes()).hexdigest(),h)
        for v in r['variants']:
            cases=[a for a in r['attempts'] if a['variant']==v['variant']]
            self.assertEqual(len(cases),20)
            self.assertEqual(v['paper_pass'],all(a['decision']=='PAPER_ONLY' for a in cases))
            self.assertTrue(all(a['audit']['status']=='PASS' for a in cases))
            d=json.loads(Path('public/data/momentum10-v2',v['variant']+'.json').read_text())
            self.assertNotIn('SPY',{p['ticker'] for p in d['positions']})
            self.assertAlmostEqual(d['curve'][0]['nav_sek'],20000,places=6)
            nav=sum(p['value_sek'] for p in d['positions'])+d['cash_sek']+d['claims_sek']
            self.assertAlmostEqual(nav,d['curve'][-1]['nav_sek'],places=6)
            self.assertTrue(all(float(t['quantity']).is_integer() for t in d['trades'] if t['side'] in ('BUY','SELL')))
            gates={g['gate']:g for g in d['result']['gates']}
            self.assertEqual(gates['drawdown']['requirement'],'>= -20%')
            self.assertEqual(gates['at_least_30_periods']['requirement'],'>= 30')
