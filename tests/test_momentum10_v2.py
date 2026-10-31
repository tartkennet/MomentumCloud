import math
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from momentum_core import CONFIG
from research_momentum10_v2 import RetentionLedger


def rows():
    return [dict(ticker='S'+str(i),raw_price=10,weight=.1,daily_volatility=.02,
                 return_1m=.1,return_3m=.1,risk_normalized_score=20-i) for i in range(10)]


def market(opening=10,close=10):
    return SimpleNamespace(splits=[],dividends=[],cash_actions={},stock_actions={},distributions=[],
        bars=lambda day:{r['ticker']:[opening,close,100000] for r in rows()})


class RetentionTests(unittest.TestCase):
    def basket(self):
        return {'signal_date':'2026-10-29','signal_nav':1000,'exposure':1.,'targets':rows(),'suppressed':[]}

    def test_continuing_ten_names_have_no_trades_or_fees(self):
        s=RetentionLedger(cash=50,shares={r['ticker']:3 for r in rows()},pending=self.basket())
        before=dict(s.shares)
        s.execute_open(market(),'2026-10-30')
        self.assertEqual(s.shares,before);self.assertEqual(s.cash,50);self.assertFalse(s.trades)

    def test_only_replaced_members_trade(self):
        p=self.basket();p['targets'][0]['ticker']='NEW'
        data=market();original=data.bars
        data.bars=lambda day:dict(original(day),NEW=[10,10,100000])
        s=RetentionLedger(cash=50,shares={r['ticker']:2 for r in rows()},pending=p)
        s.execute_open(data,'2026-10-30')
        self.assertEqual({t['ticker'] for t in s.trades},{'S0','NEW'})
        self.assertTrue(all(s.shares['S'+str(i)]==2 for i in range(1,10)))
        self.assertGreaterEqual(s.cash,0)

    def test_unfunded_basket_cannot_partially_sell(self):
        s=RetentionLedger(cash=5,pending=self.basket())
        s.execute_open(market(),'2026-10-30')
        self.assertFalse(s.trades);self.assertEqual(s.cash,5)
        self.assertEqual(s.blocked[0]['reason'],'MINIMUM_COMPLETE_BASKET_UNFUNDED')

    def test_gap_stop_uses_observed_next_open_not_threshold(self):
        s=RetentionLedger(cash=100,shares={'S0':2},stop_mode='fixed10',interval=3,
            references={'S0':dict(reference=100,level=90,distance=.1,basis_signal='2026-10-01')},
            previous_risk=True,seen_month='2026-10',last_date='2026-10-29')
        with patch('momentum_core.risk_on',return_value=True):
            s.step_stocks(market(100,89),'2026-10-30',CONFIG,{})
            self.assertFalse(s.trades)
            s.step_stocks(market(70,72),'2026-11-02',CONFIG,{})
        self.assertEqual(s.trades[0]['price'],70)
        self.assertEqual(s.trades[0]['signal_date'],'2026-10-30')
        self.assertNotIn('S0',s.shares);self.assertIn('S0',s.blacklist)

    def test_split_and_dividend_adjust_stop_without_fake_cash(self):
        s=RetentionLedger(cash=0,shares={'S0':2},stop_mode='fixed10',
            references={'S0':dict(reference=100,level=90,distance=.1)})
        data=market()
        data.splits=[dict(ticker='S0',execution_date='2026-10-30',split_from=1,split_to=2)]
        data.dividends=[dict(ticker='S0',ex_dividend_date='2026-10-30',cash_amount=2,currency='USD',pay_date='2026-11-02')]
        s.events_before_open(data,'2026-10-30')
        self.assertEqual(s.shares['S0'],4);self.assertEqual(s.references['S0']['reference'],50)
        self.assertEqual(s.references['S0']['level'],43);self.assertEqual(s.cash,0)
        self.assertEqual(s.receivables[0]['amount'],8)

    def test_volatility_stop_uses_precommitted_signal_sigma(self):
        s=RetentionLedger(cash=1000,stop_mode='vol',pending=self.basket())
        s.execute_open(market(10,5),'2026-10-30')
        self.assertAlmostEqual(s.references['S0']['level'],10*(1-2*.02*math.sqrt(21)))

    def test_calendar_is_anchored_not_time_since_last_trade(self):
        s=RetentionLedger(interval=3,previous_risk=True,seen_month='2026-09',last_date='2026-09-30',cash=1000)
        with patch('momentum_core.risk_on',return_value=True),patch('research_stocks10.population',return_value=rows()):
            s.step_stocks(market(),'2026-10-01',CONFIG,{})
            self.assertTrue(s.decisions[-1]['ordinary'])
            s.step_stocks(market(),'2026-11-02',CONFIG,{})
            self.assertFalse(s.decisions[-1]['ordinary'])

    def test_same_close_stop_cannot_be_rebought_by_ordinary_selection(self):
        s=RetentionLedger(interval=3,stop_mode='fixed10',cash=1000,shares={'S0':1},
            previous_risk=True,seen_month='2026-09',last_date='2026-09-30',
            references={'S0':dict(reference=100,level=90,distance=.1)})
        with patch('momentum_core.risk_on',return_value=True),patch('research_stocks10.population',return_value=rows()):
            s.step_stocks(market(10,10),'2026-10-01',CONFIG,{})
        self.assertEqual(s.pending['suppressed'],['S0'])
        s.execute_open(market(),'2026-10-02')
        self.assertFalse(any(t['ticker']=='S0' and t['side']=='BUY' for t in s.trades))
        self.assertEqual(len(s.shares),9)

    def test_missing_sell_open_keeps_unfilled_order_and_holding(self):
        s=RetentionLedger(cash=10,shares={'GONE':2},sell_queue={'GONE':{'signal_date':'2026-10-29','reason':'STOP_fixed10'}})
        s.execute_open(market(),'2026-10-30')
        self.assertEqual(s.shares['GONE'],2);self.assertIn('GONE',s.sell_queue)
        self.assertFalse(s.trades)

    def test_daily_regime_exit_does_not_wait_for_quarterly_selection(self):
        s=RetentionLedger(cash=10,shares={'S0':2},interval=3,previous_risk=True,
                          seen_month='2026-10',last_date='2026-10-15')
        with patch('momentum_core.risk_on',return_value=False):
            s.step_stocks(market(),'2026-10-16',CONFIG,{})
            self.assertFalse(s.trades)
            s.step_stocks(market(8,8),'2026-10-19',CONFIG,{})
        self.assertEqual(s.trades[0]['reason'],'RISK_OFF')
        self.assertEqual(s.trades[0]['price'],8)
        self.assertFalse(s.shares)

    def test_new_buy_does_not_erase_existing_fractional_cost_reference(self):
        s=RetentionLedger(cash=1000,shares={'S0':.5},stop_mode='fixed10',pending=self.basket(),
                         references={'S0':dict(reference=100,level=90,distance=.1)})
        s.execute_open(market(),'2026-10-30')
        q=next(t['quantity'] for t in s.trades if t['ticker']=='S0')
        self.assertAlmostEqual(s.references['S0']['reference'],(50+q*10)/(.5+q))
        self.assertAlmostEqual(s.references['S0']['level'],(45+q*9)/(.5+q))


if __name__=='__main__':unittest.main()
