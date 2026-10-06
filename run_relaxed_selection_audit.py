"""Audit the authorised relaxed profile and full selection chain on frozen inputs."""
import gzip,hashlib,json,math
from pathlib import Path
import pandas as pd
import backtest_momentum_v3 as engine
import run_v4_ablation_and_simple_candidate as existing
from run_corrected_component_audit import independent_check

OUT=Path('Momentum_selection_audit')
PROFILE={'name':'v4-relaxed-research-test','status':'RESEARCH_ONLY','extension_rank_weight':0,'market_regime':'OFF','stop_loss_pct':10.0,'positions':15,'rebalance':'monthly next-open','m12_weight':.55,'m6_weight':.20,'low_vol_weight':.15,'min_actual_price_usd':10,'min_adv20_usd':5000000,'production_changed':False,'source_scenario':'v4_stop_1_regime_0_extension_0','no_parameter_search':True}

def snapshot(day,adjusted):
 req={'path':'/v2/aggs/grouped/locale/us/market/stocks/'+day,'params':{'adjusted':'true' if adjusted else 'false'}}
 h=hashlib.sha256(json.dumps(req,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 p=Path('audit_request_snapshot')/(h+'.json.gz')
 if not p.exists():raise RuntimeError('Missing frozen grouped snapshot '+day+' adjusted='+str(adjusted))
 with gzip.open(p,'rt') as f:return {str(r['T']):r for r in json.load(f)['response'].get('results',[]) if r.get('T')}

def split_events():
 events={}
 for p in Path('audit_request_snapshot').glob('*.json.gz'):
  with gzip.open(p,'rt') as f:
   d=json.load(f)
  if d['request']['path']!='/stocks/v1/splits':continue
  for r in d['response'].get('results',[]):
   if r.get('ticker'):events.setdefault(r['ticker'],{})[str(r.get('execution_date'))]=r
 return {t:list(v.values()) for t,v in events.items()}

def diagnose(t,latest,history,raw,excluded):
 row={'Ticker':t,'GapExcluded':t in excluded,'Reasons':[]}
 value=existing.history_for(t,latest,history)
 if not value:
  row['Reasons'].append('INSUFFICIENT_CONTIGUOUS_HISTORY_OR_VOLUME');return row
 closes,adv=value
 price=closes[0];raw_price=raw.get(t,{}).get('c')
 row.update({'Price':price,'RawPrice':raw_price,'ADV20':adv,'M12':100*(closes[21]/closes[252]-1),'M6':100*(closes[21]/closes[126]-1),'M3':100*(price/closes[63]-1),'SMA50':sum(closes[:50])/50,'SMA200':sum(closes[:200])/200,'PriorSMA200':sum(closes[21:221])/200,'Vol':existing.formation_volatility(closes)})
 row['Extension']=100*(price/row['SMA50']-1)
 if raw_price is None:row['Reasons'].append('MISSING_RAW_PRICE')
 elif raw_price<10:row['Reasons'].append('ACTUAL_PRICE_FLOOR')
 if adv<5e6:row['Reasons'].append('ADV20_FLOOR')
 if price<=row['SMA200']:row['Reasons'].append('BELOW_SMA200')
 if row['SMA200']<=row['PriorSMA200']:row['Reasons'].append('SMA200_NOT_RISING')
 for k in ['M12','M6','M3']:
  if row[k]<=0:row['Reasons'].append(k+'_NOT_POSITIVE')
 if row['Vol'] is None:row['Reasons'].append('VOL_HISTORY')
 return row

def forward_return(cache,days,ticker,entry,exit_day):
 # Future returns are attached only after eligibility and ranking are fixed.
 entry_row=engine.get_from_map(cache.get(entry,{}),ticker)
 if not entry_row or not entry_row.get('open'):return None,'MISSING_PLANNED_ENTRY'
 actual,row,action=engine.resolve_exit_execution(cache,days,ticker,exit_day,entry,exit_day)
 if row is None or actual!=exit_day:return None,'MISSING_PLANNED_EXIT'
 return (float(row['open'])/float(entry_row['open'])-1)*100,'VERIFIED_WITHIN_PERIOD'

def main():
 OUT.mkdir(exist_ok=True)
 (OUT/'research_test_profile.json').write_text(json.dumps(PROFILE,indent=2))
 cache,basis=engine.load_backtest_cache(engine.CACHE_FILE)
 if not cache:raise RuntimeError('No safe frozen price cache')
 universes=engine.load_point_in_time_universe_cache(engine.UNIVERSE_CACHE_FILE)
 results=pd.read_csv('control_evidence/v4_stop_1_regime_0_extension_0_results.csv')
 positions=pd.read_csv('control_evidence/v4_stop_1_regime_0_extension_0_positions.csv')
 metadata=json.loads(Path('control_evidence/controlled_component_audit.json').read_text())
 metrics=next(x['metrics'] for x in metadata['runs'] if x['scenario']==PROFILE['source_scenario'])
 independent_check({'results':results,'positions':positions,'metrics':metrics})
 results.to_csv(OUT/'relaxed_v4_results.csv',index=False);positions.to_csv(OUT/'relaxed_v4_positions.csv',index=False)
 pd.read_csv('control_evidence/simple_without_regime_results.csv').to_csv(OUT/'relaxed_simple_results.csv',index=False)
 pd.read_csv('control_evidence/simple_without_regime_positions.csv').to_csv(OUT/'relaxed_simple_positions.csv',index=False)
 days=sorted(cache);tickers=sorted(set(t for u in universes.values() for t in u))
 gaps=engine.find_unverified_split_basis_tickers(cache,days,tickers,split_events())
 formation=[];flow=[];pricechecks=[];quintiles=[];unresolved=[]
 for period in results.itertuples():
  signal=period.SignalDate;raw=snapshot(signal,False);adjusted=snapshot(signal,True)
  latest=cache[signal]
  for t,r in latest.items():
   if t in raw:r['raw_signal_close']=raw[t].get('c')
  histories=[(day,cache[day]) for day in sorted((x for x in cache if x<=signal),reverse=True)[:253]]
  excluded=engine.data_quality_exclusions_asof(gaps,signal)
  rows=[diagnose(t,latest,histories,raw,excluded) for t in universes[signal]]
  for row in rows:
   row.update({'SignalDate':signal,'EntryDate':period.EntryDate,'ExitDate':period.ExitDate})
   row['EligibleIgnoringGap']=not row['Reasons']
   row['Eligible']=row['EligibleIgnoringGap'] and not row['GapExcluded']
   t=row['Ticker'];u=raw.get(t);v=adjusted.get(t)
   if u and v and u.get('c') and v.get('c') and u.get('v') and v.get('v'):
    ratio=(v['c']*v['v'])/(u['c']*u['v'])
    if abs(ratio-1)>1e-5:
     pricechecks.append({'SignalDate':signal,'Ticker':t,'RawClose':u['c'],'AdjustedClose':v['c'],'RawVolume':u['v'],'AdjustedVolume':v['v'],'DollarVolumeRatio':ratio,'Eligible':row['Eligible']})
  frame=pd.DataFrame(rows)
  eligible=frame.loc[frame.Eligible].copy()
  eligible['Score']=100*(.55*eligible.M12.rank(pct=True)+.20*eligible.M6.rank(pct=True)+.15*eligible.Vol.rank(pct=True,ascending=False))
  eligible=eligible.sort_values('Score',ascending=False,kind='stable')
  eligible['Rank']=range(1,len(eligible)+1)
  candidates=existing.v4_builder({'m12':True,'m6':True,'vol':True,'extension':False})([t for t in universes[signal] if t not in excluded],latest,histories,'v4-balanced',5e6)
  expected=sorted(candidates,key=lambda x:x.total_score,reverse=True)
  expected=[x.ticker for x in expected if engine.has_executable_planned_entry(x.ticker,period.EntryDate)][:15]
  actual=list(positions.loc[positions.SignalDate==signal].sort_values('Rank').Ticker)
  if expected!=actual:raise AssertionError('Relaxed selected tickers fail exact reproduction on '+signal)
  score_map={x.ticker:x.total_score for x in candidates}
  for r in eligible.itertuples():
   if abs(r.Score-score_map[r.Ticker])>1e-7:raise AssertionError('Independent ranking score mismatch')
  eligible['Selected']=eligible.Ticker.isin(actual)
  forward=[forward_return(cache,days,t,period.EntryDate,period.ExitDate) for t in eligible.Ticker]
  eligible['ForwardNoStopReturn_pct']=[x[0] for x in forward];eligible['ForwardStatus']=[x[1] for x in forward]
  eligible['RankQuintile']=((eligible['Rank']-1)*5//len(eligible)+1).clip(upper=5)
  for q,grp in eligible.groupby('RankQuintile'):
   valid=grp.dropna(subset=['ForwardNoStopReturn_pct'])
   quintiles.append({'SignalDate':signal,'Quintile':int(q),'EligibleCount':len(grp),'VerifiedCount':len(valid),'MeanForwardNoStopReturn_pct':float(valid.ForwardNoStopReturn_pct.mean()) if len(valid) else None,'SPYReturn_pct':period.SPYReturn_pct})
  winners=eligible.nlargest(10,'ForwardNoStopReturn_pct')
  winners.to_csv(OUT/(signal+'_top_forward_winners.csv'),index=False)
  formation.extend(json.loads(eligible.to_json(orient='records')))
  for r in eligible.loc[eligible.ForwardNoStopReturn_pct.isna()].itertuples():unresolved.append({'SignalDate':signal,'Ticker':r.Ticker,'status':r.ForwardStatus})
  reasons={reason:sum(reason in row['Reasons'] for row in rows) for reason in sorted(set(x for row in rows for x in row['Reasons']))}
  flow.append({'SignalDate':signal,'Universe':len(rows),'Eligible':len(eligible),'GapExcludedOtherwiseEligible':int((frame.EligibleIgnoringGap&frame.GapExcluded).sum()),'Selected':len(actual),'ReasonsOverlapping':reasons})
  (OUT/'selection_flow.json').write_text(json.dumps(flow,indent=2))
  print('SELECTION_AUDIT_SIGNAL',signal,'eligible',len(eligible),'selected reproduction PASS',flush=True)
 pd.DataFrame(formation).to_csv(OUT/'eligible_candidate_features.csv',index=False)
 pd.DataFrame(pricechecks).to_csv(OUT/'raw_adjusted_dollar_volume_mismatches.csv',index=False)
 pd.DataFrame(quintiles).to_csv(OUT/'rank_quintile_forward_returns.csv',index=False)
 (OUT/'unresolved_forward_valuations.json').write_text(json.dumps(unresolved,indent=2))
 manifest={'status':'COMPLETE','profile':PROFILE,'metrics':metrics,'all_43_selected_portfolios_exactly_reproduced':True,'candidate_scores_independently_reproduced':True,'raw_adjusted_dollar_volume_mismatch_rows':len(pricechecks),'raw_adjusted_mismatches_eligible':sum(x['Eligible'] for x in pricechecks),'forward_unresolved':len(unresolved),'price_basis_date':basis,'source_snapshot_run':37419651430,'source_control_run':37427345730,'limits':['forward quintile results conditional on observed valuation coverage','gap exclusions remain hypotheses','SIC not GICS','price returns omit dividends'],'next_required_action':'VERIFY_AND_REPAIR_LIQUIDITY_BASIS_BEFORE_MODEL_CONCLUSIONS' if pricechecks else 'REVIEW_RANK_AND_ELIGIBILITY_EVIDENCE'}
 (OUT/'selection_audit_manifest.json').write_text(json.dumps(manifest,indent=2))
 print('SELECTION_AUDIT_MANIFEST',json.dumps(manifest),flush=True)

if __name__=='__main__':main()
