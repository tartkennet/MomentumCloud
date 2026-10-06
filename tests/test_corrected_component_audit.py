import itertools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_corrected_component_audit as audit

class ComponentAccountingTests(unittest.TestCase):
    def test_interaction_allocated_once(self):
        values={x:2*x[0]+3*x[1]+5*x[2]+7*x[0]*x[1] for x in itertools.product([False,True],repeat=3)}
        result=audit.factorial_contributions(values)
        self.assertAlmostEqual(result['stop_keeping_effect_pp'],5.5)
        self.assertAlmostEqual(result['regime_keeping_effect_pp'],6.5)
        self.assertAlmostEqual(result['extension_keeping_effect_pp'],5.0)
        self.assertAlmostEqual(result['all_rules_minus_none_pp'],17.0)

    def test_provider_snapshot_reuses_exact_response(self):
        calls=[]
        def fake(self,path,params=None):
            calls.append(path)
            return {'results':[{'close':len(calls)}]}
        with tempfile.TemporaryDirectory() as d,patch.object(audit,'SNAPSHOT',Path(d)),patch.object(audit.PolygonClient,'_get',fake):
            audit.freeze_provider()
            client=object.__new__(audit.PolygonClient)
            first=client._get('/test',{'date':'2023-01-01'})
            self.assertEqual(first,client._get('/test',{'date':'2023-01-01'}))
            self.assertEqual(len(calls),1)
            self.assertNotEqual(first,client._get('/test',{'date':'2023-01-02'}))

    def test_secret_removed_from_snapshot_pagination(self):
        value={'next_url':'https://api.example/test?cursor=abc&apiKey=secret','apiKey':'secret'}
        self.assertEqual(audit.redact_response(value),{'next_url':'https://api.example/test?cursor=abc'})
