import copy
import json
import subprocess
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime

from avanza10_capital import configure, requirements, membership, validate_transition
from avanza10_forward import POLICY, decide, observe_account, run
from quality_forward import digest
from audit_avanza10 import audit_funding
from test_avanza10_forward import fixture


class CapitalPolicyTests(unittest.TestCase):
    def test_auto_minimum_is_not_twenty_thousand_and_is_independently_audited(self):
        old,r,a,data,client,now=fixture()
        new,archived=configure(None,a,r,now,digest(POLICY))
        need=requirements(a,r['fx']['usdsek'])
        self.assertEqual(new['initial_sek'],need['minimum_capital_sek'])
        self.assertLess(new['initial_sek'],20000)
        self.assertEqual(new['capital_configuration']['mode'],'AUTO_MINIMUM')
        self.assertIsNone(archived)
        self.assertFalse(new['strategy']['trades'])
        self.assertEqual(audit_funding(a,r['fx']['usdsek'],need)['status'],'PASS')
        decide(new,r,a,data,now)
        self.assertEqual(len(new['pending']['targets']),10)
        self.assertTrue(all(o['quantity']>=1 and isinstance(o['quantity'],int) for o in new['pending']['plan']['orders']))

    def test_expensive_names_never_change_for_capital_and_cash_in_python_or_browser(self):
        old,r,a,data,client,now=fixture()
        expensive=a['selection']['rows'][0]['ticker'];a['quotes'][expensive]=5000
        names=[x['ticker'] for x in membership(a['selection']['rows'])]
        self.assertIn(expensive,names)
        for amount in ['500','20000','100000','400000']:
            new,_=configure(None,a,r,now,digest(POLICY),amount)
            self.assertEqual(new['initial_sek'],float(amount))
            decide(new,r,a,data,now)
            self.assertEqual([x['ticker'] for x in new['ranked_targets']],names)
            if float(amount)<requirements(a,10)['minimum_capital_sek']:
                self.assertIsNone(new['pending'])
                self.assertIn('UNFUNDED_OR_RISK_LIMITED_MINIMUM_BASKET',new['blockers'])
        a['selection']['usdsek']=10
        browser_report=dict(r,delivery={'verified':True},avanza10=a)
        js="""const fs=require('fs');const p=require('./public/avanza10-plan');const r=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify([500,20000,100000,400000].map(capital=>{const x=p.plan(r,{capital,cash:capital,holdings:{},excluded:new Set()},new Date('2026-11-02T08:17:00Z'));return {names:x.rows.map(z=>z.ticker),minimum:x.minimumCapital,total:x.minimumTotal,shortfall:x.capitalShortfall};})));"""
        result=json.loads(subprocess.check_output(['node','-e',js],input=json.dumps(browser_report),text=True))
        need=requirements(a,10)
        for row in result:
            self.assertEqual(row['names'],names)
            self.assertEqual(row['minimum'],need['minimum_capital_sek'])
            self.assertEqual(row['total'],need['minimum_one_each_sek'])
        self.assertGreater(result[0]['shortfall'],0)
        self.assertEqual(result[-1]['shortfall'],0)

    def test_untraded_legacy_is_preserved_exactly_before_new_cohort(self):
        old,r,a,data,client,now=fixture()
        old['initialized_at']='2026-11-01T08:17:00+00:00'
        old['strategy']['equity']=[dict(date='2026-11-01',nav=2000)]
        original=copy.deepcopy(old)
        new,archived=configure(old,a,r,now,digest(POLICY))
        self.assertEqual(old,original);self.assertEqual(archived,original)
        self.assertEqual(new['supersedes']['sha256'],digest(original))
        self.assertTrue(validate_transition(original,new,archived))
        self.assertEqual(new['initialized_at'],now.isoformat())
        self.assertFalse(new['strategy']['trades']);self.assertFalse(new['strategy']['equity'])
        bad=copy.deepcopy(archived);bad['initial_sek']+=1
        with self.assertRaises(AssertionError):validate_transition(original,new,bad)

    def test_locked_configuration_and_existing_fills_are_never_recapitalized(self):
        old,r,a,data,client,now=fixture()
        new,_=configure(None,a,r,now,digest(POLICY),'60000')
        unchanged,archive=configure(new,a,r,now,digest(POLICY),'150000')
        self.assertEqual(unchanged,new);self.assertIsNone(archive)
        old['strategy']['trades']=[{'side':'BUY','ticker':'RECORDED'}]
        unchanged,archive=configure(old,a,r,now,digest(POLICY),'150000')
        self.assertEqual(unchanged,old);self.assertIsNone(archive)

    def test_new_capital_never_creates_a_purchase_at_an_already_passed_open(self):
        old,r,a,data,client,now=fixture()
        now=datetime.fromisoformat('2026-11-02T14:47:00+00:00')
        r['generated_at']=now.isoformat()
        new,_=configure(None,a,r,now,digest(POLICY))
        decide(new,r,a,data,now)
        after=observe_account(new,data,client,now)
        self.assertFalse(after['strategy']['trades'])
        self.assertIsNotNone(after['pending'])
        self.assertEqual(after['pending']['created_at'],now.isoformat())

    def test_collection_crossing_an_open_cannot_backdate_the_new_capital_commitment(self):
        old,r,a,data,client,_=fixture()
        start=datetime.fromisoformat('2026-11-02T14:29:00+00:00')
        after=datetime.fromisoformat('2026-11-02T14:31:00+00:00')
        r['generated_at']=start.isoformat()
        class Clock(datetime):
            calls=0
            @classmethod
            def now(cls,tz=None):
                cls.calls+=1
                return start if cls.calls==1 else after
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);out=root/'out';out.mkdir();prev=root/'previous';prev.mkdir()
            (out/'quality.json').write_text(json.dumps(r));(out/'avanza10.json').write_text(json.dumps(a))
            with patch('avanza10_forward.datetime',Clock), patch('avanza10_forward.data_for',return_value=(data,client)), patch.dict('os.environ',{'AVANZA_INITIAL_SEK':'AUTO_MINIMUM'}):
                run(SimpleNamespace(output=str(out),previous=str(prev),cache=str(root/'cache')))
            state=json.loads((out/'avanza-state.json').read_text())
            self.assertEqual(state['initialized_at'],after.isoformat())
            self.assertEqual(state['pending']['created_at'],after.isoformat())
            self.assertFalse(state['strategy']['trades'])

    def test_incomplete_data_or_invalid_choice_never_initializes_or_swaps_names(self):
        old,r,a,data,client,now=fixture()
        for invalid in ['garbage','0','-1','nan','5.005']:
            with self.assertRaises(ValueError):configure(None,a,r,now,digest(POLICY),invalid)
        del a['quotes'][a['selection']['rows'][0]['ticker']]
        with self.assertRaises(ValueError):configure(None,a,r,now,digest(POLICY))
        a['selection']['rows']=a['selection']['rows'][:3]
        with self.assertRaises(ValueError):configure(None,a,r,now,digest(POLICY),'60000')
