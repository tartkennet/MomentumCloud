import os
import unittest
from unittest.mock import patch
from probe_h3_readiness import probe


class H3ReadinessTests(unittest.TestCase):
    def test_existing_key_checks_only_access_and_quotes_do_not_require_purchase(self):
        calls=[]
        def query(key,path,params):
            calls.append(path)
            return {'authorized':False,'http_status':403} if 'quotes' in path else {'authorized':True,'rows':1}
        with patch.dict(os.environ,{'POLYGON_API_KEY':'secret-fixture'}):report=probe(True,query=query)
        self.assertEqual(report['status'],'PASS');self.assertEqual(len(calls),5)
        self.assertFalse(report['optional_quotes']['authorized'])
        self.assertNotIn('secret-fixture',str(report));self.assertFalse(report['subscription_changed'])

    def test_missing_key_blocks_without_making_a_request(self):
        with patch.dict(os.environ,{},clear=True):
            r=probe(True,query=lambda *a: self.fail('No request without key'))
        self.assertEqual(r['status'],'DATA_BLOCKED')
