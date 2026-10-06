"""Controlled diagnostics of existing rules; no search, optimisation or new model."""
import gzip
import hashlib
import itertools
import json
import logging
import math
import os
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from pathlib import Path

import pandas as pd
import backtest_momentum_v3 as engine
import run_v4_ablation_and_simple_candidate as existing
from momentum_master_v3 import PolygonClient

OUT=Path('Momentum_component_audit')
SNAPSHOT=Path('audit_request_snapshot')


def redact_response(value):
    if isinstance(value,dict):
        return {k:redact_response(v) for k,v in value.items() if k.lower() not in {'apikey','api_key','authorization'}}
    if isinstance(value,list):
        return [redact_response(v) for v in value]
    if isinstance(value,str) and 'apikey=' in value.lower():
        url=urlparse(value)
        query=[(k,v) for k,v in parse_qsl(url.query,keep_blank_values=True) if k.lower()!='apikey']
        return urlunparse(url._replace(query=urlencode(query)))
    return value


def freeze_provider():
    """Persist every successful provider response once and reuse it across runs."""
    original=PolygonClient._get
    def frozen(self,path,params=None):
        payload=json.dumps({'path':path,'params':params},sort_keys=True,separators=(',',':'))
        digest=hashlib.sha256(payload.encode()).hexdigest()
        filename=SNAPSHOT/(digest+'.json.gz')
        if filename.exists():
            with gzip.open(filename,'rt') as f:
                return json.load(f)
        value=redact_response(original(self,path,params))
        tmp=filename.with_suffix('.tmp')
        with gzip.open(tmp,'wt') as f:
            json.dump({'request':json.loads(payload),'response':value},f,separators=(',',':'))
        tmp.replace(filename)
        return value
    # Stored files retain the request as well as its response for reproducibility.
    def cached(self,path,params=None):
        payload=json.dumps({'path':path,'params':params},sort_keys=True,separators=(',',':'))
        filename=SNAPSHOT/(hashlib.sha256(payload.encode()).hexdigest()+'.json.gz')
        if filename.exists():
            with gzip.open(filename,'rt') as f:
                return json.load(f)['response']
        return frozen(self,path,params)
    PolygonClient._get=cached


def independent_check(run,reference=None):
    results=run['results'];positions=run['positions']
    if results.SignalDate.duplicated().any():
        raise AssertionError('Duplicate monthly periods')
    equity=spy=1.0
    for row in results.itertuples():
        group=positions.loc[positions.SignalDate==row.SignalDate]
        if len(group):
            if len(group)!=15 or group.Ticker.duplicated().any():
                raise AssertionError('Invalid equal-weight portfolio')
            if (group.ExitDate>row.ExitDate).any() or (group.EntryDate<row.EntryDate).any():
                raise AssertionError('Execution outside monthly period')
            gross=sum(float(x.GrossReturn_pct)/int(x.TopN) for x in group.itertuples())
            net=gross-engine.ROUND_TRIP_COST_PCT
        else:
            gross=net=0.0
        if abs(gross-row.GrossReturn_pct)>1e-7 or abs(net-row.NetReturn_pct)>1e-7:
            raise AssertionError('Independent position aggregation failed')
        equity*=1+net/100;spy*=1+row.SPYReturn_pct/100
    if abs((equity-1)*100-run['metrics']['TotalReturn_pct'])>1e-7:
        raise AssertionError('Independent capital aggregation failed')
    if reference is not None:
        cols=['SignalDate','EntryDate','ExitDate','GrossReturn_pct','NetReturn_pct','SPYReturn_pct','RiskRegime']
        pd.testing.assert_frame_equal(results[cols].reset_index(drop=True),reference[cols].reset_index(drop=True),check_dtype=False,check_exact=False,rtol=1e-7,atol=1e-7)
    return {'independent_position_and_capital_aggregation':'PASS','baseline_reproduction':'PASS' if reference is not None else 'NOT_APPLICABLE','periods':len(results),'spy_price_return_pct':(spy-1)*100}


def factorial_contributions(values):
    """Shapley allocation of the three-rule delta, including interactions."""
    factors=['stop','regime','extension'];answer={}
    for j,label in enumerate(factors):
        contribution=0.0
        others=[i for i in range(3) if i!=j]
        for subset in itertools.product([False,True],repeat=2):
            key=[False]*3
            for i,v in zip(others,subset):key[i]=v
            size=sum(key)
            weight=math.factorial(size)*math.factorial(2-size)/math.factorial(3)
            without=tuple(key);key[j]=True
            contribution+=weight*(values[tuple(key)]-values[without])
        answer[label+'_keeping_effect_pp']=contribution
    answer['all_rules_minus_none_pp']=values[(True,True,True)]-values[(False,False,False)]
    if abs(sum(answer[k] for k in answer if k.endswith('keeping_effect_pp'))-answer['all_rules_minus_none_pp'])>1e-7:
        raise AssertionError('Factorial contributions do not reconcile')
    return answer


def main():
    OUT.mkdir(exist_ok=True);SNAPSHOT.mkdir(exist_ok=True)
    freeze_provider()
    flags={'m12':True,'m6':True,'vol':True,'extension':True}
    specs=[('v4_baseline',existing.v4_builder(flags),10.0,False,(True,True,True),'v4')]
    for stop,regime,extension in itertools.product([False,True],repeat=3):
        if (stop,regime,extension)==(True,True,True):continue
        name=f'v4_stop_{int(stop)}_regime_{int(regime)}_extension_{int(extension)}'
        specs.append((name,existing.v4_builder({**flags,'extension':extension}),10.0 if stop else None,not regime,(stop,regime,extension),None))
    for factor in ['m12','m6','vol']:
        specs.append(('v4_without_'+factor,existing.v4_builder({**flags,factor:False}),10.0,False,None,None))
    specs.extend([('simple_baseline',existing.simple_builder,None,False,None,'simple'),('simple_without_regime',existing.simple_builder,None,True,None,None)])
    metadata={'scope':'existing-rule diagnostic counterfactuals; not new strategy candidates','start':'2023-02-01','end':'2026-10-03','data':'successful provider responses frozen on first access','cost_model':'existing fixed 0.30 pct per invested month','limits':['price returns exclude dividends','SIC is not GICS','historical liquidity split basis unresolved','gap heuristic remains unverified'],'runs':[]}
    values={};allruns={}
    for name,builder,stop,no_regime,key,reference_name in specs:
        logging.warning('CONTROLLED_AUDIT_START %s',name)
        try:
            run=existing.run_one(name,builder,metadata['start'],metadata['end'],stop,no_regime)
            ref=pd.read_csv(Path('audit_corrected')/(reference_name+'_results.csv')) if reference_name else None
            checks=independent_check(run,ref)
            run['results'].to_csv(OUT/(name+'_results.csv'),index=False)
            run['positions'].to_csv(OUT/(name+'_positions.csv'),index=False)
            record={'scenario':name,'status':'COMPLETE','metrics':run['metrics'],'out_of_sample_metrics':run['out_of_sample_metrics'],'checks':checks}
            allruns[name]=run
            if key is not None:values[key]=run['metrics']['TotalReturn_pct']
        except Exception as exc:
            # Continue independent diagnostics without manufacturing missing results.
            record={'scenario':name,'status':'FAILED','error_type':type(exc).__name__,'reason':str(exc) if isinstance(exc,AssertionError) else 'Execution blocked; inspect workflow logs'}
            logging.exception('CONTROLLED_AUDIT_FAILED %s',name)
        metadata['runs'].append(record)
        (OUT/'controlled_component_audit.json').write_text(json.dumps(metadata,indent=2,allow_nan=False))
        print('CONTROLLED_AUDIT_RESULT '+json.dumps(record,allow_nan=False),flush=True)
    if len(values)==8:
        metadata['v4_three_rule_shapley']=factorial_contributions(values)
        metadata['shapley_definition']='Average marginal keeping effect across all six rule orders. Allocates all-versus-none delta, not the full SPY gap. No generalisation beyond this sample.'
    if 'v4_baseline' in allruns:
        base=allruns['v4_baseline'];baseline=set(zip(base['positions'].SignalDate,base['positions'].Ticker))
        alt=allruns.get('v4_stop_1_regime_1_extension_0')
        if alt:
            selected=alt['positions'].loc[[(r.SignalDate,r.Ticker) not in baseline for r in alt['positions'].itertuples()]].copy()
            selected.to_csv(OUT/'corrected_low_extension_excluded_lots.csv',index=False)
            metadata['corrected_low_extension_excluded']={'lots':len(selected),'positive':int((selected.GrossReturn_pct>0).sum()),'closed_ge50':int((selected.GrossReturn_pct>=50).sum()),'closed_ge100':int((selected.GrossReturn_pct>=100).sum())}
    metadata['snapshot_files']=len(list(SNAPSHOT.glob('*.json.gz')))
    (OUT/'controlled_component_audit.json').write_text(json.dumps(metadata,indent=2,allow_nan=False))
    pd.DataFrame([{'scenario':x['scenario'],**x.get('metrics',{}),'status':x['status']} for x in metadata['runs']]).to_csv(OUT/'component_summary.csv',index=False)
    if any(x['status']!='COMPLETE' for x in metadata['runs']):
        raise RuntimeError('Some diagnostics failed; successful evidence was retained')

if __name__=='__main__':
    main()
