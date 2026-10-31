import unittest
from types import SimpleNamespace
from dataclasses import replace
from momentum_core import CONFIG
from attribute_momentum10_v3 import attribute_account


class AttributionTests(unittest.TestCase):
    def test_ticker_pnl_includes_actual_fill_fee_and_marks(self):
        fee=1.4
        source=SimpleNamespace(splits=[],dividends=[])
        data=SimpleNamespace(source=source,cash_actions={},stock_actions={},distributions=[],halt_marks={},
            history=lambda d,t,n:[],bars=lambda d:{'ABC':[100,90 if d=='2024-01-03' else 100,100000]})
        s=SimpleNamespace(trades=[dict(date='2024-01-03',signal_date='2024-01-02',ticker='ABC',side='BUY',quantity=1,price=100,fee=fee)],
            equity=[dict(date='2024-01-02',nav=1000,cash=1000,receivables=0,fees_cumulative=0,stock_value=0,positions=0),
                    dict(date='2024-01-03',nav=988.6,cash=898.6,receivables=0,fees_cumulative=fee,stock_value=90,positions=1)],
            shares={'ABC':1},cash=898.6,fx_payments=[])
        a=attribute_account(data,replace(CONFIG,initial_cash=1000),s,lambda d,c:1.)
        self.assertEqual(a['status'],'PASS');self.assertAlmostEqual(a['drawdown_contribution_usd'][0][1],-11.4)
        self.assertEqual(a['missing_trend_stock_days'],1)
