import json
import tempfile
import unittest
from pathlib import Path
from attribute_benchmark_core import attribute


class BenchmarkCoreAttributionTests(unittest.TestCase):
    def test_buy_cost_price_loss_and_dividend_accrual_have_hand_calculated_pnl(self):
        days=['2024-01-02','2024-01-03','2024-01-04','2024-01-05']
        b={'shares':{'SPY':10},'trades':[{'side':'BUY','quantity':10}],
           'equity':[{'date':d,'nav':n,'stock_value':s} for d,n,s in zip(days,[1000,1000,990,995],[0,100,90,90])]}
        s={'shares':{'SPY':4},'trades':[{'date':days[1],'ticker':'SPY','side':'BUY','quantity':4,'price':10,'fee':.4}],
           'targets':[{'date':days[0],'risk_on':True},{'date':days[2],'risk_on':False}],
           'equity':[{'date':d,'nav':n} for d,n in zip(days,[1000,999.6,995.6,997.6])]}
        audit={'status':'PASS','maximum_drawdown_interval':{'peak_date':days[0],'trough_date':days[2],
                                                         'peak_nav_usd':1000,'trough_nav_usd':995.6}}
        with tempfile.TemporaryDirectory() as name:
            root=Path(name)
            (root/'checkpoint.json').write_text(json.dumps({'strategy':s,'benchmark':b}))
            (root/'Momentum_core_accounting_audit.json').write_text(json.dumps(audit))
            result=attribute(root)
        self.assertAlmostEqual(result['overall_core_pnl_usd'],-2.4)
        self.assertAlmostEqual(result['drawdown_core_pnl_usd'],-4.4)
        self.assertAlmostEqual(result['drawdown_other_pnl_usd'],0)
        self.assertEqual(result['risk_off_sessions_in_episode'],1)
