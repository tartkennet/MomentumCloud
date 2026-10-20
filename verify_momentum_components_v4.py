"""Independent standard-library audit of funded cash, fills and daily equity."""
import gzip
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

OUT=Path("audit_evidence/components_v4_20261020")


def near(a,b,label):
    if not math.isclose(float(a),float(b),rel_tol=1e-9,abs_tol=1e-6):
        raise AssertionError(f"{label}: {a} != {b}")


def read(name):
    return json.loads((OUT/name).read_text())


def main():
    comparison=read("comparison.json")
    if not comparison["status"].startswith("COMPLETE_"):
        raise AssertionError("Incomplete factorial")
    for name,digest in comparison["source_sha256"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
            raise AssertionError("Source changed after comparison: "+name)
    periods=read("periods.json")
    days=read("days.json")
    marks=read("unit_marks.json")
    definitions={**read("variant_lots.json"),**read("benchmark_lots.json")}
    factors=read("variant_factors.json")
    if len(factors)!=16 or len(periods)!=43 or comparison["blocked_variants"]:
        raise AssertionError("Factorial coverage")
    checks={}
    for path in sorted(OUT.glob("*_ledger.json.gz")):
        name,scenario,capital=path.name.removesuffix("_ledger.json.gz").rsplit("__",2)
        ledger=json.loads(gzip.decompress(path.read_bytes()))
        summary=ledger["summary"]
        costs=summary["cost_configuration"]
        if costs["name"]!=scenario:
            raise AssertionError("Mislabeled fee scenario")
        current_periods=periods if name!="spy_buy_hold" else [
            {"SignalDate":periods[0]["SignalDate"],"EntryDate":periods[0]["EntryDate"],"ExitDate":periods[-1]["ExitDate"]}]
        if len(ledger["results"])!=len(current_periods):
            raise AssertionError("Missing ledger month")
        lots={(p["SignalDate"],p["Ticker"]):p for p in definitions[name]}
        alloc=defaultdict(dict)
        for a in ledger["allocations"]:
            key=(a["SignalDate"],a["Ticker"])
            base=lots[key]
            near(a["Quantity"]*base["EntryPrice_USD"],a["AllocationBudget_USD"]*base["Weight"],"Funded quantity")
            if a["UnitPath"]!=base["UnitPath"]:
                raise AssertionError("Price path changed")
            alloc[a["SignalDate"]][a["Ticker"]]={**base,**a}
        if sum(len(v) for v in alloc.values())!=len(lots):
            raise AssertionError("A selected lot disappeared")
        orders_by_signal=defaultdict(list)
        fees_by_component=defaultdict(float)
        for order in ledger["orders"]:
            notional=order["Notional"]
            near(notional,order["Price"]*order["Quantity"],"Order notional")
            if notional<=1e-8 or order["Side"] not in ("BUY","SELL","CASH_SETTLEMENT"):
                raise AssertionError("Invalid fill")
            settlement=order["Side"]=="CASH_SETTLEMENT"
            commission=0. if settlement else max(costs["minimum_usd"],costs["commission"]*notional)
            expected={"commission":commission,"fx":costs["fx"]*notional,
                      "half_spread":0. if settlement else costs["half_spread"]*notional,
                      "slippage":0. if settlement else costs["slippage"]*notional}
            near(order["total_USD"],sum(expected.values()),"Total per-order charge")
            for key,value in expected.items():
                near(order[key+"_USD"],value,"Per-order "+key)
                fees_by_component[key]+=value
            orders_by_signal[order["SignalDate"]].append(order)
        cash=float(capital)
        carry={}
        nav_by_signal=defaultdict(list)
        for row in ledger["nav"]: nav_by_signal[row["SignalDate"]].append(row)
        for i,period in enumerate(current_periods):
            signal,entry,end=period["SignalDate"],period["EntryDate"],period["ExitDate"]
            group=alloc[signal]
            pre_nav=cash+sum(p["Quantity"]*p["ExitPrice_USD"] for p in carry.values())
            monthly=ledger["results"][i]
            near(monthly["PreTradeNAV_USD"],pre_nav,"Opening equity")
            if monthly["SignalDate"]!=signal:
                raise AssertionError("Period chronology")
            for lot in group.values():
                near(lot["PreTradeNAV_USD"],pre_nav,"Allocation-time capital")
            net_orders={}
            for order in orders_by_signal[signal]:
                if not entry<=order["Date"]<=end:
                    raise AssertionError("Fee outside actual month")
                if order["Reason"]=="NET_REBALANCE":
                    if order["Date"]!=entry or order["Ticker"] in net_orders:
                        raise AssertionError("Unnetted duplicate boundary order")
                    net_orders[order["Ticker"]]=order
            for ticker in set(carry)|set(group):
                old_q=carry.get(ticker,{}).get("Quantity",0.)
                new_q=group.get(ticker,{}).get("Quantity",0.)
                expected_delta=new_q-old_q
                price=(group[ticker]["EntryPrice_USD"] if ticker in group else carry[ticker]["ExitPrice_USD"])
                order=net_orders.get(ticker)
                if abs(expected_delta*price)<=1e-8:
                    if order: raise AssertionError("Fictional retained-share transaction")
                else:
                    if order is None: raise AssertionError("Missing net rebalance order")
                    near(order["Quantity"],abs(expected_delta),"Actual net quantity")
                    near(order["Price"],price,"Boundary opening price")
                    if order["Side"]!=("BUY" if expected_delta>0 else "SELL"):
                        raise AssertionError("Wrong trade direction")
            by_day=defaultdict(list)
            for order in orders_by_signal[signal]: by_day[order["Date"]].append(order)
            terminal=0.
            rows=nav_by_signal[signal]
            if [r["Date"] for r in rows]!=[d for d in days if entry<=d<=end]:
                raise AssertionError("Missing daily NAV date")
            for row in rows:
                day=row["Date"]
                for order in by_day[day]:
                    if order["Reason"]!="NET_REBALANCE":
                        lot=group[order["Ticker"]]
                        near(order["Quantity"],lot["Quantity"],"Full exit quantity")
                        near(order["Price"],lot["ExitPrice_USD"],"Actual exit price")
                        if order["Date"]!=lot["ExitDate"] or lot["CarryAtEnd"]:
                            raise AssertionError("Incorrect or fictional exit date")
                        if (order["Side"]=="CASH_SETTLEMENT")!=(lot["ExitReason"]=="CASH_MERGER"):
                            raise AssertionError("Merger consideration treated as stock trade")
                    cash+=( -order["Notional"] if order["Side"]=="BUY" else order["Notional"] )-order["total_USD"]
                holdings=0.
                for lot in group.values():
                    if day>lot["ExitDate"] or day==lot["ExitDate"] and not lot["CarryAtEnd"]:
                        continue
                    price=lot["ExitPrice_USD"] if day==lot["ExitDate"] else marks[lot["UnitPath"]][day]
                    holdings+=lot["Quantity"]*price
                if cash < -1e-5:
                    raise AssertionError("Borrowed cash after the execution batch")
                near(row["Cash_USD"],cash,"Daily independent cash")
                near(row["Holdings_USD"],holdings,"Daily independent holdings")
                terminal=cash+holdings
                near(row["Equity_USD"],terminal,"Independent daily equity")
            near(monthly["Equity_USD"],terminal,"Monthly terminal equity")
            near(monthly["NetReturn_pct"],(terminal/pre_nav-1)*100,"Monthly net return")
            near(monthly["Cost_USD"],sum(o["total_USD"] for o in orders_by_signal[signal]),"Monthly fee sum")
            carry={t:p for t,p in group.items() if p["CarryAtEnd"]}
        if carry:
            raise AssertionError("Final portfolio not liquidated")
        near(summary["final_usd"],cash,"Final cash balance")
        near(summary["net_return_pct"],(cash/float(capital)-1)*100,"Net return")
        for key,total in fees_by_component.items(): near(summary["total_cost_usd"][key],total,"Fee total "+key)
        near(summary["total_cost_usd"]["total"],sum(fees_by_component.values()),"All fees")
        peak,dd=float(capital),0.
        for row in ledger["nav"]:
            peak=max(peak,row["Equity_USD"])
            dd=min(dd,(row["Equity_USD"]/peak-1)*100)
        near(summary["daily_drawdown_pct"],dd,"Daily drawdown")
        checks[path.name]={"status":"PASS","orders":len(ledger["orders"]),"months":len(current_periods),
                           "daily_marks":len(ledger["nav"]),"net_return_pct":summary["net_return_pct"]}
    expected=16*6+16*8+8
    if len(checks)!=expected:
        raise AssertionError(f"Ledger coverage {len(checks)} != {expected}")
    result={"status":"PASS_INDEPENDENT_ORDER_CASH_AND_NAV_RECONCILIATION","ledgers":len(checks),
            "checks":checks,"limitation":"Accounting and frozen-path validation, not independently verified market fills or unseen performance."}
    (OUT/"independent_check.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="checks"},indent=2))


if __name__=="__main__": main()
