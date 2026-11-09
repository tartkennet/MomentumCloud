import gzip,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from best_v2_sources import canonical_sec_submission,material_original
from quality_sources import DataUnavailable
from supplement_quality_sources import sha

class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.row={'ticker':'PLSE','cik':'0001625101'}
        self.old='https://www.sec.gov/Archives/edgar/data/1625101/0001437749-26-006269.txt'
        self.good='https://www.sec.gov/Archives/edgar/data/1625101/000143774926006269/0001437749-26-006269.txt'
        self.filing=dict(cik='0001625101',accession_number='0001437749-26-006269',filing_url=self.old)
    def test_canonical_complete_submission_and_already_canonical(self):
        self.assertEqual(canonical_sec_submission(self.row,self.filing),self.good)
        self.assertEqual(canonical_sec_submission(self.row,dict(self.filing,filing_url=self.good)),self.good)
    def test_identity_and_untrusted_paths_fail_closed(self):
        for change in ({'cik':'1'},{'accession_number':'../../bad'},{'filing_url':self.old+'?key=bad'},
                       {'filing_url':self.old.replace('www.sec.gov','example.com')},
                       {'filing_url':self.old.replace('1625101','12345')}):
            with self.assertRaises(DataUnavailable):canonical_sec_submission(self.row,dict(self.filing,**change))
    def test_cached_original_reused_without_any_network(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/'best-v2-sec';folder.mkdir();key=sha(self.old.encode());raw=b'verified cached original'
            (folder/(key+'.gz')).write_bytes(gzip.compress(raw))
            (folder/(key+'.json')).write_text(json.dumps(dict(url=self.old,sha256=sha(raw))))
            with patch('best_v2_mirrors.original',side_effect=DataUnavailable('NO_VERIFIED_ISSUER_MIRROR')),patch('requests.Session.get',side_effect=AssertionError('network forbidden')):
                text,meta=material_original(dict(self.row,_cache=root),self.filing,'2026-11-09')
            self.assertEqual(text,raw.decode());self.assertEqual(meta['url'],self.old)
    def test_only_canonical_is_requested_when_cache_missing_and_403_stays_blocking(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('best_v2_mirrors.original',side_effect=DataUnavailable('NO_VERIFIED_ISSUER_MIRROR')),patch('requests.Session.get') as get:
                get.return_value.status_code=403
                with self.assertRaisesRegex(DataUnavailable,'SEC_HTTP_403'):
                    material_original(dict(self.row,_cache=root),self.filing,'2026-11-09')
                self.assertEqual(get.call_args.args[0],self.good);self.assertEqual(get.call_count,1)
