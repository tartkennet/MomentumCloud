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
