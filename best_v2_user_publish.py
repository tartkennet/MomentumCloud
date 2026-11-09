"""Immutable prospective BEST observations; no writes to legacy accounts."""
import argparse
import json
import os
import tempfile
from pathlib import Path
from publish_h3_snapshot import git
from quality_forward import digest
from momentum_core_data import atomic_json
import audit_best_v2_user as audit_best
import best_v2_strategy as best_strategy

BRANCH='best-v2-user-snapshots'


def publish(folder,manifest):
    folder=Path(folder).resolve();report=json.loads((folder/'best-v2-report.json').read_text());meta=json.loads(Path(manifest).read_text())
    assert report['model']==best_strategy.MODEL and report['account_id']=='best-v2-user-simulation-2026-11-09'
    assert json.loads(Path('vercel.json').read_text())['git']['deploymentEnabled'][BRANCH] is False
    state=json.loads((folder/'best-v2-state.json').read_text()) if (folder/'best-v2-state.json').exists() else None
    remote=git('ls-remote','--heads','origin','refs/heads/'+BRANCH)
    if remote:git('fetch','--no-tags','origin','refs/heads/'+BRANCH);base=git('rev-parse','FETCH_HEAD')
    else:base=git('rev-parse','HEAD')
    with tempfile.TemporaryDirectory(prefix='best-publish-') as tmp:
        work=Path(tmp)/'work';git('worktree','add','--detach',str(work),base)
        try:
            previous=work/'best-v2-state.json'
            if previous.exists():
                old=json.loads(previous.read_text());assert state and state['previous_state_sha256']==digest(old)
                assert state['initial_sek']==old['initial_sek'] and state['capital_configuration']==old['capital_configuration']
                for account in ('strategy','benchmark'):
                    for field in ('trades','equity'):assert state[account][field][:len(old[account][field])]==old[account][field]
                for field in ('decisions','event_journal','opening_quotes','gaps','unfilled_orders','cancelled_intentions','execution_attempts','intraday_observations','execution_policy_journal'):
                    if field not in old:continue
                    assert state[field][:len(old[field])]==old[field]
            if state:
                assert report['paper']['journal_sha256']==digest(state)
                if report['technical_readiness']['status']=='PASS':audit_best.audit_account(state)
                atomic_json(previous,state)
            journal=work/'best-v2-journal';journal.mkdir(exist_ok=True)
            key=os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1');record=journal/(key+'.json')
            assert not record.exists()
            report['journal_evidence']=dict(record=key,**meta)
            atomic_json(record,dict(manifest=meta,report=report,state=state))
            atomic_json(work/'public/data/momentum-best-v2.json',report)
            atomic_json(work/'best-v2-current-manifest.json',meta)
            git('add','best-v2-journal','public/data/momentum-best-v2.json','best-v2-current-manifest.json',*(['best-v2-state.json'] if state else []),cwd=work)
            git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit','-m','BEST prospective observation '+key,cwd=work)
            git('push','origin','HEAD:refs/heads/'+BRANCH,cwd=work)
        finally:git('worktree','remove','--force',str(work))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--manifest',required=True)
    a=p.parse_args();publish(a.folder,a.manifest)
