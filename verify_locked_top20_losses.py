"""Audit the 20 preselected largest losses against paired individual bars.

The case set is fixed by the archived loss ranking. No security is removed,
and no new model rule or hindsight performance filter is installed.
"""
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

OUT=Path('audit_evidence/robust_stop_diagnostic_20261019')
SOURCE=Path('audit_evidence/robust_top20_source_batch_20261019.json')


def bars(text):
    if text.startswith(('Error','Warning')):
        raise ValueError('An error or empty response is not price evidence')
    result={}
    for row in csv.DictReader(io.StringIO(text)):
        bar={field:float(row[field]) for field in ('o','h','l','c','v','t')}
        if min(bar[field] for field in ('o','h','l','c','v'))<=0:
            raise ValueError('Non-positive OHLCV is not an observed trading bar')
        day=datetime.fromtimestamp(bar['t']/1000,timezone.utc).date().isoformat()
        if day in result:
            raise ValueError('Duplicate daily observation')
        result[day]=bar
    return result


def main():
    source=json.loads(SOURCE.read_text())
    saved=json.loads((OUT/'top20_cached_windows.json').read_text())
    calendar=json.loads((OUT/'calendar.json').read_text())
    observed={(r['request']['ticker'],r['request']['params']['adjusted']):bars(r['response_csv']) for r in source['records']}
    tickers={r['lot']['Ticker'] for r in saved['windows']}
    if len(saved['windows'])!=20 or len(observed)!=40:
        raise AssertionError('The fixed 20-case / 40-request scope is incomplete')
    recent_splits=list(csv.DictReader(io.StringIO(source['post_basis_splits']['response_csv'])))
    affecting=[r for r in recent_splits if r['ticker'] in tickers]
    if affecting:
        raise AssertionError('A later split requires explicit basis conversion before comparison')
    results=[]
    for case in saved['windows']:
        lot,cache=case['lot'],case['cache']
        ticker=lot['Ticker'];adjusted=observed[ticker,'true'];raw=observed[ticker,'false']
        mismatches=[];missing=[];checks=0
        for day,row in cache.items():
            if row is None or day not in adjusted or day not in raw:
                missing.append(day)
                continue
            for field,key in [('open','o'),('high','h'),('low','l'),('close','c')]:
                checks+=1
                if abs(float(row[field])/adjusted[day][key]-1)>1e-6:
                    mismatches.append({'day':day,'field':field,'cached':row[field],'individual':adjusted[day][key]})
        for field,day,key in [('SignalPrice_USD',lot['SignalDate'],'c'),('EntryPrice_USD',lot['EntryDate'],'o'),('ExitPrice_USD',lot['ExitDate'],'o')]:
            if day not in adjusted:
                missing.append(day);continue
            checks+=1
            if abs(float(lot[field])/adjusted[day][key]-1)>1e-6:
                mismatches.append({'day':day,'field':field,'cached':lot[field],'individual':adjusted[day][key]})
        entry=adjusted[lot['EntryDate']]['o']
        holding_days=[d for d in calendar if lot['EntryDate']<=d<lot['PlannedExitDate']]
        trigger=next((d for d in holding_days if d in adjusted and adjusted[d]['c']/entry-1<=-0.1),None)
        expected_exit=calendar[calendar.index(trigger)+1] if trigger else lot['PlannedExitDate']
        expected_reason='STOP_LOSS' if trigger else 'REBALANCE'
        if (expected_exit,expected_reason)!=(lot['ExitDate'],lot['ExitReason']):
            mismatches.append({'field':'stop_timing','expected_exit':expected_exit,'expected_reason':expected_reason,'model_exit':lot['ExitDate'],'model_reason':lot['ExitReason']})
        exit_open=adjusted[lot['ExitDate']]['o']
        previous_day=calendar[calendar.index(lot['ExitDate'])-1]
        previous_close=adjusted[previous_day]['c']
        before_trigger=None if trigger is None else calendar[calendar.index(trigger)-1]
        result={'ticker':ticker,'signal_date':lot['SignalDate'],'entry_date':lot['EntryDate'],'exit_date':lot['ExitDate'],
                'model_return_pct':lot['GrossReturn_pct'],'individual_return_pct':(exit_open/entry-1)*100,
                'source_entry_open':entry,'source_exit_open':exit_open,'stop_signal_date':trigger,
                'return_at_stop_signal_close_pct':None if not trigger else (adjusted[trigger]['c']/entry-1)*100,
                'stop_signal_day_open_gap_pct':None if not trigger else (adjusted[trigger]['o']/adjusted[before_trigger]['c']-1)*100,
                'stop_signal_day_open_to_close_pct':None if not trigger else (adjusted[trigger]['c']/adjusted[trigger]['o']-1)*100,
                'exit_open_gap_from_previous_close_pct':(exit_open/previous_close-1)*100,
                'planned_month_end_return_without_stop_pct':(adjusted[lot['PlannedExitDate']]['o']/entry-1)*100,
                'actual_raw_signal_close':raw[lot['SignalDate']]['c'],
                'actual_raw_signal_passes_5_usd':raw[lot['SignalDate']]['c']>=5,
                'daily_ohlc_and_lot_price_checks':checks,'source_observed_days':len(adjusted),
                'raw_adjusted_close_factors':sorted({round(adjusted[d]['c']/raw[d]['c'],8) for d in adjusted if d in raw}),
                'missing_days':sorted(set(missing)),'mismatches':mismatches,
                'status':'PASS_INDIVIDUAL_BARS_AND_STOP_TIMING' if not missing and not mismatches else 'REQUIRES_REVIEW'}
        results.append(result)
    report={'status':'COMPLETE_ALL_20_PASS' if all(r['status'].startswith('PASS') for r in results) else 'INCOMPLETE_OR_MISMATCH',
            'scope':'Fixed 20 largest archived losses; same vendor individual adjusted/raw endpoints, not an independent market-data provider or proof of order fills.',
            'cases':20,'pass':sum(r['status'].startswith('PASS') for r in results),
            'daily_ohlc_and_lot_price_checks':sum(r['daily_ohlc_and_lot_price_checks'] for r in results),
            'post_basis_split_check':{'from_exclusive':'2026-10-06','through':'2026-10-19','events_returned':len(recent_splits),'affecting_cases':affecting},
            'raw_signal_price_floor_failures':sum(not r['actual_raw_signal_passes_5_usd'] for r in results),
            'results':results,'sources':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [SOURCE,OUT/'top20_cached_windows.json',OUT/'calendar.json',Path(__file__)]}}
    (OUT/'top20_price_and_stop_audit.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    fields=['ticker','signal_date','entry_date','exit_date','individual_return_pct','stop_signal_date','return_at_stop_signal_close_pct','exit_open_gap_from_previous_close_pct','planned_month_end_return_without_stop_pct','actual_raw_signal_close','status']
    with (OUT/'top20_price_and_stop_audit.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in results)
    print(json.dumps({k:v for k,v in report.items() if k not in ['results','sources']},indent=2))
    print(json.dumps([{k:r[k] for k in fields} for r in results[:4]],indent=2))
    if report['pass']!=20:
        raise AssertionError('Source audit requires review; no performance approval')


if __name__=='__main__':
    main()
