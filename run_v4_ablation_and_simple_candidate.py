#!/usr/bin/env python3
"""Research-only v4 ablations and one pre-registered simple candidate."""
from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import backtest_momentum_v3 as engine

try:
    import verified_exit_data
    verified_exit_data.install_verified_exit_data(engine)
except ImportError:
    pass

OOS_START = "2025-03-31"
TOP_N = 15
MIN_PRICE = 10.0
MIN_ADV = 5_000_000.0
SIMPLE_MODEL = "simple-momentum-12-1-6-1-v1"


def history_for(ticker, latest, history):
    if not engine.get_from_map(latest, ticker):
        return None
    closes, dollars = [], []
    for i, (_, grouped) in enumerate(history):
        row = engine.get_from_map(grouped, ticker)
        if not row:
            break
        close = float(row["close"])
        closes.append(close)
        if i < 20 and row.get("volume") is not None:
            dollars.append(close * float(row["volume"]))
    if len(closes) < 253 or len(dollars) < 10:
        return None
    return closes, sum(dollars) / len(dollars)


def formation_volatility(closes):
    prices = list(reversed(closes[21:127]))
    returns = [b / a - 1.0 for a, b in zip(prices, prices[1:]) if a > 0 and b > 0]
    if len(returns) < 80:
        return None
    mean = sum(returns) / len(returns)
    var = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    return max(var, 0.0) ** 0.5 * 252.0 ** 0.5 * 100.0


def v4_builder(flags):
    def build(tickers, latest, history, _model, _adv):
        rows = []
        for ticker in tickers:
            value = history_for(ticker, latest, history)
            if not value:
                continue
            closes, adv20 = value
            price = closes[0]
            sma50 = sum(closes[:50]) / 50.0
            sma200 = sum(closes[:200]) / 200.0
            prior_sma200 = sum(closes[21:221]) / 200.0
            mom12_2 = (closes[21] / closes[252] - 1.0) * 100.0
            mom6_2 = (closes[21] / closes[126] - 1.0) * 100.0
            ret3 = (price / closes[63] - 1.0) * 100.0
            vol = formation_volatility(closes)
            if vol is None or (price < MIN_PRICE or adv20 < MIN_ADV or price <= sma200 or sma200 <= prior_sma200 or mom12_2 <= 0 or mom6_2 <= 0 or ret3 <= 0):
                continue
            rows.append({"ticker":ticker,"price":price,"m12":mom12_2,"m6":mom6_2,"vol":vol,"extension":(price / sma50 - 1.0) * 100.0})
        if not rows:
            return []
        frame = pd.DataFrame(rows)
        frame["r12"] = frame.m12.rank(pct=True)
        frame["r6"] = frame.m6.rank(pct=True)
        frame["rv"] = frame.vol.rank(pct=True, ascending=False)
        frame["re"] = frame.extension.rank(pct=True, ascending=False)
        frame["score"] = 100.0 * (0.55 * flags["m12"] * frame.r12 + 0.20 * flags["m6"] * frame.r6 + 0.15 * flags["vol"] * frame.rv + 0.10 * flags["extension"] * frame.re)
        return [SimpleNamespace(ticker=str(row.ticker), price_usd=float(row.price), total_score=float(row.score)) for row in frame.itertuples(index=False)]
    return build


def simple_builder(tickers, latest, history, _model, _adv):
    rows = []
    for ticker in tickers:
        value = history_for(ticker, latest, history)
        if not value:
            continue
        closes, adv20 = value
        price = closes[0]
        if price <= MIN_PRICE or adv20 <= MIN_ADV:
            continue
        rows.append({"ticker":ticker,"price":price,"m12":(closes[21] / closes[252] - 1.0) * 100.0,"m6":(closes[21] / closes[126] - 1.0) * 100.0})
    if not rows:
        return []
    frame = pd.DataFrame(rows)
    frame["score"] = 100.0 * (0.60 * frame.m12.rank(pct=True) + 0.40 * frame.m6.rank(pct=True))
    return [SimpleNamespace(ticker=str(row.ticker), price_usd=float(row.price), total_score=float(row.score)) for row in frame.itertuples(index=False)]


@contextmanager
def patched(builder, no_regime=False):
    old_builder, old_regime, old_adv = engine.build_prior_2_12_metrics, engine.core_market_regime_is_risk_on, engine.RESEARCH_MIN_ADV20_USD
    engine.build_prior_2_12_metrics, engine.RESEARCH_MIN_ADV20_USD = builder, MIN_ADV
    if no_regime:
        engine.core_market_regime_is_risk_on = lambda *_args, **_kwargs: True
    try:
        yield
    finally:
        engine.build_prior_2_12_metrics, engine.core_market_regime_is_risk_on, engine.RESEARCH_MIN_ADV20_USD = old_builder, old_regime, old_adv


def segment(results, positions):
    if results.empty:
        raise RuntimeError("Validation segment contains no complete monthly periods")
    pi = (1.0 + results.NetReturn_pct / 100.0).prod()
    si = (1.0 + results.SPYReturn_pct / 100.0).prod()
    cache, _ = engine.load_backtest_cache(engine.CACHE_FILE)
    return {"Periods":int(len(results)),"TotalReturn_pct":float((pi-1.0)*100.0),"SPYTotalReturn_pct":float((si-1.0)*100.0),"TotalEdgeVsSPY_pct":float((pi-si)*100.0),"PeriodHitRate_pct":float((results.NetReturn_pct>0).mean()*100.0),"DailyMaxDrawdown_pct":float(engine.daily_portfolio_max_drawdown(positions.to_dict("records"),cache,sorted(cache)))}


def check(total, oos):
    return {"at_least_30_periods":total["Periods"]>=30,"positive_net_return":total["TotalReturn_pct"]>0,"beats_spy":total["TotalEdgeVsSPY_pct"]>0,"daily_max_drawdown_at_most_20_pct":total["DailyMaxDrawdown_pct"]>=-20,"hit_rate_at_least_50_pct":total["PeriodHitRate_pct"]>=50,"oos_at_least_12_periods":oos["Periods"]>=12,"oos_positive_net_return":oos["TotalReturn_pct"]>0,"oos_beats_spy":oos["TotalEdgeVsSPY_pct"]>0,"oos_daily_max_drawdown_at_most_20_pct":oos["DailyMaxDrawdown_pct"]>=-20,"oos_hit_rate_at_least_50_pct":oos["PeriodHitRate_pct"]>=50}


def run_one(name, builder, start, end, stop=10.0, no_regime=False):
    with patched(builder, no_regime):
        engine.run(start=start,end=end,rebalance_months=1,stop_loss_pct=stop,exit_rule="stop" if stop is not None else "rebalance",exit_execution="next-open",top_n=TOP_N,entry_execution="next-open",rebalance_exit_execution="next-open",selection_model="v4-balanced",portfolio_value_usd=10_000.0,universe_mode="point-in-time")
    results, positions = pd.read_csv("Momentum_backtest_results.csv"), pd.read_csv("Momentum_backtest_positions.csv")
    total = segment(results, positions)
    oos = segment(results.loc[results.SignalDate>=OOS_START].copy(), positions.loc[positions.SignalDate>=OOS_START].copy())
    return {"scenario":name,"metrics":total,"out_of_sample_metrics":oos,"gates":check(total,oos),"results":results,"positions":positions}


def row(run, baseline=None):
    total, oos = run["metrics"], run["out_of_sample_metrics"]
    data={"Scenario":run["scenario"],"TotalReturn_pct":total["TotalReturn_pct"],"SPYTotalReturn_pct":total["SPYTotalReturn_pct"],"TotalEdgeVsSPY_pct":total["TotalEdgeVsSPY_pct"],"DailyMaxDrawdown_pct":total["DailyMaxDrawdown_pct"],"PeriodHitRate_pct":total["PeriodHitRate_pct"],"OOSPeriods":oos["Periods"],"OOSTotalReturn_pct":oos["TotalReturn_pct"],"OOSSPYTotalReturn_pct":oos["SPYTotalReturn_pct"],"OOSEdgeVsSPY_pct":oos["TotalEdgeVsSPY_pct"],"OOSDailyMaxDrawdown_pct":oos["DailyMaxDrawdown_pct"],"OOSHitRate_pct":oos["PeriodHitRate_pct"],"Status":"GO" if all(run["gates"].values()) else "NO-GO"}
    if baseline:
        data["DeltaTotalReturn_pct"] = total["TotalReturn_pct"] - baseline["metrics"]["TotalReturn_pct"]
        data["DeltaOOSTotalReturn_pct"] = oos["TotalReturn_pct"] - baseline["out_of_sample_metrics"]["TotalReturn_pct"]
    return data


def _compounded_return(values):
    return float(((1.0 + values / 100.0).prod() - 1.0) * 100.0) if len(values) else 0.0


def _records(frame, columns):
    return json.loads(frame.loc[:, columns].to_json(orient="records"))


def exposure_accounting(results):
    risk_on = results.loc[results["RiskRegime"] == "RISK_ON"].copy()
    cash = results.loc[results["RiskRegime"] == "CASH"].copy()
    gross_total = _compounded_return(results["GrossReturn_pct"])
    net_total = _compounded_return(results["NetReturn_pct"])
    return {
        "risk_on_periods": int(len(risk_on)),
        "cash_periods": int(len(cash)),
        "risk_on_stock_gross_return_pct": _compounded_return(risk_on["GrossReturn_pct"]),
        "risk_on_spy_return_pct": _compounded_return(risk_on["SPYReturn_pct"]),
        "cash_period_spy_return_pct": _compounded_return(cash["SPYReturn_pct"]),
        "gross_before_fixed_cost_pct": gross_total,
        "net_after_fixed_cost_pct": net_total,
        "fixed_transaction_cost_effect_pct_points": gross_total - net_total,
        "turnover_measurement": "NOT_AVAILABLE: engine charges one fixed 0.30% round-trip cost in every RISK_ON month and does not measure security-level turnover or partial turnover.",
    }


def root_cause_metrics(run):
    """Describe realised holdings and periods; no inferred sector labels."""
    results, positions = run["results"].copy(), run["positions"].copy()
    positions["Weight"] = 1.0 / positions["TopN"]
    positions["WeightedContribution_pct"] = positions["GrossReturn_pct"] * positions["Weight"]
    ticker = (positions.groupby("Ticker", as_index=False)
        .agg(Occurrences=("Ticker", "size"), GrossContribution_pct=("WeightedContribution_pct", "sum"),
             AveragePositionReturn_pct=("GrossReturn_pct", "mean"), WorstPositionReturn_pct=("GrossReturn_pct", "min"))
        .sort_values("GrossContribution_pct"))
    months = results.sort_values("NetReturn_pct")
    return {
        "largest_losing_tickers_by_weighted_gross_contribution": _records(ticker.head(20), ["Ticker", "Occurrences", "GrossContribution_pct", "AveragePositionReturn_pct", "WorstPositionReturn_pct"]),
        "worst_months": _records(months.head(20), ["SignalDate", "NetReturn_pct", "GrossReturn_pct", "SPYReturn_pct", "NetEdgeVsSPY_pct", "RiskRegime"]),
        "stop_loss": {
            "triggered_positions": int((positions["ExitReason"] == "STOP_LOSS").sum()),
            "total_positions": int(len(positions)),
            "trigger_rate_pct": float((positions["ExitReason"] == "STOP_LOSS").mean() * 100.0) if len(positions) else 0.0,
        },
        "position_return_thresholds": {
            "at_least_50_pct": int((positions["GrossReturn_pct"] >= 50.0).sum()),
            "at_least_100_pct": int((positions["GrossReturn_pct"] >= 100.0).sum()),
            "total_positions": int(len(positions)),
        },
        "exposure_and_accounting": {
            "total": exposure_accounting(results),
            "out_of_sample": exposure_accounting(results.loc[results["SignalDate"] >= OOS_START].copy()),
        },
        "sector_attribution": {
            "status": "NOT_COMPUTED",
            "reason": "No point-in-time sector identifier is stored in the universe cache, OHLCV cache or position output. Sector contribution would be invented without an additional verified sector dataset.",
        },
    }


def low_extension_counterfactual(baseline, no_extension):
    base = baseline["positions"][["SignalDate", "Ticker"]].drop_duplicates()
    alternative = no_extension["positions"].merge(base, on=["SignalDate", "Ticker"], how="left", indicator=True)
    alternative["EqualWeight_pct"] = 100.0 / alternative["TopN"]
    excluded = alternative.loc[alternative["_merge"] == "left_only"].copy()
    winners = excluded.loc[excluded["GrossReturn_pct"] > 0.0].sort_values("GrossReturn_pct", ascending=False)
    return {
        "definition": "Counterfactual holdings selected when only the low-extension rank is removed, but not selected by baseline; this is not a causal claim about a single ticker.",
        "counterfactual_excluded_positions": int(len(excluded)),
        "counterfactual_excluded_winners": int(len(winners)),
        "counterfactual_excluded_winners_at_least_50_pct": int((winners["GrossReturn_pct"] >= 50.0).sum()),
        "counterfactual_excluded_winners_at_least_100_pct": int((winners["GrossReturn_pct"] >= 100.0).sum()),
        "largest_counterfactual_excluded_winners": _records(winners.head(30), ["SignalDate", "Ticker", "GrossReturn_pct", "EqualWeight_pct", "ExitReason"]),
    }


def component_rows(model, baseline, no_stop=None, no_regime=None):
    exposure = root_cause_metrics(baseline)["exposure_and_accounting"]
    total, oos = exposure["total"], exposure["out_of_sample"]
    rows = [
        {"component": "stock selection, RISK_ON months", "total_effect_pct_points": total["risk_on_stock_gross_return_pct"] - total["risk_on_spy_return_pct"], "oos_effect_pct_points": oos["risk_on_stock_gross_return_pct"] - oos["risk_on_spy_return_pct"], "method": "gross selected portfolio versus SPY during the same RISK_ON months"},
        {"component": "cash versus SPY, CASH months", "total_effect_pct_points": -total["cash_period_spy_return_pct"], "oos_effect_pct_points": -oos["cash_period_spy_return_pct"], "method": "portfolio earns 0% while the regime is cash"},
        {"component": "fixed transaction costs", "total_effect_pct_points": -total["fixed_transaction_cost_effect_pct_points"], "oos_effect_pct_points": -oos["fixed_transaction_cost_effect_pct_points"], "method": "compounded gross-before-cost versus net-after-cost"},
        {"component": "security turnover", "total_effect_pct_points": None, "oos_effect_pct_points": None, "method": total["turnover_measurement"]},
    ]
    if no_stop is not None:
        rows.append({"component": "10% stop-loss kept", "total_effect_pct_points": baseline["metrics"]["TotalReturn_pct"] - no_stop["metrics"]["TotalReturn_pct"], "oos_effect_pct_points": baseline["out_of_sample_metrics"]["TotalReturn_pct"] - no_stop["out_of_sample_metrics"]["TotalReturn_pct"], "method": "one-factor ablation; interactions and compounding mean it is not additive"})
    else:
        rows.append({"component": "stop-loss", "total_effect_pct_points": None, "oos_effect_pct_points": None, "method": "not present in this model"})
    if no_regime is not None:
        rows.append({"component": "SPY>SMA200 regime kept", "total_effect_pct_points": baseline["metrics"]["TotalReturn_pct"] - no_regime["metrics"]["TotalReturn_pct"], "oos_effect_pct_points": baseline["out_of_sample_metrics"]["TotalReturn_pct"] - no_regime["out_of_sample_metrics"]["TotalReturn_pct"], "method": "one-factor ablation; interactions and compounding mean it is not additive"})
    return {"model": model, "non_additivity_warning": "Rows are separate counterfactual/accounting views and must not be summed.", "rows": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start",default="2023-02-01")
    parser.add_argument("--end",default=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat())
    args = parser.parse_args()
    base={"m12":True,"m6":True,"vol":True,"extension":True}
    specs=[("v4-balanced baseline",v4_builder(base),10.0,False),("v4 without stop-loss",v4_builder(base),None,False),("v4 without low-volatility rank",v4_builder({**base,"vol":False}),10.0,False),("v4 without low-extension rank",v4_builder({**base,"extension":False}),10.0,False),("v4 without SPY>SMA200 regime",v4_builder(base),10.0,True),("v4 without 12-2 score",v4_builder({**base,"m12":False}),10.0,False),("v4 without 6-2 score",v4_builder({**base,"m6":False}),10.0,False)]
    runs=[run_one(name,builder,args.start,args.end,stop,no_regime) for name,builder,stop,no_regime in specs]
    baseline=runs[0]
    simple=run_one(SIMPLE_MODEL,simple_builder,args.start,args.end,None,False)
    simple_no_regime=run_one("simple without SPY>SMA200 regime",simple_builder,args.start,args.end,None,True)
    pd.DataFrame([row(item,None if item is baseline else baseline) for item in runs]+[row(simple,baseline),row(simple_no_regime,simple)]).to_csv("Momentum_ablation_results.csv",index=False)
    decision={"model":SIMPLE_MODEL,"pre_registered_rules":{"universe":"POINT_IN_TIME_US_COMMON_STOCKS","price_floor_usd":MIN_PRICE,"adv20_floor_usd":MIN_ADV,"market_regime":"SPY > SMA200","ranking":"60% completed 12-1, 40% completed 6-1","positions":TOP_N,"weighting":"equal","rebalancing":"monthly next-open","single_stock_exit":"rebalance only","round_trip_cost_pct":engine.ROUND_TRIP_COST_PCT},"out_of_sample_start":OOS_START,"metrics":simple["metrics"],"out_of_sample_metrics":simple["out_of_sample_metrics"],"gates":simple["gates"],"status":"GO" if all(simple["gates"].values()) else "NO-GO","limitation":"Current limitation: survivorship bias"}
    Path("Momentum_simple_momentum_validation_decision.json").write_text(json.dumps(decision,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    review={"scope":"research-only; production, Buy Now and paper portfolio untouched","execution_chain":{"universe":"point-in-time US common stocks","data":"Massive/Polygon adjusted daily OHLCV","v4_filters":"price > 10, ADV20 > 5M, above rising SMA200, positive 12-2, 6-2 and 3-month returns","v4_ranking":"55% 12-2, 20% 6-2, 15% low volatility, 10% low extension","portfolio":"15 equal-weight","exits":"10% stop or monthly rebalance, next-open","market_regime":"SPY > SMA200","costs":f"{engine.ROUND_TRIP_COST_PCT}% round trip"},"v4_balanced":{"status":"RETIRED_RESEARCH_ONLY" if not all(baseline["gates"].values()) else "RESEARCH_ONLY","gates":baseline["gates"],"metrics":baseline["metrics"],"out_of_sample_metrics":baseline["out_of_sample_metrics"]},"ablation_results":[{"scenario":run["scenario"],"total_return_delta_pct":run["metrics"]["TotalReturn_pct"]-baseline["metrics"]["TotalReturn_pct"],"oos_return_delta_pct":run["out_of_sample_metrics"]["TotalReturn_pct"]-baseline["out_of_sample_metrics"]["TotalReturn_pct"],"interpretation":"descriptive one-factor ablation, not statistical proof"} for run in runs[1:]],"simple_candidate":decision,"evidence_limit":"One five-year sample and single-factor ablations are descriptive; they do not establish statistical significance.","limitation":"Current limitation: survivorship bias"}
    Path("Momentum_model_review.json").write_text(json.dumps(review,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    root_cause={"scope":"research-only; no model, production, Buy Now or paper-portfolio change","v4_balanced":root_cause_metrics(baseline),"simple_momentum":root_cause_metrics(simple),"low_extension_counterfactual":low_extension_counterfactual(baseline,runs[3]),"component_attribution":{"v4_balanced":component_rows("v4-balanced",baseline,runs[1],runs[4]),"simple_momentum":component_rows(SIMPLE_MODEL,simple,None,simple_no_regime)},"limitation":"Current limitation: survivorship bias"}
    Path("Momentum_root_cause_analysis.json").write_text(json.dumps(root_cause,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print("ROOT_CAUSE_ANALYSIS_JSON=" + json.dumps(root_cause,sort_keys=True,allow_nan=False))
    print(pd.read_csv("Momentum_ablation_results.csv").to_string(index=False))
    print(f"{SIMPLE_MODEL}: {decision['status']}")
    if decision["status"] != "GO":
        failed=", ".join(key for key,value in simple["gates"].items() if not value)
        raise RuntimeError(f"{SIMPLE_MODEL} is NO-GO: {failed}")


if __name__ == "__main__":
    main()
