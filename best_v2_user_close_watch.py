"""Keep an already-started afternoon run alive until the NYSE close is published.

No market credentials and no journal writes: dispatch the existing audited workflow.
The account job has a separate lock so this wait cannot block intraday updates.
"""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import exchange_calendars
import pandas as pd

NY = ZoneInfo('America/New_York')


def plan(now):
    calendar = exchange_calendars.get_calendar('XNYS')
    day = now.astimezone(NY).date().isoformat()
    if not calendar.is_session(day):
        return dict(status='EXCHANGE_CLOSED',session=day)
    due = (calendar.session_close(day)+pd.Timedelta(minutes=15)).to_pydatetime()
    wait = max(0,(due-now).total_seconds())
    # At most 4.5h waiting + three bounded 20-minute child runs fits a 355m job.
    return dict(status='TOO_EARLY' if wait>270*60 else 'WATCH',session=day,
                due=due.isoformat(),wait_seconds=wait)


def published(report,day):
    return (report.get('price_as_of')==day and not report.get('errors')
            and report.get('technical_readiness',{}).get('status')=='PASS'
            and report.get('paper',{}).get('valuation_as_of')==day
            and report.get('paper',{}).get('statistics_audit',{}).get('status')=='PASS')


def gh(*args):
    return subprocess.check_output(['gh',*args],text=True,timeout=45)


def read_report(repo):
    path=f'repos/{repo}/contents/public/data/momentum-best-v2.json?ref=best-v2-user-snapshots'
    return json.loads(gh('api',path,'-H','Accept: application/vnd.github.raw+json'))


def dispatch(repo,day,request_id):
    gh('api',f'repos/{repo}/actions/workflows/best_v2_user.yml/dispatches',
       '--method','POST','-f','ref=main','-f',f'inputs[expected_session]={day}',
       '-f','inputs[mode]=update','-f',f'inputs[request_id]={request_id}')


def child_status(repo,request_id):
    runs=json.loads(gh('api',f'repos/{repo}/actions/workflows/best_v2_user.yml/runs?event=workflow_dispatch&per_page=30'))
    matches=[r for r in runs['workflow_runs'] if r['display_title']=='BEST v2 '+request_id]
    if not matches:return None
    run=matches[0]
    return dict(id=run['id'],status=run['status'],conclusion=run['conclusion'])


def watch(repo,request_id,now=lambda:datetime.now(timezone.utc),sleep=time.sleep,
          read=read_report,start=dispatch,status=child_status,refresh=False):
    target=plan(now())
    print('CLOSE_WATCH_PLAN',json.dumps(target),flush=True)
    if target['status']!='WATCH':return target
    due=datetime.fromisoformat(target['due'])
    while now()<due:
        sleep(max(0,min(60,(due-now()).total_seconds())))
        print('CLOSE_WATCH_WAIT',json.dumps(dict(session=target['session'],due=target['due'])),flush=True)
    day=target['session']
    if published(read(repo),day) and not refresh:
        print('CLOSE_WATCH_ALREADY_VERIFIED',day,flush=True)
        return dict(status='ALREADY_VERIFIED',session=day)
    for attempt in range(1,4):
        child=request_id+'-'+str(attempt)
        start(repo,day,child)
        print('CLOSE_WATCH_DISPATCH',json.dumps(dict(session=day,request_id=child)),flush=True)
        deadline=now()+timedelta(minutes=20)
        while now()<deadline:
            result=status(repo,child)
            if result and result['status']=='completed':
                if result['conclusion']=='success' and published(read(repo),day):
                    proof=dict(status='VERIFIED',session=day,run=result['id'])
                    print('CLOSE_WATCH_VERIFIED',json.dumps(proof),flush=True)
                    return proof
                print('CLOSE_WATCH_CHILD_FAILED',json.dumps(result),flush=True)
                break
            sleep(30)
        else:
            # A queued/running child must not be duplicated indefinitely.
            raise RuntimeError('CLOSE_WATCH_CHILD_TIMEOUT')
        if attempt<3:sleep(60)
    raise RuntimeError('CLOSE_VALUATION_NOT_PUBLISHED')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan-at',help='Read-only clock test; never dispatches or waits.')
    args=parser.parse_args()
    if args.plan_at:print(json.dumps(plan(datetime.fromisoformat(args.plan_at))))
    else:watch(os.environ['GITHUB_REPOSITORY'],'close-'+os.environ['GITHUB_RUN_ID'],
               refresh=os.getenv('BEST_V2_CLOSE_WATCH_REFRESH')=='true')
