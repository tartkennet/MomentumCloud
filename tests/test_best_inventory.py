import tempfile
import json
import unittest
from pathlib import Path
from best_inventory import scan

class InventoryTests(unittest.TestCase):
    def test_interrupted_scan_resumes_and_requires_every_record(self):
        records=[dict(ticker='T'+str(i)) for i in range(12)]
        calls=[]
        def evaluate(record):
            calls.append(record['ticker'])
            if len(calls)==7:raise RuntimeError('interrupted')
            return dict(ticker=record['ticker']),None
        with tempfile.TemporaryDirectory() as cache:
            with self.assertRaises(RuntimeError):scan(records,evaluate,cache,{'day':'2026-11-05'},batch_size=5)
            calls.clear()
            rows,excluded,manifest=scan(records,lambda r:(calls.append(r['ticker']) or dict(r),None),cache,{'day':'2026-11-05'},batch_size=5)
            self.assertEqual(len(rows),12);self.assertEqual(len(calls),7)
            self.assertTrue(manifest['complete']);self.assertEqual(manifest['resumed_batches'],1)
            self.assertEqual(manifest['processed_records'],12)
            changed=Path(cache)/'best-inventory-v1'/manifest['fingerprint']/'0.json'
            payload=json.loads(changed.read_text());payload['start']=1;changed.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):scan(records,lambda r:(dict(r),None),cache,{'day':'2026-11-05'},batch_size=5)

    def test_source_change_invalidates_cached_batches_without_limiting_universe(self):
        records=[dict(ticker='T'+str(i)) for i in range(301)]
        with tempfile.TemporaryDirectory() as cache:
            a=scan(records,lambda r:(dict(r),None),cache,{'source':'A'})[2]
            b=scan(records,lambda r:(None,'MISSING'),cache,{'source':'B'})[2]
            self.assertNotEqual(a['fingerprint'],b['fingerprint'])
            self.assertEqual(b['excluded_records'],301);self.assertTrue(b['complete'])


class ClassificationTests(unittest.TestCase):
    def test_missing_reference_classification_uses_only_dated_matching_filer_metadata(self):
        from best_forward import reference
        row=dict(ticker='TEST',cik='0000000123')
        class Client:
            def get(self,path,params):
                if '/tickers/' in path:return {'results':dict(ticker='TEST',cik='123',sic_code=None,type='CS')}
                return {'results':[
                    dict(filing_date='20261106',id='future',entities=[dict(relation='filer',company_data=dict(cik='123',sic='7372'))]),
                    dict(filing_date='20261104',id='wrong',entities=[dict(relation='filer',company_data=dict(cik='999',sic='7372'))]),
                    dict(filing_date='20261103',id='actual',entities=[dict(relation='filer',company_data=dict(cik='123',sic='5411'))])
                ]}
        with tempfile.TemporaryDirectory() as cache:
            result=reference(row,'2026-11-05',Path(cache),Client())
            self.assertEqual(result['sic'],'5411');self.assertEqual(result['division'],'Retail')
            saved=json.loads((Path(cache)/'best-reference-v1/2026-11-05/TEST.json').read_text())
            self.assertEqual(saved['sic_evidence']['accession'],'actual')
            self.assertLessEqual(saved['sic_evidence']['filed'],'2026-11-05')

    def test_unknown_classification_does_not_silently_drop_the_strong_name(self):
        from best_forward import reference
        row=dict(ticker='TEST',cik='0000000123')
        class Client:
            def get(self,path,params):
                return {'results':dict(ticker='TEST',cik='123',sic_code=None,type='CS')} if '/tickers/' in path else {'results':[]}
        with tempfile.TemporaryDirectory() as cache:
            with self.assertRaisesRegex(ValueError,'UNVERIFIED_INDUSTRY_CLASSIFICATION_TEST'):
                reference(row,'2026-11-05',Path(cache),Client())
