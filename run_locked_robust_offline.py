"""Replay the already locked robust candidate; never issue a trading approval."""
import hashlib
import json
import logging
import traceback
from pathlib import Path

import pandas as pd

import replay_verified_audit_offline as offline
import run_corrected_component_audit as controls
from momentum_config import PRODUCTION
from run_universe_diagnostic_batch import evidence_error

OUT = Path("audit_evidence/robust_locked_20261019")


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    OUT.mkdir(parents=True, exist_ok=True)
    record = {
        "model": PRODUCTION.selection_model,
        "configuration": PRODUCTION.to_dict(),
        "status": "STARTED",
        "approval": "UNVALIDATED",
        "holdout": "All historical periods have already been examined; no new holdout.",
        "limitations": [
            "Historical adjusted OHLCV signal basis matches the existing live ranker; raw price/liquidity parity is not approved.",
            "Fixed 0.30% cost per invested month; actual spread, slippage and turnover are not measured.",
            "Universe classification and dated issuer continuity require separate evidence checks.",
            "SPY regime is evaluated at month-end signals; the live app's daily exits and intramonth reentries are not replayed.",
            "Fractional equal-weight lots are used; live whole-share affordability and calendar scheduling are not replayed.",
        ],
    }
    path = OUT / "model_result.json"
    path.write_text(json.dumps(record, indent=2) + "\n")
    issues = {}
    try:
        record["inputs"] = offline.audit.install_verified_inputs("robust_locked_candidate")
        # Complete the diagnostic pass when evidence is unavailable, but never
        # accept returns from a pass that skipped a stop mark or an exit.
        def guard(function, kind):
            def checked(*args, **kwargs):
                try:
                    return function(*args, **kwargs)
                except RuntimeError as error:
                    if not evidence_error(error):
                        raise
                    key = str(error)
                    if key not in issues:
                        issues[key] = {'path':kind, 'reason':key}
                        (OUT / 'missing_evidence.json').write_text(json.dumps({
                            'status':'DIAGNOSTIC_ONLY_NO_VALID_RETURN',
                            'issues':list(issues.values()),
                        },indent=2)+'\n')
                        logging.error('LOCKED_REPLAY_EVIDENCE_GAP %s', key)
                    return (None, None, None) if kind == 'exit' else (None, None)
            return checked
        offline.engine.resolve_exit_execution = guard(offline.engine.resolve_exit_execution, 'exit')
        offline.engine.position_close_on_day = guard(offline.engine.position_close_on_day, 'daily_close')
        offline.engine.run(
            start="2023-02-01", end="2026-10-03", rebalance_months=1,
            stop_loss_pct=PRODUCTION.stop_loss_pct, exit_rule="stop",
            exit_execution="next-open", top_n=PRODUCTION.position_count,
            entry_execution="next-open", rebalance_exit_execution="next-open",
            selection_model=PRODUCTION.selection_model, portfolio_value_usd=10_000.0,
            universe_mode="point-in-time", execution_backfill=False,
        )
        if issues:
            raise RuntimeError('Skipped price evidence; this diagnostic has no valid return')
        results = pd.read_csv("Momentum_backtest_results.csv")
        positions = pd.read_csv("Momentum_backtest_positions.csv")
        summary = pd.read_csv("Momentum_backtest_summary.csv", keep_default_na=False).iloc[0].to_dict()
        record["checks"] = controls.independent_check({
            "results": results, "positions": positions, "metrics": summary,
        })
        for source in ("Momentum_backtest_results.csv", "Momentum_backtest_positions.csv", "Momentum_backtest_summary.csv"):
            (OUT / source).write_bytes(Path(source).read_bytes())
        record.update(status="COMPLETE_RESEARCH_REPLAY", metrics=summary,
                      positions=len(positions), unique_tickers=int(positions.Ticker.nunique()))
        record['gross_return_pct'] = float(((1 + results.GrossReturn_pct / 100).prod() - 1) * 100)
        record['spy_same_fixed_cost_return_pct'] = float(((1 + (results.SPYReturn_pct - offline.engine.ROUND_TRIP_COST_PCT) / 100).prod() - 1) * 100)
        from validate_production_backtest import OOS_START, segment_metrics
        record['previously_examined_later_segment_start'] = OOS_START
        record['previously_examined_later_segment'] = segment_metrics(results.loc[results.SignalDate >= OOS_START])
        (OUT / 'traceback.txt').unlink(missing_ok=True)
    except Exception as exc:
        record.update(status="BLOCKED", error_type=type(exc).__name__, error=str(exc))
        record['evidence_issues'] = list(issues.values())
        (OUT / "traceback.txt").write_text(traceback.format_exc())
        raise
    finally:
        record["source_sha256"] = {
            name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
            for name in ("backtest_momentum_v3.py", "momentum_strategy.py", "momentum_config.py",
                         "run_one_verified_gap_model.py", "run_locked_robust_offline.py")
        }
        path.write_text(json.dumps(record, indent=2, default=str, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
