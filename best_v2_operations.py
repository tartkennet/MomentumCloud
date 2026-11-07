"""Read-only proof that default-branch paper scheduling is actually enabled."""
import json,os,subprocess,hashlib
from datetime import datetime,timezone
from pathlib import Path
from momentum_core_data import atomic_json

def verify(output):
    repo=os.environ['GITHUB_REPOSITORY']
    def api(path):return json.loads(subprocess.check_output(['gh','api','repos/'+repo+'/'+path],text=True))
    info=api('');workflow=api('actions/workflows/momentum_best_v2.yml')
    if workflow['state']!='active' or os.environ.get('GITHUB_REF')!='refs/heads/'+info['default_branch']:raise ValueError('V2_DEFAULT_BRANCH_AUTOMATION_NOT_ENABLED')
    source=Path('.github/workflows/momentum_best_v2.yml').read_text()
    schedules=['22 8,22 * * 1-5','52 14,15 * * 1-5']
    if any(x not in source for x in schedules):raise ValueError('V2_EXPECTED_SCHEDULE_MISSING')
    receipt=dict(status='PASS',enabled=True,workflow_id=workflow['id'],workflow_state=workflow['state'],default_branch=info['default_branch'],
        source_commit=os.environ['GITHUB_SHA'],verified_at=datetime.now(timezone.utc).isoformat(),schedules=schedules,workflow_sha256=hashlib.sha256(source.encode()).hexdigest())
    atomic_json(Path(output)/'operations.json',receipt)
    print('BEST_V2_OPERATIONS',json.dumps(receipt),flush=True)
if __name__=='__main__':verify('best_v2_output')
