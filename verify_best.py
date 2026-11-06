"""Explicit technical release gate; historical economic GO is not required."""
import argparse
import json
from pathlib import Path
from quality_forward import digest
import audit_best


def verify(folder):
    folder=Path(folder);r=json.loads((folder/'best-report.json').read_text())
    if r.get('technical_readiness',{}).get('status')!='PASS':
        raise ValueError('BEST_TECHNICAL_BLOCKED:'+','.join(r.get('errors',[])))
    s=json.loads((folder/'best-state.json').read_text());p=r['paper']
    assert r['population_audit']['status']=='PASS'
    assert r['diagnostics']['inventory']['complete'] is True
    assert r['diagnostics']['inventory']['processed_records']==r['diagnostics']['reference_records']
    assert r['diagnostics']['adv_truncation'] is False
    rows=(r['signal'].get('selection') or {}).get('rows',[])
    assert len(rows)==10 and len({x['cik'] for x in rows})==10
    assert all(x['ticker']!='SPY' and x['instrument_type']=='CS' for x in rows)
    assert p['live_approved'] is False and p['broker_orders_enabled'] is False
    assert p['initial_sek']>0 and p['capital_configuration']['initial_sek']==p['initial_sek']
    assert r['technical_readiness']['funded'] is True
    assert p['journal_sha256']==digest(s)
    audit_best.account(s,p)
    if not p['paper_started']:
        pending=s.get('pending') or {}
        assert pending.get('kind')=='MEMBERSHIP'
        buys=[o for o in pending['plan']['orders'] if o['side']=='BUY']
        assert len(buys)==10 and {o['ticker'] for o in buys}=={x['ticker'] for x in rows}
        assert all(type(o['quantity']) is int and o['quantity']>=1 for o in buys)
        assert not p['trades'] and not p['positions']
    result=dict(status='PASS',targets=[x['ticker'] for x in rows],initial_sek=p['initial_sek'],
        reference_records=r['diagnostics']['reference_records'],priced_liquid=r['diagnostics']['priced_liquid'],
        paper_started=p['paper_started'],live_approved=False)
    print('BEST_RELEASE_GATE',json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',required=True)
    verify(parser.parse_args().folder)
