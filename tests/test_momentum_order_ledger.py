import math
import unittest

from momentum_order_ledger import Costs, ZERO, simulate


def fixture(two=True):
    periods=[dict(SignalDate="2024-01-31",EntryDate="2024-02-01",ExitDate="2024-03-01")]
    if two:
        periods.append(dict(SignalDate="2024-02-29",EntryDate="2024-03-01",ExitDate="2024-04-01"))
    days=["2024-02-01","2024-02-02","2024-03-01","2024-03-02","2024-04-01"]
    lots=[]
    marks={}
    for i,p in enumerate(periods):
        key=str(i)
        lots.append({**p,"PlannedExitDate":p["ExitDate"],"Ticker":"AAA","Weight":1.,
                     "EntryPrice_USD":100.,"ExitPrice_USD":100.,"UnitPath":key,
                     "ExitReason":"REBALANCE","CorporateAction":""})
        marks[key]={d:100. for d in days if p["EntryDate"]<=d<p["ExitDate"]}
    return periods,lots,marks,days


class OrderLedgerTests(unittest.TestCase):
    def test_fee_breakdown_both_sides_and_minimum(self):
        fee=Costs("test",.0025,1.,.0025,.0005,.0005)
        self.assertAlmostEqual(fee.charge(100)["total"],1.35)
        self.assertAlmostEqual(fee.charge(1000)["total"],6.)
        self.assertEqual(fee.charge(0)["total"],0.)
        self.assertAlmostEqual(fee.charge(100,settlement=True)["total"],.25)
        for value in (-1.,float("nan"),float("inf")):
            with self.assertRaises(ValueError): fee.charge(value)

    def test_unchanged_holdings_do_not_sell_and_rebuy(self):
        p,l,m,d=fixture()
        fee=Costs("one_percent",.01,0.,0.,0.,0.)
        out=simulate(p,l,m,d,fee,1000.)
        self.assertEqual([o["Side"] for o in out["orders"]],["BUY","SELL"])
        self.assertAlmostEqual(out["summary"]["final_usd"],1000*.99/1.01,places=7)
        self.assertTrue(all(r["Cash_USD"]>=-1e-6 for r in out["nav"]))

    def test_zero_cost_gross_compounding_with_drift_and_rebalance(self):
        p,l,m,d=fixture()
        l[0]["ExitPrice_USD"]=120.
        l[1]["EntryPrice_USD"]=120.
        l[1]["ExitPrice_USD"]=90.
        m['1']={day:110. for day in m['1']}
        out=simulate(p,l,m,d,ZERO,1000.)
        self.assertAlmostEqual(out["summary"]["final_usd"],900.)
        self.assertAlmostEqual(out["results"][0]["NetReturn_pct"],20.)
        self.assertAlmostEqual(out["results"][1]["NetReturn_pct"],-25.)

    def test_minimum_fees_funded_before_fractional_purchase(self):
        p,l,m,d=fixture(False)
        fee=Costs("flat",0.,1.,0.,0.,0.)
        out=simulate(p,l,m,d,fee,100.)
        self.assertAlmostEqual(out["allocations"][0]["Quantity"],.99)
        self.assertAlmostEqual(out["summary"]["final_usd"],98.)
        self.assertEqual(out["summary"]["total_cost_usd"]["commission"],2.)

    def test_stop_exit_charges_on_sale_date_and_cannot_net_next_entry(self):
        p,l,m,d=fixture()
        l[0].update(ExitDate="2024-02-02",ExitReason="STOP_LOSS",ExitPrice_USD=80.)
        out=simulate(p,l,m,d,Costs("flat",0.,1.,0.,0.,0.),1000.)
        self.assertEqual([o["Date"] for o in out["orders"]],
                         ["2024-02-01","2024-02-02","2024-03-01","2024-04-01"])
        self.assertEqual(out["nav"][1]["Holdings_USD"],0.)
        self.assertAlmostEqual(out["nav"][1]["Cash_USD"],999*.8-1)

    def test_cash_merger_is_fx_settlement_without_market_commission(self):
        p,l,m,d=fixture(False)
        l[0].update(ExitReason="CASH_MERGER",CorporateAction="CASH_MERGER")
        out=simulate(p,l,m,d,Costs("test",.01,1.,.0025,.001,.001),1000.)
        cash=out["orders"][-1]
        self.assertEqual(cash["Side"],"CASH_SETTLEMENT")
        self.assertEqual(cash["commission_USD"],0.)
        self.assertAlmostEqual(cash["total_USD"],cash["Notional"]*.0025)

    def test_empty_period_has_no_order_cost_and_preserves_cash(self):
        p,l,m,d=fixture(False)
        out=simulate(p,[],{},d,Costs("test"),1000.)
        self.assertEqual(out["orders"],[])
        self.assertEqual(out["summary"]["final_usd"],1000.)

    def test_carry_with_different_price_units_is_rejected(self):
        p,l,m,d=fixture()
        l[1]["EntryPrice_USD"]=50.
        with self.assertRaisesRegex(RuntimeError,"different share-price units"):
            simulate(p,l,m,d,ZERO,1000.)

    def test_partial_target_rebalance_only_changes_required_quantity(self):
        p,l,m,d=fixture()
        l[0]["Weight"]=.5
        l[1]["Weight"]=.25
        out=simulate(p,l,m,d,ZERO,1000.)
        self.assertEqual([o["Notional"] for o in out["orders"]],[500.,250.,250.])
        self.assertEqual(out["summary"]["final_usd"],1000.)


if __name__=="__main__": unittest.main()
