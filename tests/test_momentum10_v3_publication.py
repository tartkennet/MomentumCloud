import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from build_momentum10_v3_view import build
from research_momentum10_v3 import choose
from audit_momentum10_v3 import independently_choose


class PublicationTests(unittest.TestCase):
    def test_incomplete_or_altered_source_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder,'results.json');p.write_text(json.dumps({'completed':False,'attempts':[]}))
            with self.assertRaises(AssertionError):build(SimpleNamespace(evidence=folder))
            p.write_text(json.dumps({'completed':True,'attempts':[{'status':'COMPLETE','audit':{'status':'PASS'}}]*20,
                'variants':[{}],'sources':{'research_momentum10_v3.py':'0'*64}}))
            with self.assertRaises(AssertionError):build(SimpleNamespace(evidence=folder))

    def test_transitive_cluster_not_three_only_if_all_pairs_correlate(self):
        # Orthogonal zero-mean sine vectors: corr(A,B)=corr(B,C)=cos(40deg),
        # corr(A,C)=cos(80deg). A three-member component must be rejected.
        u=[math.sin(2*math.pi*i/63) for i in range(63)];v=[math.cos(2*math.pi*i/63) for i in range(63)]
        def vector(deg):return [math.cos(math.radians(deg))*a+math.sin(math.radians(deg))*b for a,b in zip(u,v)]
        rows=[dict(ticker=t,_returns=vector(deg)) for t,deg in [('A',0),('B',40),('C',80)]]
        rows += [dict(ticker=f'F{k}',_returns=[math.sin(2*math.pi*k*i/63) for i in range(63)]) for k in range(2,11)]
        for select in (choose,independently_choose):
            selected=select(rows,'D');names=[r['ticker'] for r in selected]
            self.assertEqual(len(names),10);self.assertIn('A',names);self.assertIn('B',names);self.assertNotIn('C',names)

    def test_executed_source_cases_gates_and_all_published_accounts(self):
        path=Path('public/data/momentum10-v3.json')
        if not path.exists():self.skipTest('Requires completed evidence, never fabricate a fixture')
        r=json.loads(path.read_text())
        self.assertTrue(r['completed']);self.assertFalse(r['untouched_out_of_sample'])
        self.assertFalse(r['live_approved']);self.assertFalse(r['broker_orders_enabled'])
        self.assertEqual(len(r['attempts']),20*len(r['variants']))
        for f,h in r['sources'].items():self.assertEqual(hashlib.sha256(Path(f).read_bytes()).hexdigest(),h)
        for v in r['variants']:
            cases=[a for a in r['attempts'] if a['variant']==v['variant']]
            self.assertEqual(len(cases),20);self.assertTrue(all(a['audit']['status']=='PASS' for a in cases))
            self.assertEqual(v['paper_pass'],all(a['decision']=='PAPER_ONLY' for a in cases))
            d=json.loads(Path('public/data/momentum10-v3',v['variant']+'.json').read_text())
            self.assertNotIn('SPY',{p['ticker'] for p in d['positions']})
            self.assertAlmostEqual(d['curve'][0]['nav_sek'],20000,places=6)
            self.assertAlmostEqual(sum(p['value_sek'] for p in d['positions'])+d['cash_sek']+d['claims_sek'],d['curve'][-1]['nav_sek'],places=6)
            self.assertTrue(all(float(t['quantity']).is_integer() for t in d['trades'] if t['side'] in ('BUY','SELL')))
            self.assertEqual({g['gate']:g['requirement'] for g in d['result']['gates']}['drawdown'],'>= -20%')
        final=r['hypothesis_order'][-1]
        self.assertEqual({(v['main']['interval'],v['main']['stop']) for v in r['variants'] if v['variant'].startswith(final+'_')},
            {(f,s) for f in (1,2,3) for s in ('none','fixed10','vol')})
