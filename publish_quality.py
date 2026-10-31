"""Publish a durable, append-only Quality paper record, separately from H3."""
import argparse,json,os,shutil,tempfile
from pathlib import Path
from publish_h3_snapshot import git
from quality_forward import digest

BRANCH='quality-observed-snapshots'


def publish(folder,manifest):
    folder=Path(folder).resolve();report=json.loads((folder/'quality.json').read_text());meta=json.loads(Path(manifest).read_text())
    assert report['live_approved'] is False and report['broker_orders_enabled'] is False
    assert json.loads(Path('vercel.json').read_text())['git']['deploymentEnabled'][BRANCH] is False
    remote=git('ls-remote','--heads','origin','refs/heads/'+BRANCH)
    if remote:git('fetch','--no-tags','origin','refs/heads/'+BRANCH);base=git('rev-parse','FETCH_HEAD')
    else:base=git('rev-parse','HEAD')
    with tempfile.TemporaryDirectory(prefix='quality-publish-') as name:
        work=Path(name)/'work';git('worktree','add','--detach',str(work),base)
        try:
            journal=work/'quality-journal';journal.mkdir(exist_ok=True)
            key=os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1');record=journal/(key+'.json')
            if record.exists():raise ValueError('Observation IDs are immutable')
            state=json.loads((folder/'state.json').read_text()) if (folder/'state.json').exists() else None
            prevpath=work/'quality-state.json';old=json.loads(prevpath.read_text()) if prevpath.exists() else None
            if old:
                assert state and state['previous_state_sha256']==digest(old),'Journal compare-and-swap failed'
                for k in ('strategy','benchmark'):
                    for f in ('trades','equity'):assert state[k][f][:len(old[k][f])]==old[k][f]
                for f in ('decisions','event_journal','opening_quotes','gaps'):assert state[f][:len(old[f])]==old[f]
            record.write_text(json.dumps(dict(manifest=meta,state=state,report=report),allow_nan=False))
            if state:prevpath.write_text(json.dumps(state,allow_nan=False))
            report['journal_evidence']=dict(record=key,previous_state_sha256=state.get('previous_state_sha256') if state else None,**meta)
            (work/'public/data/quality-earnings.json').write_text(json.dumps(report,ensure_ascii=False,allow_nan=False))
            (work/'quality-current-manifest.json').write_text(json.dumps(meta))
            if not remote:shutil.copyfile('vercel.json',work/'vercel.json')
            git('add','quality-journal','quality-current-manifest.json','public/data/quality-earnings.json',*(['quality-state.json'] if state else []),*(['vercel.json'] if not remote else []),cwd=work)
            git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com','commit','-m','Quality prospective observation '+key,cwd=work)
            git('push','origin','HEAD:refs/heads/'+BRANCH,cwd=work)
            print(json.dumps(dict(branch=BRANCH,status=report['status'],sessions=report['sessions'],record=key)))
        finally:git('worktree','remove','--force',str(work))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--folder',required=True);p.add_argument('--manifest',required=True);a=p.parse_args();publish(a.folder,a.manifest)
