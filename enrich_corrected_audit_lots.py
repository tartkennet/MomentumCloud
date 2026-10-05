"""Complete missing daily peaks and historical SIC facts; no strategy or backtest."""
import json
import os
from pathlib import Path
from datetime import datetime,timezone
from momentum_master_v3 import PolygonClient
import backtest_momentum_v3 as engine
import pandas as pd

def safe_error(exc):
    response=getattr(exc,'response',None)
    return {'status':'UNAVAILABLE','error_type':type(exc).__name__,'http_status':getattr(response,'status_code',None)}

def bars(client,ticker,start,end):
    d=client._get(f'/v2/aggs/ticker/{ticker}/range/1/day/{start}/{end}',{'adjusted':'true','sort':'asc','limit':50000})
    return {datetime.fromtimestamp(x['t']/1000,timezone.utc).date().isoformat():x for x in d.get('results',[])}

def main():
    os.environ.setdefault('POLYGON_MAX_RETRIES','5')
    os.environ.setdefault('POLYGON_RATE_LIMIT_WAIT_SECONDS','15')
    client=PolygonClient(os.environ['POLYGON_API_KEY'])
    # Read pre-existing artifacts inside the same authenticated private repo.
    # No position payload is committed, transmitted to a new repo or published.
    positions=[]
    keys=['Ticker','EntryDate','ExitDate','EntryPrice_USD','ExitPrice_USD']
    for model in ['v4','simple']:
        corrected=pd.read_csv(Path('audit_corrected')/(model+'_positions.csv'))
        original=pd.read_csv(Path('audit_original')/(model+'_enriched_positions.csv'))
        joined=corrected.merge(original[keys].drop_duplicates(),on=keys,how='left',indicator=True)
        missing=joined.loc[joined['_merge']=='left_only'].drop(columns='_merge').copy()
        missing['Model']=model
        positions.extend(json.loads(missing.to_json(orient='records')))
    inp={'source_run':37380437479,'positions':positions}
    out=Path('Momentum_data_audit');out.mkdir(exist_ok=True)
    records=[]
    references={}
    for p in inp['positions']:
        record={'Model':p['Model'],'Ticker':p['Ticker'],'EntryDate':p['EntryDate'],'ExitDate':p['ExitDate'],'SignalDate':p['SignalDate']}
        key=(p['Ticker'],p['EntryDate'])
        if key not in references:
            try:
                d=client._get('/v3/reference/tickers/'+p['Ticker'],{'date':p['EntryDate']}).get('results',{})
                references[key]={'SIC':d.get('sic_code'),'Industry':d.get('sic_description') or 'UNKNOWN','CIK':d.get('cik'),'Name':d.get('name'),'ReferenceDate':p['EntryDate'],'ReferenceStatus':'OK'}
            except Exception as exc:
                references[key]={'SIC':None,'Industry':'UNKNOWN','ReferenceStatus':'UNAVAILABLE',**safe_error(exc)}
        record.update(references[key])
        try:
            prices=bars(client,p['Ticker'],p['EntryDate'],p['ExitDate'])
            entry=prices.get(p['EntryDate'],{}).get('o')
            error=abs(entry/p['EntryPrice_USD']-1) if entry else None
            record['EntryRelativeError']=error
            if error is None or error>1e-6:
                record['PeakStatus']='UNVERIFIED_ENTRY_BASIS'
            else:
                action=engine.STOCK_CORPORATE_ACTIONS.get(p['Ticker'])
                successor=bars(client,action['successor_ticker'],p['EntryDate'],p['ExitDate']) if action and action['effective_date']<p['ExitDate'] else {}
                highs=[float(p['EntryPrice_USD']),float(p['ExitPrice_USD'])]
                closes=list(highs)
                for day,row in prices.items():
                    if p['EntryDate']<=day<p['ExitDate'] and not (action and day>=action['effective_date']):
                        highs.append(float(row['h']));closes.append(float(row['c']))
                for day,row in successor.items():
                    if max(p['EntryDate'],action['effective_date'])<=day<p['ExitDate']:
                        ratio=action['shares_per_share'];cash=action.get('cash_per_share',0)
                        highs.append(float(row['h'])*ratio+cash);closes.append(float(row['c'])*ratio+cash)
                record['MaxIntradayReturn_pct']=100*(max(highs)/p['EntryPrice_USD']-1)
                record['MaxCloseOrExitReturn_pct']=100*(max(closes)/p['EntryPrice_USD']-1)
                record['PeakStatus']='COMPLETE_SAME_PROVIDER'
                (out/(p['Model']+'_'+p['Ticker']+'_'+p['SignalDate']+'_bars.json')).write_text(json.dumps({'position':p,'adjusted_bars':prices,'successor_bars':successor},indent=2))
        except Exception as exc:
            record.update(safe_error(exc));record['PeakStatus']='UNAVAILABLE'
        records.append(record)
        (out/'corrected_lot_enrichment.json').write_text(json.dumps({'source_run':inp['source_run'],'records':records},indent=2,allow_nan=False))
    print('Completed corrected-lot enrichment:',len(records))

if __name__=='__main__':
    main()
