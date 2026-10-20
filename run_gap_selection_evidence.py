"""Expose excluded candidates and dated gap evidence, without modifying selection."""
import json
from pathlib import Path
import pandas as pd
import backtest_momentum_v3 as engine
import run_v4_ablation_and_simple_candidate as existing
import run_relaxed_selection_audit as selection
OUT=Path('Momentum_gap_selection_evidence');OUT.mkdir(exist_ok=True)
cache,basis=engine.load_backtest_cache(engine.CACHE_FILE)
universes=engine.load_point_in_time_universe_cache(engine.UNIVERSE_CACHE_FILE)
raw=json.loads(Path('raw_evidence/raw_dollar_volume.json').read_text())
old=existing.history_for
def actual(t,latest,history):
 v=old(t,latest,history)
 if v is None:return None
 dollars=[raw[d][t] for d,g in history[:20] if engine.get_from_map(g,t) is not None and engine.get_from_map(g,t).get('volume') is not None]
 return (v[0],sum(dollars)/len(dollars)) if len(dollars)>=10 else None
existing.history_for=actual
days=sorted(cache);tickers=sorted({t for u in universes.values() for t in u})
gaps=engine.find_unverified_split_basis_tickers(cache,days,tickers,selection.split_events())
rows=[]
for period in pd.read_csv('raw_evidence/selection/relaxed_v4_results.csv').itertuples():
 s=period.SignalDate;r=selection.snapshot(s,False);latest=cache[s]
 for t,v in latest.items():
  if t in r:v['raw_signal_close']=r[t].get('c')
 history=[(d,cache[d]) for d in sorted((x for x in cache if x<=s),reverse=True)[:253]]
 excluded=engine.data_quality_exclusions_asof(gaps,s)
 for t in universes[s]:
  if t not in excluded:continue
  x=selection.diagnose(t,latest,history,r,excluded)
  if x['Reasons']:continue
  x.update({'SignalDate':s,'GapObservationsAsOfSignal':[v for v in gaps[t] if v[:10]<=s]})
  rows.append(x)
 print('GAP_SIGNAL_COMPLETE',s,flush=True)
(OUT/'otherwise_eligible_gap_excluded.json').write_text(json.dumps(rows,indent=2,allow_nan=False))
pd.DataFrame(rows).drop(columns=['GapObservationsAsOfSignal'],errors='ignore').to_csv(OUT/'otherwise_eligible_gap_excluded.csv',index=False)
(OUT/'manifest.json').write_text(json.dumps({'status':'COMPLETE','excluded_candidate_months':len(rows),'unique_tickers':len({x['Ticker'] for x in rows}),'purpose':'dated hypotheses requiring news/corporate-action verification; no rule changes'},indent=2))
