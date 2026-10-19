"""Hold the 585 archived choices fixed and remove only their stock stop.

This is a diagnostic on previously examined data, not a new model or approval.
The original signal keys, entry prices, entry dates and monthly cash decisions
are immutable. Missing exits or daily marks block a complete comparison.
"""
import hashlib
import json
import logging
from pathlib import Path

import pandas as pd

import replay_verified_audit_offline as replay

BASE = Path('audit_evidence/robust_locked_20261019')
OUT = Path('audit_evidence/robust_stop_diagnostic_20261019')


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    OUT.mkdir(exist_ok=True)
    periods = pd.read_csv(BASE / 'Momentum_backtest_results.csv')
    original = pd.read_csv(BASE / 'Momentum_backtest_positions.csv', keep_default_na=False)
    replay.audit.install_verified_inputs('robust_locked_candidate')
    engine = replay.engine
    cache, basis = engine.load_backtest_cache(None)
    days = sorted(cache)
    splits = engine.PolygonClient('OFFLINE_NO_NETWORK').fetch_recent_splits('2021-11-08','2026-10-03')
    split_events = {}
    for event in splits:
        split_events.setdefault(event['ticker'],[]).append(event)
    top = original.nsmallest(20, 'GrossReturn_pct')
    windows = []
    for row in top.to_dict('records'):
        prices = {day:cache[day].get(row['Ticker']) for day in days
                  if row['SignalDate'] <= day <= row['PlannedExitDate']}
        windows.append({'lot':row,'cache':prices})
    (OUT / 'top20_cached_windows.json').write_text(json.dumps({'basis':basis,'windows':windows},indent=2)+'\n')
    (OUT / 'calendar.json').write_text(json.dumps(days)+'\n')
    issues, changed = [], []
    for old in original.to_dict('records'):
        ticker, entry, target = old['Ticker'], old['EntryDate'], old['PlannedExitDate']
        try:
            day, row, action = engine.resolve_exit_execution(cache, days, ticker, target, entry, target)
            if row is None or day is None or not entry < day <= target:
                issues.append({'ticker':ticker,'signal':old['SignalDate'],'target':target,'error':'NO_OBSERVED_EXIT_WITHIN_ORIGINAL_MONTH'})
                continue
            if action and action['reason'] == 'CASH_MERGER':
                price = float(row['close'])
                reason = 'CASH_MERGER'
            else:
                valuation_ticker=action.get('valuation_ticker',ticker) if action else ticker
                ratio=float(action.get('shares_per_share',1)) if action else 1.0
                prior=engine.get_from_map(cache[days[days.index(day)-1]],valuation_ticker)
                reference=None if prior is None else float(prior['close'])*ratio
                # Preserve the engine's exact execution-price convention; the
                # counterfactual may change only the stop, not its price logic.
                price = engine.execution_price(row,'next-open',split_events.get(valuation_ticker,[]),day,reference,valuation_ticker)
                reason = 'REBALANCE'
            new = dict(old)
            new.update(ExitDate=day, ExitPrice_USD=price, ExitReason=reason,
                       CorporateAction=action['reason'] if action else '',
                       StopLoss_pct='', GrossReturn_pct=(price/old['EntryPrice_USD']-1)*100)
            changed.append(new)
        except RuntimeError as error:
            issues.append({'ticker':ticker,'signal':old['SignalDate'],'target':target,'error':str(error)})
    no_stop = pd.DataFrame(changed)
    no_stop.to_csv(OUT / 'same_choices_without_stop_positions.csv',index=False)
    if issues:
        (OUT / 'comparison.json').write_text(json.dumps({'status':'BLOCKED_NO_COMPLETE_COMPARISON','issues':issues},indent=2)+'\n')
        print(json.dumps({'status':'BLOCKED','issues':issues}))
        return
    key = ['SignalDate','Ticker']
    frozen = original.set_index(key).sort_index()
    counterfactual = no_stop.set_index(key).sort_index()
    pd.testing.assert_frame_equal(frozen[['EntryDate','EntryPrice_USD','Rank','TopN']],counterfactual[['EntryDate','EntryPrice_USD','Rank','TopN']])
    unchanged=frozen.loc[frozen.ExitReason!='STOP_LOSS']
    pd.testing.assert_frame_equal(unchanged[['ExitDate','ExitPrice_USD']],counterfactual.loc[unchanged.index,['ExitDate','ExitPrice_USD']])
    equity, peak, worst = 100.0, 100.0, 0.0
    output_periods, nav = [], []
    for period in periods.itertuples():
        group = no_stop.loc[no_stop.SignalDate == period.SignalDate]
        cash = period.RiskRegime == 'CASH'
        if (cash and len(group)) or (not cash and (len(group)!=15 or group.Ticker.duplicated().any())):
            raise AssertionError('Frozen portfolio structure changed')
        gross = 0.0 if cash else float(group.GrossReturn_pct.mean())
        net = gross if cash else gross - 0.3
        start_value = equity
        for day in days:
            if not period.EntryDate <= day <= period.ExitDate:
                continue
            marks = []
            for position in group.itertuples():
                if day >= position.ExitDate:
                    price = position.ExitPrice_USD
                else:
                    price, _ = engine.position_close_on_day(cache,position.Ticker,day,position.EntryDate)
                    if price is None:
                        issues.append({'ticker':position.Ticker,'signal':period.SignalDate,'target':day,'error':'MISSING_DAILY_MARK'})
                        break
                marks.append(price/position.EntryPrice_USD-1)
            if len(marks)!=len(group):
                continue
            equity = start_value if cash else start_value*(1+sum(marks)/15-0.003)
            peak=max(peak,equity);worst=min(worst,equity/peak-1)
            nav.append({'SignalDate':period.SignalDate,'Date':day,'PortfolioIndex':equity})
        if abs(equity - start_value*(1+net/100))>1e-7:
            raise AssertionError('Daily marks do not reconcile with monthly cash/positions')
        output_periods.append({'SignalDate':period.SignalDate,'EntryDate':period.EntryDate,'ExitDate':period.ExitDate,
                               'RiskRegime':period.RiskRegime,'GrossReturn_pct':gross,'NetReturn_pct':net,
                               'SPYReturn_pct':period.SPYReturn_pct,'PortfolioIndex':equity})
    no_periods=pd.DataFrame(output_periods)
    no_periods.to_csv(OUT/'same_choices_without_stop_results.csv',index=False)
    pd.DataFrame(nav).to_csv(OUT/'same_choices_without_stop_daily_nav.csv',index=False)
    baseline=json.loads((BASE/'model_result.json').read_text())
    delta=counterfactual.GrossReturn_pct-frozen.GrossReturn_pct
    record={'status':'COMPLETE_FROZEN_INPUT_DIAGNOSTIC' if not issues else 'BLOCKED_MISSING_DAILY_MARKS',
            'approval':'UNVALIDATED','basis':basis,'choice_keys_entries_ranks_weights':'EXACTLY_PRESERVED',
            'periods':len(periods),'positions':len(no_stop),'cash_signals':periods.loc[periods.RiskRegime=='CASH','SignalDate'].tolist(),
            'with_stop':{'net_return_pct':baseline['metrics']['TotalReturn_pct'],'daily_drawdown_pct':baseline['metrics']['DailyMaxDrawdown_pct']},
            'without_stop':{'net_return_pct':equity-100,'gross_return_pct':float(((1+no_periods.GrossReturn_pct/100).prod()-1)*100),
                            'daily_drawdown_pct':worst*100,'positive_months':int((no_periods.NetReturn_pct>0).sum()),
                            'positive_lots':int((no_stop.GrossReturn_pct>0).sum())},
            'without_minus_with_stop_pp':equity-100-baseline['metrics']['TotalReturn_pct'],
            'lots_improved_without_stop':int((delta>1e-8).sum()),'lots_worse_without_stop':int((delta< -1e-8).sum()),
            'lots_unchanged':int((abs(delta)<=1e-8).sum()),'issues':issues,
            'limitations':['Frozen source prices and original choices; not a fresh ranking replay.','Top-20 source audit is separate and must be read before interpreting performance.','Monthly SPY gate, fixed cost, continuous equal weights and action assumptions unchanged.','No new unseen holdout, live approval or parameter optimization.'],
            'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'Momentum_backtest_positions.csv',BASE/'Momentum_backtest_results.csv',Path(__file__)]}}
    (OUT/'comparison.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    print(json.dumps(record,indent=2))


if __name__=='__main__':
    main()
