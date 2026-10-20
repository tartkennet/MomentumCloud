"""Replay the single preregistered v2 design on existing frozen inputs only."""
import csv
import hashlib
import json
import logging
import traceback
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

import risk_managed_momentum as model

BASE = Path("audit_evidence/robust_locked_20261019")
OUT = Path("audit_evidence/risk_managed_v2_20261020")
VARIANTS = ("selection_equal", "selection_sized", "full_v2")


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def actual_price(engine, cache, days, splits, ticker, day, reference=None):
    row = engine.get_from_map(cache.get(day, {}), ticker)
    if row is None or "open" not in row:
        raise RuntimeError(f"Missing exact opening execution: {ticker} {day}")
    price = engine.execution_price(row, "next-open", splits.get(ticker, []), day, reference, ticker)
    if not np.isfinite(price) or price <= 0:
        raise RuntimeError(f"Invalid execution: {ticker} {day}")
    return float(price)


def execute_lot(engine, cache, days, splits, candidate, period, weight, regime_exit):
    ticker, entry, planned = candidate.ticker, period.EntryDate, period.ExitDate
    entry_price = actual_price(engine, cache, days, splits, ticker, entry, candidate.price)
    target, reason, trigger = planned, "REBALANCE", ""
    sessions = [day for day in days if entry <= day <= planned]
    for day, next_day in zip(sessions, sessions[1:]):
        if regime_exit is not None and day >= regime_exit:
            break  # No stock observations are needed after a funded market exit.
        cash_action = getattr(engine, "CASH_CORPORATE_ACTIONS", {}).get(ticker)
        if cash_action and entry < cash_action["effective_date"] <= day:
            # A settled cash acquisition no longer has a stock close to test.
            # Its documented consideration is resolved by the shared converter.
            target, reason = day, "CASH_MERGER"
            break
        close, _ = engine.position_close_on_day(cache, ticker, day, entry)
        if close is None or not np.isfinite(close) or close <= 0:
            raise RuntimeError(f"Missing stop observation: {ticker} {day}")
        if close / entry_price - 1 <= -model.CONFIG.stop_loss + 1e-12:
            target, reason, trigger = next_day, "STOP_LOSS", day
            break
    if regime_exit is not None and regime_exit <= target:
        target, reason = regime_exit, "MARKET_RISK_OFF"
        trigger = days[days.index(regime_exit) - 1]
    day, row, action = engine.resolve_exit_execution(cache, days, ticker, target, entry, planned)
    if row is None or day != target and not action:
        raise RuntimeError(f"Unresolved exact exit: {ticker} {target}; returned {day}")
    if day is None or not entry < day <= planned:
        raise RuntimeError(f"Exit outside funded monthly lot: {ticker} {day}")
    if action and action["reason"] == "CASH_MERGER":
        exit_price, reason = float(row["close"]), "CASH_MERGER"
    else:
        valuation_ticker = action.get("valuation_ticker", ticker) if action else ticker
        ratio = float(action.get("shares_per_share", 1)) if action else 1.0
        prior = engine.get_from_map(cache[days[days.index(day) - 1]], valuation_ticker)
        reference = float(prior["close"]) * ratio if prior else None
        if "open" not in row:
            raise RuntimeError(f"Missing opening field: {ticker} {day}")
        exit_price = float(engine.execution_price(row, "next-open", splits.get(valuation_ticker, []), day, reference, valuation_ticker))
    if not np.isfinite(exit_price) or exit_price <= 0:
        raise RuntimeError(f"Invalid exit price: {ticker} {day}")
    return {"SignalDate": period.SignalDate, "Ticker": ticker,
            "EntryDate": entry, "PlannedExitDate": planned, "ExitDate": day,
            "EntryPrice_USD": entry_price, "ExitPrice_USD": exit_price,
            "SignalPrice_USD": candidate.price, "RawSignalPrice_USD": candidate.raw_price,
            "RawADV20_USD": candidate.raw_adv20, "Weight": weight,
            "ExitReason": reason, "TriggerDate": trigger,
            "CorporateAction": action["reason"] if action else "",
            "GrossReturn_pct": (exit_price / entry_price - 1) * 100}


def aggregate(engine, cache, days, periods, lots, variant):
    nav, result = [], []
    equity, gross_equity, stress_equity = 100.0, 100.0, 100.0
    for period in periods.itertuples():
        group = [p for p in lots if p["SignalDate"] == period.SignalDate]
        if len({p["Ticker"] for p in group}) != len(group):
            raise AssertionError("Duplicated lot")
        exposure = sum(p["Weight"] for p in group)
        if not 0 <= exposure <= 1 + 1e-12:
            raise AssertionError("Borrowed monthly capital")
        cost = model.CONFIG.fixed_monthly_cost if exposure > 0 else 0.0
        start = equity
        gross_return = sum(p["Weight"] * (p["ExitPrice_USD"] / p["EntryPrice_USD"] - 1) for p in group)
        for day in days:
            if not period.EntryDate <= day <= period.ExitDate:
                continue
            change = 0.0
            for p in group:
                if day >= p["ExitDate"]:
                    price = p["ExitPrice_USD"]
                else:
                    price, _ = engine.position_close_on_day(cache, p["Ticker"], day, p["EntryDate"])
                    if price is None or not np.isfinite(price) or price <= 0:
                        raise RuntimeError(f"Missing daily mark: {p['Ticker']} {day}")
                change += p["Weight"] * (price / p["EntryPrice_USD"] - 1)
            value = start * (1 + change - cost)
            nav.append({"SignalDate": period.SignalDate, "Date": day, "PortfolioIndex": value})
        equity = start * (1 + gross_return - cost)
        gross_equity *= 1 + gross_return
        stress_equity *= 1 + gross_return - 2 * cost
        if not np.isclose(nav[-1]["PortfolioIndex"], equity, atol=1e-9):
            raise AssertionError("Daily/monthly terminal mismatch")
        result.append({"SignalDate": period.SignalDate, "EntryDate": period.EntryDate,
                       "ExitDate": period.ExitDate, "Positions": len(group), "InitialExposure": exposure,
                       "GrossReturn_pct": gross_return * 100, "NetReturn_pct": (gross_return - cost) * 100,
                       "Cost_pct": cost * 100, "PortfolioIndex": equity})
    pd.DataFrame(lots).to_csv(OUT / (variant + "_positions.csv"), index=False)
    frame = pd.DataFrame(result)
    frame.to_csv(OUT / (variant + "_results.csv"), index=False)
    pd.DataFrame(nav).to_csv(OUT / (variant + "_daily_nav.csv"), index=False)
    values = np.r_[100.0, [row["PortfolioIndex"] for row in nav]]
    drawdown = float((values / np.maximum.accumulate(values) - 1).min() * 100)
    monthly_vol = float(frame.NetReturn_pct.std(ddof=1) * np.sqrt(12))
    annualized = float(((equity / 100) ** (12 / len(periods)) - 1) * 100)
    return {"net_return_pct": equity - 100, "gross_return_pct": gross_equity - 100,
            "cost_stress_060_return_pct": stress_equity - 100, "daily_drawdown_pct": drawdown,
            "annualized_return_pct": annualized, "monthly_annualized_volatility_pct": monthly_vol,
            "positive_months": int((frame.NetReturn_pct > 0).sum()),
            "invested_months": int((frame.Positions > 0).sum()), "positions": len(lots),
            "unique_tickers": len({p["Ticker"] for p in lots}),
            "average_initial_exposure_pct": float(frame.InitialExposure.mean() * 100),
            "max_initial_weight_pct": max((p["Weight"] * 100 for p in lots), default=0),
            "worst_lot_return_pct": min((p["GrossReturn_pct"] for p in lots), default=0),
            "stop_exits": sum(p["ExitReason"] == "STOP_LOSS" for p in lots),
            "market_exits": sum(p["ExitReason"] == "MARKET_RISK_OFF" for p in lots),
            "cash_action_exits": sum(p["ExitReason"] == "CASH_MERGER" for p in lots),
            "positive_net_and_drawdown_within_20pct": bool(equity > 100 and drawdown >= -20)}


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    record = {"status": "STARTED", "approval": "RESEARCH_ONLY_UNVALIDATED",
              "configuration": model.CONFIG.to_dict(), "variants_predeclared": VARIANTS,
              "spec_sha256_before_returns": hashlib.sha256(Path("docs/risk_managed_momentum_v2_spec.md").read_bytes()).hexdigest(),
              "holdout": "All 43 periods were previously inspected; this is exploratory redesign, not unseen validation."}
    try:
        import replay_verified_audit_offline as replay
        record["inputs"] = replay.audit.install_verified_inputs("robust_locked_candidate")
        engine = replay.engine
        cache, basis = engine.load_backtest_cache(None)
        days = sorted(cache)
        record["price_basis"] = basis
        periods = pd.read_csv(BASE / "Momentum_backtest_results.csv")
        raw_dollars = json.loads(Path("raw_evidence/raw_dollar_volume.json").read_text())
        # Individual paired full histories supersede the grouped dollar series.
        full_raw = json.loads(Path("classification/verified_ticker_histories.json").read_text())
        for ticker, bases in full_raw.items():
            for day, row in bases["raw"].items():
                raw_dollars.setdefault(day, {})[ticker] = float(row["close"]) * float(row["volume"])
        from datetime import datetime, timezone
        for ticker, bases in replay.histories.items():
            for row in bases["false"].get("results", []):
                day = datetime.fromtimestamp(row["t"] / 1000, timezone.utc).date().isoformat()
                raw_dollars.setdefault(day, {})[ticker] = float(row["c"]) * float(row["v"])
        client = engine.PolygonClient("OFFLINE_NO_NETWORK")
        splits = {}
        for row in client.fetch_recent_splits("2021-11-08", "2026-10-03"):
            splits.setdefault(row["ticker"], []).append(row)
        signals, lots = [], {name: [] for name in VARIANTS}
        missing_sources = {}
        benchmark_lots = {"spy_buy_hold": [], "spy_matched_risk": []}
        for period in periods.itertuples():
            signal = period.SignalDate
            history_days = [day for day in days if day <= signal][-253:][::-1]
            history = [(day, cache[day]) for day in history_days]
            universe = engine.fetch_point_in_time_universe(client, signal, locked_robust=True)
            raw_closes = client.fetch_unadjusted_signal_closes(signal)
            ranked, exclusions = model.rank_candidates(universe, history, signal, raw_closes, raw_dollars)
            risk_on = model.spy_risk_on(history)
            if risk_on != (period.RiskRegime != "CASH"):
                raise AssertionError("SPY signal differs from baseline")
            selected = ranked[:model.CONFIG.position_count] if risk_on else []
            weights, sizing = model.allocation(selected, history, signal)
            regime_exit, regime_signal = None, None
            for day in days:
                if not period.EntryDate <= day < period.ExitDate:
                    continue
                at_day = [(d, cache[d]) for d in days if d <= day][-200:][::-1]
                if not model.spy_risk_on(at_day):
                    regime_signal, regime_exit = day, days[days.index(day) + 1]
                    break
            signals.append({"signal": signal, "universe_count": len(universe), "qualified_count": len(ranked),
                            "exclusions": exclusions, "risk_on": risk_on, "sizing": sizing,
                            "market_exit_signal": regime_signal, "market_exit": regime_exit,
                            "selected": [asdict(c) for c in selected], "weights": weights})
            for candidate in selected:
                for variant in VARIANTS:
                    weight = 1 / model.CONFIG.position_count if variant == "selection_equal" else weights[candidate.ticker]
                    try:
                        lots[variant].append(execute_lot(engine, cache, days, splits, candidate, period, weight,
                                                       regime_exit if variant == "full_v2" else None))
                    except RuntimeError as error:
                        if not str(error).startswith("OFFLINE_REQUEST_MISSING "):
                            raise
                        request = json.loads(str(error).split(" ", 1)[1])
                        missing_sources[str(error)] = request
                        save_json(OUT / "missing_sources.json", list(missing_sources.values()))
            spy_entry = actual_price(engine, cache, days, splits, "SPY", period.EntryDate)
            for name, exposure, exit_day in [("spy_buy_hold", 1.0, period.ExitDate),
                                             ("spy_matched_risk", sum(weights.values()), regime_exit or period.ExitDate)]:
                if exposure <= 0:
                    continue
                price = actual_price(engine, cache, days, splits, "SPY", exit_day)
                benchmark_lots[name].append({"SignalDate": signal, "Ticker": "SPY", "Weight": exposure,
                    "EntryDate": period.EntryDate, "PlannedExitDate": period.ExitDate, "ExitDate": exit_day,
                    "EntryPrice_USD": spy_entry, "ExitPrice_USD": price, "ExitReason": "BENCHMARK",
                    "GrossReturn_pct": (price / spy_entry - 1) * 100})
            save_json(OUT / "signals.json", signals)
            print("COMPLETE_SIGNAL", signal, len(ranked), len(selected), sizing["cash_weight"], flush=True)
        if missing_sources:
            record["missing_sources"] = list(missing_sources.values())
            raise RuntimeError("Missing source observations; no aggregate returns accepted")
        record["models"] = {name: aggregate(engine, cache, days, periods, lots[name], name) for name in VARIANTS}
        record["benchmarks"] = {name: aggregate(engine, cache, days, periods, trades, name)
                                for name, trades in benchmark_lots.items()}
        baseline = json.loads((BASE / "model_result.json").read_text())
        record["old_robust_v1"] = {"net_return_pct": baseline["metrics"]["TotalReturn_pct"],
                                    "daily_drawdown_pct": baseline["metrics"]["DailyMaxDrawdown_pct"]}
        record["status"] = "COMPLETE_PREREGISTERED_RESEARCH_REPLAY"
        record["data_gaps"] = []
        (OUT / "missing_sources.json").unlink(missing_ok=True)
        (OUT / "traceback.txt").unlink(missing_ok=True)
        record["limitations"] = [
            "Full v2 is a separate research implementation, not the app's existing v1 execution behavior.",
            "Fractional share weights, zero cash interest, fixed invested-month cost; actual fills/fees not measured.",
            "Split-adjusted price returns only; dividends, tax and USD/SEK are not simulated.",
            "Individual reference audit of every new lot and dated issuer identity audit remain separate.",
            "Research risk targets and 5% initial cap are not guarantees against gaps or later weight drift.",
            "No untouched holdout or claim of future outperformance; no parameter grid was run.",
        ]
    except Exception as exc:
        record.update(status="BLOCKED_NO_COMPLETE_V2_RETURN", error=str(exc), error_type=type(exc).__name__)
        (OUT / "traceback.txt").write_text(traceback.format_exc())
        raise
    finally:
        record["source_sha256"] = {name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                                   for name in ["risk_managed_momentum.py", "run_risk_managed_research.py",
                                                "docs/risk_managed_momentum_v2_spec.md"]}
        save_json(OUT / "comparison.json", record)
    print(json.dumps(record, indent=2), flush=True)


if __name__ == "__main__":
    main()

