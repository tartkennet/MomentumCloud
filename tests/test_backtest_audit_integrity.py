import unittest
from unittest.mock import patch
import backtest_momentum_v3 as engine
from momentum_master_v3 import PolygonClient
import run_v4_ablation_and_simple_candidate as existing

class IntegrityTests(unittest.TestCase):
    def test_future_reverse_split_cannot_make_penny_stock_pass_price_floor(self):
        row={'close':30.88,'volume':1_000_000,'raw_signal_close':3.86}
        history=[(str(i),{'KULR':row}) for i in range(253)]
        self.assertEqual(existing.simple_builder(['KULR'],{'KULR':row},history,None,None),[])

    def test_future_gap_cannot_exclude_earlier_signal(self):
        observations={'TEST':['2025-01-02: open 10 vs prior close 20, split-like ratio 2']}
        self.assertNotIn('TEST',engine.data_quality_exclusions_asof(observations,'2023-02-28'))
        self.assertIn('TEST',engine.data_quality_exclusions_asof(observations,'2025-01-31'))

    def test_cir_uses_verified_cash_instead_of_price_years_later(self):
        cache={'2023-10-02':{'CIR':{'open':55.74,'close':55.74}},'2023-11-01':{},'2026-07-07':{'CIR':{'open':23.76,'close':23.76}}}
        day,row,action=engine.resolve_exit_execution(cache,sorted(cache),'CIR','2023-11-01','2023-10-02','2026-07-07')
        self.assertEqual(day,'2023-10-18')
        self.assertEqual(row['close'],56.)
        self.assertEqual(action['reason'],'CASH_MERGER')

    def test_split_pagination_collects_later_pages_without_reusing_api_key(self):
        client=PolygonClient('not-a-real-key')
        pages=[{'results':[{'ticker':'FIRST'}],'next_url':'https://api.polygon.io/stocks/v1/splits?cursor=two&apiKey=ignored'}, {'results':[{'ticker':'SECOND'}]}]
        with patch.object(client,'_get',side_effect=pages) as fetch:
            events=client.fetch_recent_splits('2023-01-01','2026-01-01')
        self.assertEqual([e['ticker'] for e in events],['FIRST','SECOND'])
        self.assertEqual(fetch.call_args_list[1].args,('/stocks/v1/splits',{'cursor':'two'}))

if __name__=='__main__':
    unittest.main()
