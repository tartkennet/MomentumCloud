"""Re-use authenticated original observations for the registered data alternative; no price/fund requests."""
import argparse
import copy
import gzip
import hashlib
import json
import socket
from datetime import datetime,timezone
from pathlib import Path
from quality_sources import DataUnavailable
from quality_fundamentals import parse_original
from quality_audit import audit_fundamental,audit_selection,audit_plan
from quality_strategy import MODEL,PARAMETERS,choose,plan_orders,division
from momentum_core_data import atomic_json
from run_core_risk_research import make_data
from research_core_actions import supplement
from audit_core_normalized import closes_at


def recheck(root,out,cache=None):
    root=Path(root);out=Path(out);out.mkdir(exist_ok=True,parents=True);prior=json.loads((root/'quality.json').read_text());r=copy.deepcopy(prior)
    r.update(model=MODEL,generated_at=datetime.now(timezone.utc).isoformat(),reused_source_run='41210207368',status='RECHECKING',targets=[],proposed_orders=None,paper_start_permit=False,parameters=PARAMETERS)
    files={}
    for p in (root/'originals').glob('*.json'):
        obj=json.loads(p.read_text());files[obj['filing']['accession_number']]=(obj,p.with_name(obj['xml_asset']))
    rows=[]
    for old in prior['candidates']:
        row=copy.deepcopy(old)
        if old['data_status']=='OUT_OF_SCOPE_INDUSTRY':rows.append(row);continue
        receipt=next((v for v in files.values() if any(str(e.get('company_data',{}).get('cik','')).zfill(10)==row['cik'] for e in v[0]['filing']['entities'] if e.get('relation')=='filer')),None)
        if receipt is None:raise ValueError('Missing previously archived original')
        metadata,path=receipt;raw=gzip.decompress(path.read_bytes())
        entity=next(e['company_data'] for e in metadata['filing']['entities'] if e.get('relation')=='filer' and str(e['company_data'].get('cik','')).zfill(10)==row['cik'])
        row['sic']=str(entity.get('sic','')).zfill(4);row['division']=division(row['sic'])
        try:
            f=parse_original(raw,metadata,row['cik'],r['generated_at']);a=audit_fundamental(raw,metadata,f,row['cik'],r['generated_at'])
            row.update(fundamental=f,fundamental_audit=a,data_status='VERIFIED',resolved=True);row.pop('reason',None)
        except (DataUnavailable,AssertionError,ValueError) as e:row.update(data_status='DATA_GAP',resolved=False,reason=str(e) if isinstance(e,DataUnavailable) else type(e).__name__);row.pop('fundamental',None)
        rows.append(row)
    valid=[x for x in rows if x['data_status']=='VERIFIED'];coverage=sum(x['resolved'] for x in rows)/len(rows)
    nav=prior['initial_usd'];targets=choose(valid,nav);a=audit_selection(valid,targets,nav);plan=None
    try:plan=plan_orders(targets,{},nav,nav) if targets else None
    except ValueError as e:r['selection_block']=str(e)
    order=audit_plan(targets,plan,{},nav,nav,{}) if plan else None
    price_audit={'status':'NOT_RUN_LOCAL_CACHE_UNAVAILABLE'}
    if cache:
        from run_core_normalized_research import verify_inputs
        assert verify_inputs(cache,root/'base_manifest.json')==prior['original_input_manifest']
        data=supplement(make_data(cache,prior['price_as_of'],True));spy=closes_at(data,prior['price_as_of'],'SPY',253)
        for t in targets:
            c=closes_at(data,prior['price_as_of'],t['ticker'],253)
            assert abs(t['relative_strength']-((c[0]/c[126])/(spy[0]/spy[126])-1))<1e-10
            assert c[0]>sum(c[:200])/200 and c[0]==t['price_usd']
        price_audit=dict(status='PASS',selected=len(targets),independent_code=True)
    permit=coverage>=.9 and len(targets)==10 and r['risk_on'] and order is not None and price_audit['status']=='PASS'
    r.update(candidates=sorted(rows,key=lambda x:x['ticker']),coverage=coverage,qualified_count=sum(x['fundamental']['qualified'] for x in valid),targets=targets,
        audits=dict(fundamentals_checked=len(valid),selection=a,orders=order,prices=price_audit),proposed_orders=plan,
        status='PAPER_READY_AWAITING_SESSION' if permit else 'DATA_BLOCKED' if coverage<.9 or price_audit['status']!='PASS' else 'SELECTION_BLOCKED',paper_start_permit=permit,
        historical_metrics=None,paper_metrics=None,paper_started=False,sessions=0,positions=[],trades=[])
    r['source_files']={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ('quality_sources.py','quality_fundamentals.py','quality_strategy.py','quality_audit.py','collect_quality.py','quality_forward.py','docs/QUALITY_EARNINGS_PROTOCOL_20261031.md')}
    atomic_json(out/'quality.json',r)
    print(json.dumps(dict(status=r['status'],coverage=coverage,qualified=r['qualified_count'],targets=[x['ticker'] for x in targets],price_audit=price_audit)),flush=True)
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--cache');a=p.parse_args()
    def offline(*args,**kw):raise RuntimeError('Network forbidden in saved-source recheck')
    socket.socket.connect=offline;socket.create_connection=offline
    recheck(a.input,a.output,a.cache)
