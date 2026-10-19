"""Independently aggregate the locked replay and require observed daily marks.

This audit does not run selection, change prices, or publish a GO decision.
Corporate-action unit conversions reuse the separately tested installation.
"""
import json
from pathlib import Path

import pandas as pd

import replay_verified_audit_offline as offline

OUT = Path('audit_evidence/robust_locked_20261019')


def main():
    result = json.loads((OUT / 'model_result.json').read_text())
    if result['status'] != 'COMPLETE_RESEARCH_REPLAY':
        raise RuntimeError('A complete locked replay is required')
    periods = pd.read_csv(OUT / 'Momentum_backtest_results.csv')
    positions = pd.read_csv(OUT / 'Momentum_backtest_positions.csv').fillna('')
    offline.audit.install_verified_inputs('robust_locked_candidate')
    cache, basis = offline.engine.load_backtest_cache(None)
    days = sorted(cache)
    nav, equity, peak, worst = [], 100.0, 100.0, 0.0
    cash_signals, stop_checks, missing_price_evidence, price_mismatches = [], 0, [], []
    observed_prices = 0
    for period in periods.itertuples():
        group = positions.loc[positions.SignalDate == period.SignalDate]
        history = [float(cache[day]['SPY']['close']) for day in reversed(days) if day <= period.SignalDate][:200]
        risk_on = len(history) == 200 and history[0] > sum(history) / 200
        cash = period.RiskRegime == 'CASH'
        if cash == risk_on:
            raise AssertionError('SPY regime mismatch: ' + period.SignalDate)
        if cash:
            cash_signals.append(period.SignalDate)
            if len(group) or period.NetReturn_pct != 0:
                raise AssertionError('Cash regime has positions or a nonzero return')
        elif len(group) != 15 or group.Ticker.duplicated().any():
            raise AssertionError('Portfolio must contain 15 unique equally weighted lots')
        for pos in group.itertuples():
            if not (period.EntryDate == pos.EntryDate <= pos.ExitDate <= period.ExitDate):
                raise AssertionError('Execution timing mismatch')
            calculated = (pos.ExitPrice_USD / pos.EntryPrice_USD - 1) * 100
            if abs(calculated - pos.GrossReturn_pct) > 1e-8:
                raise AssertionError('Lot return mismatch')
            if not pos.CorporateAction:
                holding_days = [d for d in days if pos.EntryDate <= d < pos.PlannedExitDate]
                first_trigger = None
                for day in holding_days:
                    close, _ = offline.engine.position_close_on_day(cache, pos.Ticker, day, pos.EntryDate)
                    if close is None:
                        raise AssertionError('Missing stop observation: ' + pos.Ticker + ' ' + day)
                    if close / pos.EntryPrice_USD - 1 <= -0.1:
                        first_trigger = days[days.index(day) + 1]
                        break
                expected_exit = first_trigger or pos.PlannedExitDate
                expected_reason = 'STOP_LOSS' if first_trigger else 'REBALANCE'
                if (pos.ExitDate, pos.ExitReason) != (expected_exit, expected_reason):
                    raise AssertionError('First close-based stop or next-session exit mismatch: ' + pos.Ticker)
                stop_checks += 1
            observations = [('SignalPrice_USD', period.SignalDate, 'c'), ('EntryPrice_USD', pos.EntryDate, 'o')]
            if not pos.CorporateAction:
                observations.append(('ExitPrice_USD', pos.ExitDate, 'o'))
            for field, day, price_field in observations:
                path = f'/v2/aggs/ticker/{pos.Ticker}/range/1/day/{day}/{day}'
                try:
                    payload = offline.offline_get(None, path, {'adjusted':'true', 'sort':'asc', 'limit':10})
                except RuntimeError as exc:
                    if not str(exc).startswith('OFFLINE_REQUEST_MISSING '):
                        raise
                    missing_price_evidence.append({'ticker':pos.Ticker, 'day':day, 'field':field})
                    continue
                bars = payload.get('results', [])
                if len(bars) != 1:
                    missing_price_evidence.append({'ticker':pos.Ticker, 'day':day, 'field':field})
                    continue
                actual, reference = float(getattr(pos, field)), float(bars[0][price_field])
                observed_prices += 1
                if abs(actual / reference - 1) > 1e-6:
                    price_mismatches.append({'ticker':pos.Ticker,'day':day,'field':field,'model':actual,'individual':reference})
        start_equity = equity
        for day in days:
            if not period.EntryDate <= day <= period.ExitDate:
                continue
            if cash:
                equity = start_equity
            else:
                gross_marks = []
                for pos in group.itertuples():
                    if day >= pos.ExitDate:
                        price = pos.ExitPrice_USD
                    else:
                        price, _ = offline.engine.position_close_on_day(cache, pos.Ticker, day, pos.EntryDate)
                        if price is None:
                            raise AssertionError('Missing daily mark: ' + pos.Ticker + ' ' + day)
                    gross_marks.append(price / pos.EntryPrice_USD - 1)
                equity = start_equity * (1 + sum(gross_marks) / 15 - 0.003)
            peak = max(peak, equity)
            worst = min(worst, equity / peak - 1)
            nav.append({'SignalDate':period.SignalDate,'Date':day,'Valuation':'EXIT_OPEN' if day == period.ExitDate else 'DAILY_CLOSE','PortfolioIndex':equity})
        if abs(equity - period.PortfolioIndex) > 1e-7:
            raise AssertionError('Independent daily NAV does not reconcile to period capital')
    if abs(worst * 100 - result['metrics']['DailyMaxDrawdown_pct']) > 1e-7:
        raise AssertionError('Independent daily drawdown mismatch')
    pd.DataFrame(nav).to_csv(OUT / 'independent_daily_nav.csv', index=False)
    audit = {'status':'PASS_INTERNAL_NAV_REGIME_AND_STOPS' if not price_mismatches else 'PRICE_MISMATCH_REQUIRES_REVIEW',
             'approval':'UNVALIDATED', 'adjusted_basis':basis,'periods':len(periods),'positions':len(positions),
             'cash_signals':cash_signals,'non_action_stop_paths_checked':stop_checks,
             'daily_marks':len(nav),'missing_daily_marks':0,'net_return_pct':equity-100,
             'daily_max_drawdown_pct':worst*100,'individual_price_checks':observed_prices,
             'individual_price_mismatches':price_mismatches,'individual_price_evidence_missing':missing_price_evidence,
             'scope':'NAV, stop timing and source coverage only; shared action converters are not independently re-derived; no new holdout or trading approval.'}
    (OUT / 'independent_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({key:value for key,value in audit.items() if key != 'individual_price_evidence_missing'}))
    if price_mismatches:
        raise AssertionError('Individual price discrepancies retained for review')


if __name__ == '__main__':
    main()
