import unittest
import pandas as pd
import run_root_cause_data_audit as audit

class AuditTests(unittest.TestCase):
    def test_peak_excludes_exit_day_after_open_and_links_costs(self):
        positions=pd.DataFrame([{'SignalDate':'2025-01-31','Ticker':'TEST','TopN':1,'EntryDate':'2025-02-03','ExitDate':'2025-02-05','EntryPrice_USD':10.,'ExitPrice_USD':8.,'GrossReturn_pct':-20.,'ExitReason':'REBALANCE'}])
        results=pd.DataFrame([{'SignalDate':'2025-01-31','NetReturn_pct':-20.3,'GrossReturn_pct':-20.,'RiskRegime':'RISK_ON'}])
        run={'positions':positions,'results':results,'metrics':{'TotalReturn_pct':-20.3}}
        cache={'2025-02-03':{'TEST':{'open':10.,'high':17.,'close':11.}},'2025-02-04':{'TEST':{'open':11.,'high':12.,'close':9.}},'2025-02-05':{'TEST':{'open':8.,'high':30.,'close':25.}}}
        enriched,summary=audit.linked_positions(run,cache)
        self.assertAlmostEqual(enriched.iloc[0].MaxIntradayReturn_pct,70.)
        self.assertEqual(summary['IntradayAtLeast100'],0)
        self.assertAlmostEqual(summary['Residual_pp'],0.)

    def test_unchanged_equal_weight_holdings_do_not_require_full_rebalance(self):
        positions=pd.DataFrame([{'SignalDate':s,'Ticker':'TEST','TopN':1,'GrossReturn_pct':0.,'ExitReason':'REBALANCE'} for s in ['2025-01-31','2025-02-28']])
        results=pd.DataFrame([{'SignalDate':s,'GrossReturn_pct':0.,'RiskRegime':'RISK_ON'} for s in ['2025-01-31','2025-02-28']])
        records,summary=audit.turnover({'positions':positions,'results':results})
        self.assertEqual(records[1]['RebalanceBuy_pct'],0.)
        self.assertEqual(records[1]['RebalanceSell_pct'],0.)
        self.assertEqual(summary['MinimumRebalanceTwoSidedSum_pct'],200.)

if __name__=='__main__':
    unittest.main()
