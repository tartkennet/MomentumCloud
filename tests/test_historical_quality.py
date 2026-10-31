import copy,unittest
from datetime import datetime
from historical_quality_facts import parse_historical,available_at
from historical_quality_audit import audit_fundamental
from quality_fundamentals import parse_original
from quality_sources import DataUnavailable
from test_quality_earnings import fixture

class HistoricalClockTests(unittest.TestCase):
    def receipt(self):
        raw,r=fixture();r['filing']['acceptance_datetime']='20260731173000';r['observed_at']='2026-10-31T12:00:00+00:00';return raw,r
    def test_actual_retrieval_is_never_backdated(self):
        raw,r=self.receipt();f=parse_historical(raw,r,'123','2026-08-03T08:17:00+00:00')
        self.assertEqual(f['observed_at'],r['observed_at']);self.assertEqual(f['available_at'],'2026-07-31T21:30:00+00:00');self.assertTrue(f['qualified']);self.assertEqual(audit_fundamental(raw,r,f,'123','2026-08-03T08:17:00+00:00')['status'],'PASS')
        with self.assertRaises(DataUnavailable):parse_original(raw,r,'123','2026-08-03T08:17:00+00:00')
    def test_after_close_report_cannot_enter_earlier_selection(self):
        raw,r=self.receipt()
        with self.assertRaises(DataUnavailable):parse_historical(raw,r,'123','2026-07-31T20:00:00+00:00')
        r['filing'].pop('acceptance_datetime')
        with self.assertRaises(DataUnavailable):parse_historical(raw,r,'123','2026-08-03T08:17:00+00:00')
    def test_new_york_dst_and_later_filing_bound(self):
        _,r=self.receipt();self.assertEqual(available_at(r['filing']).hour,21)
        r['filing'].update(acceptance_datetime='20261102173000',filing_date='20261103')
        self.assertEqual(available_at(r['filing']).isoformat(),'2026-11-03T05:00:00+00:00')
    def test_same_economic_fields_as_frozen_parser(self):
        raw,r=fixture();r['filing']['acceptance_datetime']='20260731070000'
        a=parse_original(raw,r,'123','2026-08-01T00:00:00+00:00');b=parse_historical(raw,r,'123','2026-08-01T00:00:00+00:00')
        for key in ('current','prior','metrics','checks','qualified','concepts','period','prior_period'):self.assertEqual(a[key],b[key])

if __name__=='__main__':unittest.main()
