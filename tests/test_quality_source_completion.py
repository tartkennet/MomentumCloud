import gzip
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from supplement_quality_sources import SEC,header,instance,review,sha,submissions
from quality_sources import DataUnavailable
from test_quality_earnings import fixture


class SECCompletionTests(unittest.TestCase):
    accession='0000000123-26-000001'

    def submission(self,accepted='20260731070000',form='10-Q'):
        raw,_=fixture()
        return (f'<SEC-HEADER>\nACCESSION NUMBER: {self.accession}\n'
                f'<ACCEPTANCE-DATETIME>{accepted}\nCONFORMED SUBMISSION TYPE: {form}\n'
                'FILED AS OF DATE: 20260731\nCONFORMED PERIOD OF REPORT: 20260630\n'
                'FILER:\n CENTRAL INDEX KEY: 123\n STANDARD INDUSTRIAL CLASSIFICATION: TEST [3511]\n'
                '</SEC-HEADER>\n<DOCUMENT>\n<FILENAME>original.xml\n<XML>\n<?xml version="1.0"?>').encode()+raw+b'\n</XML>\n</DOCUMENT>'

    def check_review(self,raw,form='10-Q'):
        class Client:
            def get(self,url):
                return raw,dict(url=url,sha256=sha(raw),observed_at='2026-11-01T09:00:00+00:00')
        choices=[dict(accessionNumber=self.accession,filingDate='2026-07-31',form=form)]
        with patch('supplement_quality_sources.submissions',return_value=(choices,{})):
            return review(dict(ticker='TEST',cik='123',resolved=False,reason='MISSING_ACCEPTANCE_TIMESTAMP'),'2026-08-03',Client())

    def test_original_header_and_attachment_reproduce_audited_facts(self):
        result=self.check_review(self.submission())
        self.assertTrue(result['resolved'])
        self.assertEqual(result['audit']['status'],'PASS')
        self.assertEqual(result['fundamental']['observed_at'],'2026-11-01T09:00:00+00:00')
        self.assertEqual(result['fundamental']['available_at'],'2026-07-31T11:00:00+00:00')

    def test_future_original_and_known_amendment_cannot_resolve(self):
        for raw,form in [(self.submission('20260803100000'),'10-Q'),(self.submission(form='10-Q/A'),'10-Q/A')]:
            self.assertFalse(self.check_review(raw,form)['resolved'])

    def test_wrong_filer_or_duplicate_attachment_is_rejected(self):
        raw=self.submission()
        with self.assertRaises(DataUnavailable):header(raw,self.accession,'999')
        with self.assertRaises(DataUnavailable):instance(raw+raw)

    def test_offline_receipt_rejects_changed_original_and_cache_miss(self):
        with tempfile.TemporaryDirectory() as folder:
            client=SEC(folder,offline=True);url='https://www.sec.gov/Archives/test.txt'
            with self.assertRaisesRegex(DataUnavailable,'UNCACHED'):client.get(url)
            key=sha(url.encode());root=Path(folder)
            (root/(key+'.gz')).write_bytes(gzip.compress(b'changed'))
            (root/(key+'.json')).write_text(json.dumps(dict(url=url,sha256=sha(b'original'))))
            with self.assertRaises(AssertionError):client.get(url)

    def test_discovery_checks_older_archive_when_recent_has_no_eligible_original(self):
        group=dict(form=['10-Q'],filingDate=['2026-08-01'],accessionNumber=[self.accession])
        class Client:
            def get(self,url):
                d=dict(filings=dict(recent=dict(form=['20-F'],filingDate=['2026-09-01']),files=[dict(name='old.json',filingFrom='2020-01-01',filingTo='2026-08-01')])) if url.endswith('CIK0000000123.json') else group
                return json.dumps(d).encode(),{}
        rows,_=submissions(Client(),'123','2026-08-03')
        self.assertEqual(rows[0]['accessionNumber'],self.accession)


if __name__=='__main__':unittest.main()
