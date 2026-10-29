"""Publish only the safe observed H3 export, without redeploying the dashboard."""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

BRANCH='h3-observed-snapshots'
ROOT=Path(__file__).resolve().parent


def git(*args,cwd=ROOT):
    return subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True,check=True,timeout=45).stdout.strip()


def publish(snapshot,previous_snapshot,durable_status,observer_status,manifest):
    path=Path(snapshot).resolve();data=json.loads(path.read_text())
    policy=json.loads((ROOT/'h3_forward_policy.json').read_text())
    for key in ('model','cohort','source_fingerprint'):
        if data.get(key)!=policy[key]:raise ValueError('Unrecognized observation identity')
    if data.get('live_approved') is not False or data.get('broker_orders_enabled') is not False:raise ValueError('Live flags must be false')
    if json.loads((ROOT/'vercel.json').read_text())['git']['deploymentEnabled'][BRANCH] is not False:
        raise ValueError('Data-branch deployments must be disabled')
    if durable_status!='success' or observer_status!='success':
        old=json.loads(Path(previous_snapshot).read_text()) if Path(previous_snapshot).exists() else None
        if old:
            old.update(generated_at=data['generated_at'],operations=data['operations']);data=old
        else:
            data.update(as_of=None,sessions=0,metrics=None,cost_cases={'15bp':None,'30bp':None},
                        cash_usd=None,receivables_usd=None,holdings=[],latest_decision=None,recent_trades=[],curve=[])
            data['validation'].update(observed_periods=0,remaining_periods=30,financial_gates_passed=False)
            for case in data['validation']['gates'].values():
                for gate in case:gate.update({'value':None,'pass':False})
        data['status']=data['validation']['status']='DATA_BLOCKED';data['pending_intentions']=None
        if durable_status!='success':data['operations']['errors'].append('Durable journal preservation did not complete; only the prior accepted record is displayed.')
        if observer_status!='success':data['operations']['errors'].append('Independent observation did not complete successfully; only the prior accepted record is displayed.')
    elif Path(manifest).exists():
        saved=json.loads(Path(manifest).read_text())
        data['journal_evidence']={k:saved[k] for k in ('paper_asset','paper_archive_sha256','previous_paper_asset','previous_paper_archive_sha256','workflow_run')}
    payload=json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)
    remote=git('ls-remote','--heads','origin','refs/heads/'+BRANCH)
    if remote:
        git('fetch','--no-tags','origin','refs/heads/'+BRANCH)
        base=git('rev-parse','FETCH_HEAD')
    else:base=git('rev-parse','HEAD')
    with tempfile.TemporaryDirectory(prefix='h3-publish-') as name:
        work=Path(name)/'work';git('worktree','add','--detach',str(work),base)
        try:
            destination=work/'public/data/h3.json';destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_text(payload)
            extra=[]
            if durable_status=='success' and observer_status=='success':
                from h3_display import export_account
                account_path=work/'public/data/h3-account.json'
                previous_account=json.loads(account_path.read_text()) if account_path.exists() else None
                account=export_account(path.parent,ROOT/'.portfolio_forward_cache',previous_account)
                account_path.write_text(json.dumps(account,ensure_ascii=False,indent=2,allow_nan=False))
                extra=['public/data/h3-account.json']
            # The first data-branch commit also carries its deployment opt-out.
            if not remote:shutil.copyfile(ROOT/'vercel.json',work/'vercel.json')
            git('add','public/data/h3.json',*extra,*(['vercel.json'] if not remote else []),cwd=work)
            if not git('diff','--cached','--name-only',cwd=work):return
            git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com',
                'commit','-m',f"H3 observed journal {os.getenv('GITHUB_RUN_ID','manual')} attempt {os.getenv('GITHUB_RUN_ATTEMPT','1')}",cwd=work)
            # Ordinary fast-forward only. A concurrent update rejects safely;
            # the next scheduled collection retries from its durable release.
            git('push','origin',f'HEAD:refs/heads/{BRANCH}',cwd=work)
            print(json.dumps({'branch':BRANCH,'commit':git('rev-parse','HEAD',cwd=work),'sessions':data['sessions'],'status':data['status']}))
        finally:git('worktree','remove','--force',str(work))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('snapshot','previous-snapshot','durable-status','observer-status','manifest'):p.add_argument('--'+name,required=True)
    a=p.parse_args();publish(a.snapshot,a.previous_snapshot,a.durable_status,a.observer_status,a.manifest)
