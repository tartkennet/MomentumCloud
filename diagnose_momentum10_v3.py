"""Descriptive saved-account diagnostics; future observations never feed selection."""
import json
import statistics
from collections import Counter
from pathlib import Path
import momentum_core as core
from momentum_core_data import atomic_json


def signal_risk(data,s):
    samples=[]
    for signal in s.targets:
        rows=signal['targets']
        if not rows:continue
        day=signal['date'];series=[];names={r['ticker']:r.get('name',r.get('company_name','')) for r in data.universe(day)}
        hints=Counter();corr=[];edges=[]
        for row in rows:
            t=row['ticker'];c=core.adjusted_history(data,day,t,64)
            series.append([c[i]/c[i+1]-1 for i in range(63)])
            name=names.get(t,'').upper()
            hint=('biotech/pharma name hint' if any(a in name for a in ('BIOSCIENCE','BIOPHARMA','THERAPEUT','PHARMA','LIFE SCIENCE')) else
                  'semiconductor name hint' if 'SEMICONDUCT' in name else 'unclassified')
            hints[hint]+=1
        for i in range(len(series)):
            for j in range(i):
                r=statistics.correlation(series[i],series[j]);corr.append(r)
                if r>=.7:edges.append([rows[i]['ticker'],rows[j]['ticker']])
        samples.append(dict(date=day,mean_pair_correlation=statistics.fmean(corr),max_pair_correlation=max(corr),
            edges_ge_070=edges,unverified_name_hints=dict(hints),
            median_signal_return_1m=statistics.median(r['return_1m'] for r in rows)))
    return dict(selections=samples,classification_warning='Name hints are unverified, incomplete industry descriptions, NOT SIC/GICS or selection inputs.',
        max_biopharma_named_slots=max((r['unverified_name_hints'].get('biotech/pharma name hint',0) for r in samples),default=0),
        max_mean_pair_correlation=max((r['mean_pair_correlation'] for r in samples),default=None))


def diagnose(data,root,out):
    from types import SimpleNamespace
    result={}
    for variant in ('M1','M3','Q10'):
        state=json.loads((root/f'{variant}_5_last_quote_15/strategy.json').read_text())
        result[variant]=signal_risk(data,SimpleNamespace(**state))
    fields=Counter(k for r in data.universe(data.sessions[0]) for k in r)
    result['first_pit_universe_fields']=dict(fields)
    result['industry_classification_verified']=False
    result['method']='Read completed v2 selections, cached pre-signal returns and PIT issuer names. No repeated strategy replay; no future selection inputs.'
    atomic_json(out/'baseline_diagnostic.json',result)
    return result
