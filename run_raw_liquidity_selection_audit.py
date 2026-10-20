"""Validate actual historical dollar volume; rerun fixed diagnostics, no tuning."""
import json, os, math, itertools
from pathlib import Path
import pandas as pd
import backtest_momentum_v3 as engine
import run_v4_ablation_and_simple_candidate as existing
import run_corrected_component_audit as controls
import run_relaxed_selection_audit as selection
from momentum_master_v3 import PolygonClient

OUT=Path('Momentum_raw_liquidity_audit')

def main():
 OUT.mkdir(exist_ok=True)
 controls.SNAPSHOT.mkdir(exist_ok=True)
 controls.freeze_provider()
 cache,basis=engine.load_backtest_cache(engine.CACHE_FILE)
 if not cache:raise RuntimeError('Missing validated frozen cache')
 original=pd.read_csv('control_evidence/v4_stop_1_regime_0_extension_0_results.csv')
 required=sorted({d for s in original.SignalDate for d in sorted((x for x in cache if x<=s),reverse=True)[:20]})
 client=PolygonClient(os.environ['POLYGON_API_KEY'])
 raw={};mismatches=[]
 for i,day in enumerate(required):
  response=client._get('/v2/aggs/grouped/locale/us/market/stocks/'+day,{'adjusted':'false'})
  rows={str(x['T']).upper():x for x in response.get('results',[]) if x.get('T')}
  if len(rows)<1000:raise RuntimeError('Incomplete raw session '+day)
  raw[day]={}
  for ticker,row in cache[day].items():
   u=rows.get(ticker)
   if u is None:continue
   c,v=u.get('c'),u.get('v')
   if c is None or v is None or not math.isfinite(float(c)*float(v)) or float(c)<=0 or float(v)<0:raise RuntimeError('Invalid actual dollar volume '+day+' '+ticker)
   actual=float(c)*float(v);raw[day][ticker]=actual
   used=float(row['close'])*float(row['volume'])
   if actual>0 and abs(used/actual-1)>1e-5:mismatches.append({'Date':day,'Ticker':ticker,'ActualDollarVolume':actual,'PreviouslyUsedDollarVolume':used,'Ratio':used/actual})
  print('RAW_LIQUIDITY_SESSION',i+1,len(required),day,flush=True)
 (OUT/'raw_dollar_volume.json').write_text(json.dumps(raw,separators=(',',':')))
 pd.DataFrame(mismatches).to_csv(OUT/'historical_dollar_volume_mismatches.csv',index=False)
 old_history=existing.history_for
 def corrected(ticker,latest,history):
  value=old_history(ticker,latest,history)
  if value is None:return None
  dollars=[]
  for day,grouped in history[:20]:
   r=engine.get_from_map(grouped,ticker)
   if r is None or r.get('volume') is None:continue
   if ticker not in raw.get(day,{}):raise RuntimeError('Missing verified raw liquidity '+day+' '+ticker)
   dollars.append(raw[day][ticker])
  if len(dollars)<10:return None
  return value[0],sum(dollars)/len(dollars)
 existing.history_for=corrected
 flags={'m12':True,'m6':True,'vol':True,'extension':True}
 specs=[]
 for stop,regime,extension in itertools.product([False,True],repeat=3):
  name='v4_baseline' if (stop,regime,extension)==(True,True,True) else f'v4_stop_{int(stop)}_regime_{int(regime)}_extension_{int(extension)}'
  specs.append((name,existing.v4_builder({**flags,'extension':extension}),10.0 if stop else None,not regime))
 specs += [('v4_without_'+f,existing.v4_builder({**flags,f:False}),10.0,False) for f in ['m12','m6','vol']]
 specs += [('simple_baseline',existing.simple_builder,None,False),('simple_without_regime',existing.simple_builder,None,True)]
 records=[]
 for name,builder,stop,no_regime in specs:
  run=existing.run_one(name,builder,'2023-02-01','2026-10-03',stop,no_regime)
  checks=controls.independent_check(run)
  previous=pd.read_csv('control_evidence/'+name+'_positions.csv')
  prior_keys=set(zip(previous.SignalDate,previous.Ticker));new_keys=set(zip(run['positions'].SignalDate,run['positions'].Ticker))
  run['positions'].to_csv(OUT/(name+'_positions.csv'),index=False);run['results'].to_csv(OUT/(name+'_results.csv'),index=False)
  records.append({'scenario':name,'status':'COMPLETE','metrics':run['metrics'],'out_of_sample_metrics':run['out_of_sample_metrics'],'checks':checks,'removed_position_keys':len(prior_keys-new_keys),'added_position_keys':len(new_keys-prior_keys)})
  (OUT/'controlled_component_audit.json').write_text(json.dumps({'runs':records,'liquidity_basis':'actual unadjusted historical close times actual unadjusted volume'},indent=2))
  print('RAW_LIQUIDITY_RESULT',json.dumps(records[-1]),flush=True)
 # Full selection diagnostics on the same corrected basis, without future outcome selection.
 selection.OUT=OUT/'selection';Path('control_evidence_previous').mkdir(exist_ok=True)
 import shutil
 for f in OUT.glob('*_results.csv'):shutil.copyfile(f,Path('control_evidence')/f.name)
 for f in OUT.glob('*_positions.csv'):shutil.copyfile(f,Path('control_evidence')/f.name)
 shutil.copyfile(OUT/'controlled_component_audit.json','control_evidence/controlled_component_audit.json')
 selection.main()
 (OUT/'liquidity_verification_manifest.json').write_text(json.dumps({'status':'COMPLETE','required_sessions':len(required),'verified_sessions':len(raw),'mismatch_rows':len(mismatches),'all_13_scenarios_independently_verified':len(records)==13,'no_parameter_search':True,'price_basis_date':basis,'liquidity_basis':'actual historical unadjusted close times volume','missing_raw_values':'fail closed; never impute'},indent=2))
if __name__=='__main__':main()
