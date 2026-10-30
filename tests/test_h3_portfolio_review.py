import unittest
from audit_h3_portfolio import period_return, months_before, dedupe_events

class ReadonlyReviewTests(unittest.TestCase):
    def test_split_and_dividend_do_not_manufacture_a_return(self):
        p={'2026-09-30':100.,'2026-10-01':50.,'2026-10-30':55.}
        e=[dict(ticker='X',execution_date='2026-10-01',split_from=1,split_to=2)]
        d=[dict(ticker='X',ex_dividend_date='2026-10-30',cash_amount=1,currency='USD')]
        r=period_return(p,e,d,'X','2026-10-30',1)
        self.assertAlmostEqual(r['price_return_pct'],10.);self.assertAlmostEqual(r['total_return_pct'],12.)
        self.assertEqual(months_before('2026-03-31',1),'2026-02-28')
    def test_missing_history_is_not_reported_as_zero_return(self):
        self.assertEqual(period_return({'2026-10-30':55.},[],[],'X','2026-10-30',12)['status'],'MISSING')
    def test_event_metadata_can_differ_but_economic_terms_cannot(self):
        e=dict(id='same',ticker='X',execution_date='2026-10-01',split_from=1,split_to=2)
        self.assertEqual(len(dedupe_events([e,dict(e,updated_at='later')],'split')),1)
        with self.assertRaises(ValueError):dedupe_events([e,dict(e,split_to=3)],'split')
if __name__=='__main__':unittest.main()
