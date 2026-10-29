"""Separate prospective H3 paper cohort; no broker or Buy Now integration."""
import argparse
import copy
import hashlib
import json
import os
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path

import momentum_core as core
import run_momentum_core as base
import run_core_normalized_research as study
from momentum_core_data import atomic_json
from research_core_actions import supplement
from research_core_ledger import STOCK_COMPLETIONS,CASH_COMPLETIONS,DISTRIBUTIONS
from research_portfolio_regime import MODEL,PortfolioLedger,select_targets
from run_core_risk_research import DailyEvents,replay
from run_portfolio_regime import EXTRA_FILES

ROOT=Path(__file__).resolve().parent
START='2026-10-29'
COHORT='portfolio-global-regime-forward-v1-20261029'
_CORE_FINGERPRINT,_CORE_DATA=base.source_fingerprint,base.CoreData


def development_identity():
    hashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in study.FILES+EXTRA_FILES}
    identity=hashlib.sha256(json.dumps({'core':_CORE_FINGERPRINT(),'files':hashes},sort_keys=True).encode()).hexdigest()
    return hashlib.sha256((identity+MODEL).encode()).hexdigest()


def qualify():
    result=json.loads((ROOT/'docs/CORE_PORTFOLIO_H3_RESULTS_20261029.json').read_text())
    if (result['model']!=MODEL or not result['all_attempts_completed'] or len(result['attempts'])!=40
            or result['study_fingerprint']!=development_identity()
            or any(a['status']!='COMPLETE' or a['accounting_audit']!='PASS'
                   or a['selection_audit']['status']!='PASS' or core.gates(a['metrics'])!=a['gates']
                   or not all(g['pass'] for g in a['gates'])
                   for a in result['attempts'])):
        raise core.DataBlocked('The frozen candidate has not passed all 40 unchanged historical gate/audit cases')
    return result['study_fingerprint']


def fingerprint():
    value={'cohort':COHORT,'start':START,'verified_development':development_identity(),
           'adapter':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'protocol':hashlib.sha256((ROOT/'docs/CORE_PORTFOLIO_FORWARD_PROTOCOL_20261029.md').read_bytes()).hexdigest()}
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def require_fresh(data):
    if len(data.sessions)>1:
        raise core.DataBlocked('Missed prospective sessions; retrospective intermediate intentions are forbidden')
    if data.sessions and datetime.now(timezone.utc).hour>=12:
        raise core.DataBlocked('New paper intentions must be recorded before 12:00 UTC, ahead of the next US open')


@contextmanager
def paper_engine():
    names=('MODEL','CONFIG','source_fingerprint','CoreData','replay','resume_paper')
    saved={n:getattr(base,n) for n in names};old_selector=core.select_targets
    config=replace(core.CONFIG,model=MODEL)
    def data_adapter(*args,**kwargs):
        data=supplement(DailyEvents(_CORE_DATA(*args,**kwargs)))
        data.source.cash_actions=dict(data.source.cash_actions,**copy.deepcopy(CASH_COMPLETIONS))
        data.cash_actions=copy.deepcopy(data.source.cash_actions)
        data.source.stock_actions=dict(data.source.stock_actions,**copy.deepcopy(STOCK_COMPLETIONS))
        data.distributions=copy.deepcopy(DISTRIBUTIONS)
        # No PLYA suspension occurs in this prospective cohort. Missing future
        # tradable quotes still block; no historical halt mark becomes a fill.
        data.halt_marks={}
        require_fresh(data)
        return data
    def initial(data,setting=None):
        require_fresh(data)
        return replay(data,setting or config,cls=PortfolioLedger)
    def resume(data,checkpoint,setting=None,*,stress=False):
        require_fresh(data);prefix='stress_' if stress else ''
        previous=checkpoint[prefix+'strategy'],checkpoint[prefix+'benchmark']
        if previous[0]['last_date']!=previous[1]['last_date']:
            raise core.DataBlocked('Strategy and benchmark prefix dates differ')
        s,b,m,p=replay(data,setting or config,cls=PortfolioLedger,checkpoint=previous)
        base.verify_forward_prefix(s,previous[0],s.last_date)
        base.verify_forward_prefix(b,previous[1],b.last_date)
        return s,b,m,p
    base.MODEL,base.CONFIG=MODEL,config
    base.source_fingerprint,base.CoreData=fingerprint,data_adapter
    base.replay,base.resume_paper=initial,resume
    core.select_targets=select_targets
    try:yield
    finally:
        core.select_targets=old_selector
        for n,v in saved.items():setattr(base,n,v)


def run(end,output,cache,*,offline=False):
    root=Path(output);root.mkdir(parents=True,exist_ok=True)
    checkpoint_path=root/'Momentum_core_paper_checkpoint.json'
    old_checkpoint=json.loads(checkpoint_path.read_text()) if checkpoint_path.exists() else None
    try:
        verified=qualify();identity_path=root/'Momentum_core_paper_identity.json'
        identity={'model':MODEL,'cohort':COHORT,'start':START,'source_fingerprint':fingerprint(),
                  'verified_development_fingerprint':verified,'frozen_at':datetime.now(timezone.utc).isoformat(),
                  'source_commit':os.getenv('MODEL_SOURCE_SHA',os.getenv('GITHUB_SHA')),
                  'live_approved':False,'broker_orders_enabled':False}
        if identity_path.exists():
            old=json.loads(identity_path.read_text())
            if old['source_fingerprint']!=identity['source_fingerprint']:
                raise core.DataBlocked('Forward source identity changed; preserve the old frozen cohort')
        else:atomic_json(identity_path,identity)
        decision_path=root/'Momentum_core_decision.json'
        if decision_path.exists():
            prior=json.loads(decision_path.read_text())
            if ((end<START and prior['status']=='PAPER_WAITING_FOR_SESSIONS')
                or (old_checkpoint and old_checkpoint['strategy']['last_date']==end
                    and prior['status'] in ('PAPER_COLLECTING','PAPER_ONLY','NO_GO'))):
                return prior
        latest=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
        if end>=START and end!=latest:
            raise core.DataBlocked('Record only the latest completed UTC date; past paper reconstruction is forbidden')
        with paper_engine():
            result=base.run(START,end,output,cache,mode='paper',offline=offline)
        if result['status']!='PAPER_WAITING_FOR_SESSIONS' and datetime.now(timezone.utc).hour>=12:
            raise core.DataBlocked('Paper recording finished after the prospective intention deadline')
        return result
    except Exception as exc:
        # Keep the last accepted prefix if a post-run deadline check fails.
        if checkpoint_path.exists():
            current=json.loads(checkpoint_path.read_text())
            if current!=old_checkpoint:
                atomic_json(root/'Momentum_core_rejected_checkpoint.json',current)
                if old_checkpoint is None:checkpoint_path.unlink()
                else:atomic_json(checkpoint_path,old_checkpoint)
        message=str(exc)
        secret=os.getenv('POLYGON_API_KEY')
        if secret:message=message.replace(secret,'[REDACTED]')
        error={'model':MODEL,'cohort':COHORT,'status':'DATA_BLOCKED','error':message,
               'live_approved':False,'broker_orders_enabled':False}
        atomic_json(root/'Momentum_core_decision.json',error)
        atomic_json(root/'Momentum_core_paper_orders.json',dict(error,intentions_for_next_observed_session=None))
        raise core.DataBlocked(message) from None


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--end',default=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat())
    p.add_argument('--output-dir',default='portfolio_forward_results');p.add_argument('--cache-dir',default='.portfolio_forward_cache')
    p.add_argument('--offline',action='store_true');a=p.parse_args()
    run(a.end,a.output_dir,a.cache_dir,offline=a.offline)
