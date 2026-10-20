"""Fixed component factorial on frozen inputs; no tuning or online market data."""
from dataclasses import asdict
import gzip
import hashlib
import itertools
import json
import logging
from pathlib import Path
import traceback

import numpy as np
import pandas as pd

import momentum_selection_v3 as selection
import risk_managed_momentum as risk
import run_risk_managed_research as old_execution
from momentum_order_ledger import simulate, SCENARIOS, ZERO
from run_momentum_selection_v3 import load_raw_dollars
from selection_v3_execution import install_action, documented_unfilled_entry, install_disclosed_stale_marks

OUT = Path("audit_evidence/components_v4_20261020")
V3 = Path("audit_evidence/selection_v3_20261020")
SPEC = Path("docs/momentum_components_v4_spec.md")
FACTORS = list(itertools.product((False, True), repeat=3))  # weights, stop, market


def save(name, value):
    old_execution.save_json(OUT / name, value)


def save_ledger(name, value):
    # Lot definitions/marks are stored once; retain every actual quantity,
    # order, fee, daily cash value and monthly endpoint for reconciliation.
    compact = {**value, "allocations": [{key: row[key] for key in (
        "SignalDate", "Ticker", "Quantity", "AllocationBudget_USD", "PreTradeNAV_USD", "CarryAtEnd", "UnitPath")}
        for row in value["allocations"]]}
    data = json.dumps(compact, separators=(",",":"), allow_nan=False).encode()
    (OUT/(name+"_ledger.json.gz")).write_bytes(gzip.compress(data, mtime=0))


def install_additional_actions(engine):
    engine.CASH_CORPORATE_ACTIONS["CMRX"] = {
        "effective_date": "2025-04-21", "cash_per_share": 8.55,
        "reason": "CASH_MERGER", "execution": "cash-settlement",
        "source": "https://www.sec.gov/Archives/edgar/data/1117480/000119312525087237/d942664d8k.htm"}


def label(weights, stop, market):
    return "W"*weights + "S"*stop + "M"*market or "equal_reference"


def execute_path(engine, cache, days, splits, candidate, period, stop, market_exit):
    if stop:
        return old_execution.execute_lot(engine, cache, days, splits, candidate, period, 1., market_exit)
    entry, planned, ticker = period.EntryDate, period.ExitDate, candidate.ticker
    entry_price = old_execution.actual_price(engine, cache, days, splits, ticker, entry, candidate.price)
    target, reason, trigger = market_exit or planned, "MARKET_RISK_OFF" if market_exit else "REBALANCE", ""
    if market_exit:
        trigger = days[days.index(market_exit)-1]
    cash_action = engine.CASH_CORPORATE_ACTIONS.get(ticker)
    if cash_action and entry < cash_action["effective_date"] <= target:
        target = next(day for day in days if day >= cash_action["effective_date"])
        reason, trigger = "CASH_MERGER", ""
    day, row, action = engine.resolve_exit_execution(cache, days, ticker, target, entry, planned)
    if row is None or (day != target and not action) or day is None or not entry < day <= planned:
        raise RuntimeError(f"Unresolved exact exit: {ticker} {target}; returned {day}")
    if action and action["reason"] == "CASH_MERGER":
        price, reason = float(row["close"]), "CASH_MERGER"
    else:
        valuation = action.get("valuation_ticker", ticker) if action else ticker
        ratio = float(action.get("shares_per_share", 1)) if action else 1.
        prior = engine.get_from_map(cache[days[days.index(day)-1]], valuation)
        reference = float(prior["close"])*ratio if prior else None
        if "open" not in row:
            raise RuntimeError(f"Missing opening field: {ticker} {day}")
        price = float(engine.execution_price(row, "next-open", splits.get(valuation, []), day, reference, valuation))
    if not np.isfinite(price) or price <= 0:
        raise RuntimeError(f"Invalid exit price: {ticker} {day}")
    return {"SignalDate": period.SignalDate, "Ticker": ticker, "EntryDate": entry,
            "PlannedExitDate": planned, "ExitDate": day, "EntryPrice_USD": entry_price,
            "ExitPrice_USD": price, "SignalPrice_USD": candidate.price,
            "RawSignalPrice_USD": candidate.raw_price, "RawADV20_USD": candidate.raw_adv20,
            "Weight": 1., "ExitReason": reason, "TriggerDate": trigger,
            "CorporateAction": action["reason"] if action else "",
            "GrossReturn_pct": (price/entry_price-1)*100}


def main():
    logging.basicConfig(level=logging.WARNING)
    OUT.mkdir(parents=True, exist_ok=True)
    spec_hash = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    record = {"status": "STARTED", "spec_sha256_before_returns": spec_hash,
              "approval": "RESEARCH_ONLY", "holdout": "No untouched period; all 43 were previously examined.",
              "factors": {"W": "risk weights", "S": "stock stop", "M": "monthly entry and daily exit SPY policy"},
              "scenario_assumptions": [asdict(c) for c in SCENARIOS],
              "account_sizes_usd": [10000., 100000.]}
    try:
        import replay_verified_audit_offline as replay
        record["input_install"] = replay.audit.install_verified_inputs("robust_locked_candidate")
        engine = replay.engine
        install_action(engine)
        install_additional_actions(engine)
        cache, basis = engine.load_backtest_cache(None)
        days = sorted(cache)
        record["price_basis"] = basis
        context = {}
        stale_uses = install_disclosed_stale_marks(engine, cache, days, [
            V3/"execution_original_responses.json", V3/"last_window_original_responses.json"], context)
        periods = pd.read_csv("audit_evidence/robust_locked_20261019/Momentum_backtest_results.csv")
        period_rows = periods[["SignalDate", "EntryDate", "ExitDate"]].to_dict("records")
        raw_dollars = load_raw_dollars(replay)
        client = engine.PolygonClient("OFFLINE_NO_NETWORK")
        splits = {}
        for row in client.fetch_recent_splits("2021-11-08", "2026-10-03"):
            splits.setdefault(row["ticker"], []).append(row)
        previous_signals = {s["signal"]: s for s in json.loads((V3/"signals.json").read_text())}
        variant_lots = {selector+"__"+label(*f): [] for selector in selection.SELECTORS for f in FACTORS}
        variant_factors = {selector+"__"+label(*f): {"selector": selector, **dict(zip(("weights","stop","market"),f))}
                           for selector in selection.SELECTORS for f in FACTORS}
        missing, canceled, choices, unit_marks, unit_lots = {}, [], [], {}, {}
        execution_cache = {}
        for period in periods.itertuples():
            signal = period.SignalDate
            history = [(day, cache[day]) for day in days if day <= signal][-253:][::-1]
            universe = engine.fetch_point_in_time_universe(client, signal, locked_robust=True)
            rankings, exclusions = selection.rank_candidates(universe, history, signal,
                client.fetch_unadjusted_signal_closes(signal), raw_dollars)
            risk_on = risk.spy_risk_on(history)
            old = previous_signals[signal]
            if risk_on != old["risk_on"]:
                raise AssertionError("Monthly gate changed")
            state = {"signal": signal, "risk_on": risk_on, "market_exit": old["market_exit"], "selectors": {}}
            for selector in selection.SELECTORS:
                chosen = rankings[selector][:25]
                if risk_on and [asdict(c) for c in chosen] != old["variants"][selector]["selected"]:
                    raise AssertionError("Existing v3 choices changed")
                weights, sizing = risk.allocation(chosen, history, signal)
                state["selectors"][selector] = {"selected": [asdict(c) for c in chosen],
                    "weights": weights, "sizing": sizing, "eligible": len(rankings[selector])}
                for w, stop, market in FACTORS:
                    name = selector+"__"+label(w, stop, market)
                    if market and not risk_on:
                        continue
                    context.update(variant=name, stage="STOP_AND_NAV")
                    for candidate in chosen:
                        weight = weights[candidate.ticker] if w else 1/25
                        key = "|".join((signal, candidate.ticker, str(int(stop)), str(int(market))))
                        try:
                            unfilled = documented_unfilled_entry(engine, cache, candidate.ticker, period.EntryDate)
                            if unfilled:
                                canceled.append({**unfilled,"variant":name,"signal":signal,"intended_weight":weight})
                                continue
                            if key not in execution_cache:
                                lot = execute_path(engine, cache, days, splits, candidate, period, stop,
                                                   old["market_exit"] if market else None)
                                marks = {}
                                for day in days:
                                    if not period.EntryDate <= day < lot["ExitDate"]:
                                        continue
                                    price, _ = engine.position_close_on_day(cache, candidate.ticker, day, period.EntryDate)
                                    if price is None or not np.isfinite(price) or price <= 0:
                                        raise RuntimeError(f"Missing daily mark: {candidate.ticker} {day}")
                                    marks[day] = float(price)
                                execution_cache[key] = lot, marks
                            lot, marks = execution_cache[key]
                            unit_marks[key], unit_lots[key] = marks, lot
                            variant_lots[name].append({**lot,"Weight":weight,"UnitPath":key})
                        except RuntimeError as error:
                            detail = {"variant":name,"signal":signal,"ticker":candidate.ticker,"error":str(error)}
                            if str(error).startswith("OFFLINE_REQUEST_MISSING "):
                                detail["request"] = json.loads(str(error).split(" ",1)[1])
                            missing.setdefault(name, []).append(detail)
            choices.append(state)
            save("choices.json", choices)
            save("missing_evidence.json", missing)
            print("PREPARED",signal,"gaps",sum(len(v) for v in missing.values()),flush=True)
        save("variant_factors.json",variant_factors)
        save("variant_lots.json",variant_lots)
        save("unit_marks.json",unit_marks)
        save("unit_lots.json",unit_lots)
        save("periods.json",period_rows)
        save("days.json",days)
        save("canceled_orders.json",canceled)
        save("stale_marks.json",list(stale_uses.values()))
        stale_dates={(row["ticker"],row["day"]) for row in stale_uses.values()}
        record["stale_affected_variants"]={name:[{"ticker":ticker,"day":day}
            for ticker,day in sorted(stale_dates) if any(p["Ticker"]==ticker and p["EntryDate"]<=day<p["ExitDate"] for p in lots)]
            for name,lots in variant_lots.items()}
        record["blocked_variants"] = missing
        record["models"] = {}
        record["matched_spy"] = {}
        benchmark_lots = {}
        record["bridge"] = {}
        record["checks"] = {}
        for name, lots in variant_lots.items():
            if name in missing:
                continue
            # Netting and funded fees must preserve the unit-path zero-cost return.
            zero = simulate(period_rows,lots,unit_marks,days,ZERO)
            fixed, zero_capital = 100., 100.
            monthly = []
            fixed_nav, gross_nav = [], []
            for period in period_rows:
                group = [p for p in lots if p["SignalDate"]==period["SignalDate"]]
                ret = sum(p["Weight"]*(p["ExitPrice_USD"]/p["EntryPrice_USD"]-1) for p in group)
                fee = .003 if group else 0.
                start, gross_start = fixed, zero_capital
                for day in days:
                    if not period["EntryDate"] <= day <= period["ExitDate"]:
                        continue
                    change = sum(p["Weight"]*((p["ExitPrice_USD"] if day>=p["ExitDate"] else unit_marks[p["UnitPath"]][day])/p["EntryPrice_USD"]-1) for p in group)
                    fixed_nav.append(start*(1+change-fee))
                    gross_nav.append(gross_start*(1+change))
                fixed *= 1+ret-fee
                zero_capital *= 1+ret
                monthly.append({"SignalDate":period["SignalDate"],"GrossReturn_pct":ret*100,"FixedNetReturn_pct":(ret-fee)*100})
            if not np.isclose(zero["summary"]["net_return_pct"],zero_capital-100,atol=1e-8):
                raise AssertionError("Zero-fee self-financing parity failed")
            def dd(values):
                a=np.r_[100.,values]
                return float((a/np.maximum.accumulate(a)-1).min()*100)
            record["bridge"][name] = {"gross_return_pct":zero_capital-100,"gross_drawdown_pct":dd(gross_nav),
                "fixed_cost_return_pct":fixed-100,"fixed_cost_drawdown_pct":dd(fixed_nav),"monthly":monthly}
            if name.endswith("__WSM"):
                selector=variant_factors[name]["selector"]
                old=pd.read_csv(V3/(selector+"_positions.csv"))
                cols=["SignalDate","Ticker","EntryDate","ExitDate","EntryPrice_USD","ExitPrice_USD","Weight"]
                pd.testing.assert_frame_equal(pd.DataFrame(lots)[cols].reset_index(drop=True),old[cols].reset_index(drop=True),check_exact=False,atol=1e-10,rtol=1e-10)
                old_metrics=json.loads((V3/"comparison.json").read_text())["models"][selector]
                if not np.isclose(fixed-100,old_metrics["net_return_pct"],atol=1e-8):
                    raise AssertionError("All-factor v3 fixed-cost parity failed")
                record["checks"][selector]="PASS_EXACT_CHOICES_PRICES_WEIGHTS_AND_FIXED_COST_RETURN"
            record["models"][name]={}
            for capital in record["account_sizes_usd"]:
                for costs in SCENARIOS:
                    result=simulate(period_rows,lots,unit_marks,days,costs,capital)
                    case=f"{name}__{costs.name}__{int(capital)}"
                    save_ledger(case,result)
                    record["models"][name][costs.name+"__"+str(int(capital))]=result["summary"]
            # Same intended initial exposure and portfolio market policy.
            matched = []
            market = variant_factors[name]["market"]
            for period in period_rows:
                signal = period["SignalDate"]
                exposure = sum(p["Weight"] for p in lots if p["SignalDate"]==signal)
                if not exposure:
                    continue
                exit_day = (previous_signals[signal]["market_exit"] if market else None) or period["ExitDate"]
                entry_price = old_execution.actual_price(engine,cache,days,splits,"SPY",period["EntryDate"])
                exit_price = old_execution.actual_price(engine,cache,days,splits,"SPY",exit_day)
                path_key = "SPY|"+signal+"|"+str(int(market))
                unit_marks[path_key] = {day:float(engine.get_from_map(cache[day],"SPY")["close"])
                    for day in days if period["EntryDate"]<=day<exit_day}
                matched.append({**period,"Ticker":"SPY","PlannedExitDate":period["ExitDate"],
                    "ExitDate":exit_day,"EntryPrice_USD":entry_price,"ExitPrice_USD":exit_price,
                    "ExitReason":"MARKET_RISK_OFF" if exit_day<period["ExitDate"] else "REBALANCE",
                    "CorporateAction":"","UnitPath":path_key,"Weight":exposure})
            bench = "spy_matched_"+name
            benchmark_lots[bench] = matched
            record["matched_spy"][name] = {}
            for capital in record["account_sizes_usd"]:
                for costs in (ZERO,*SCENARIOS):
                    result=simulate(period_rows,matched,unit_marks,days,costs,capital)
                    save_ledger(f"{bench}__{costs.name}__{int(capital)}",result)
                    record["matched_spy"][name][costs.name+"__"+str(int(capital))]=result["summary"]
            print("COMPARED",name,flush=True)
        # True SPY buy-and-hold: one initial buy, one final sale, no monthly resets.
        first, last=period_rows[0]["EntryDate"],period_rows[-1]["ExitDate"]
        spy_entry=old_execution.actual_price(engine,cache,days,splits,"SPY",first)
        spy_exit=old_execution.actual_price(engine,cache,days,splits,"SPY",last)
        spy_lot={"SignalDate":period_rows[0]["SignalDate"],"Ticker":"SPY","EntryDate":first,
            "PlannedExitDate":last,"ExitDate":last,"EntryPrice_USD":spy_entry,"ExitPrice_USD":spy_exit,
            "Weight":1.,"ExitReason":"REBALANCE","CorporateAction":"","UnitPath":"SPY_BUY_HOLD"}
        spy_marks={day:float(engine.get_from_map(cache[day],"SPY")["close"]) for day in days if first<=day<last}
        unit_marks["SPY_BUY_HOLD"] = spy_marks
        benchmark_lots["spy_buy_hold"] = [spy_lot]
        spy_period=[{"SignalDate":period_rows[0]["SignalDate"],"EntryDate":first,"ExitDate":last}]
        record["spy_buy_hold"]={}
        for capital in record["account_sizes_usd"]:
            for costs in (ZERO,*SCENARIOS):
                result=simulate(spy_period,[spy_lot],{"SPY_BUY_HOLD":spy_marks},days,costs,capital)
                record["spy_buy_hold"][costs.name+"__"+str(int(capital))]=result["summary"]
                save_ledger(f"spy_buy_hold__{costs.name}__{int(capital)}",result)
        save("benchmark_lots.json",benchmark_lots)
        save("unit_marks.json",unit_marks)
        record["status"]="COMPLETE_FACTORIAL_PROVISIONAL" if not missing else "PARTIAL_FACTORIAL_EVIDENCE_BLOCKS_DISCLOSED"
        record["limitations"]=["Previously inspected data, no independent holdout.",
            "Dated stale-close convention from v3; unknown gaps block affected variants.",
            "Fee rates, account sizes, half-spread and slippage are scenarios, not confirmed user fills/tariff.",
            "No dividends, cash interest, taxes, USD/SEK market returns or whole-share constraints.",
            "M combines monthly entry gate and daily exit; its subcomponents are not isolated."]
    except Exception as error:
        record.update(status="BLOCKED",error=str(error))
        (OUT/"traceback.txt").write_text(traceback.format_exc())
        raise
    finally:
        record["source_sha256"]={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            (Path("run_momentum_components_v4.py"),Path("momentum_order_ledger.py"),SPEC,Path("momentum_selection_v3.py"),Path("selection_v3_execution.py"))}
        save("comparison.json",record)
    print(json.dumps({k:v for k,v in record.items() if k not in ("models","bridge","blocked_variants")},indent=2),flush=True)


if __name__ == "__main__":
    main()
