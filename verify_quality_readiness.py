"""Read-only operational audit. Never writes to a paper state or order queue."""
import argparse,json,math
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from quality_forward import digest,opening
from quality_account_audit import audit_account
from run_quality_forward import fingerprint


def check(state,report):
    assert state['model_fingerprint']==fingerprint(),'FROZEN_SOURCE_CHANGED'
    assert report['live_approved'] is False and report['broker_orders_enabled'] is False
    assert report['initial_sek']==20000
    assert math.isclose(state['initial_usd']*state['initial_fx']['usdsek'],20000,abs_tol=1e-7)
    audits={k:audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
    s=state['strategy'];p=state.get('pending');plan=None
    if p and p.get('kind')=='MEMBERSHIP':
        h=dict(p);saved=h.pop('sha256');assert saved==digest(h)
        orders=p['plan']['orders'];targets={r['ticker']:r for r in p['targets']}
        assert len(targets)==10 and len({r['cik'] for r in targets.values()})==10
        assert 'SPY' not in targets
        buys=[o for o in orders if o['side']=='BUY'];assert all(o['ticker'] in targets for o in buys)
        assert all(type(o['quantity']) is int and o['quantity']>=1 for o in orders)
        principal=sum(o['quantity']*o['limit'] for o in buys)
        costs=lambda reserve:sum(max(1.,o['quantity']*o['limit']*.0025)+o['quantity']*o['limit']*(.0025+reserve) for o in buys)
        worst=principal+costs(.0015);stress=principal+costs(.003)
        budget=s['cash']+p['plan'].get('sale_reserve_usd',0)
        assert math.isclose(worst,p['plan']['reserved_cash_usd'],abs_tol=1e-7)
        assert worst<=budget+1e-8
        plan=dict(status='PASS',created_at=p['created_at'],signal_date=p['signal_date'],tickers=list(sorted(targets)),order_count=len(orders),shares=sum(o['quantity'] for o in buys),
            principal_usd=principal,cost_reserve_usd=costs(.0015),total_reserve_usd=worst,cash_after_limits_usd=budget-worst,
            initial_fx_usdsek=state['initial_fx']['usdsek'],reserve_at_initial_fx_sek=worst*state['initial_fx']['usdsek'],cash_at_initial_fx_sek=(budget-worst)*state['initial_fx']['usdsek'],
            stress_30bp_reserve_usd=stress,stress_funded=stress<=budget,orders=orders,
            limitation='Budget feasibility at committed caps, not a guarantee of next-open execution or retail broker availability.')
    if not s['trades']:
        assert not s['shares'] and not s['equity'] and s['fees']==0
        assert not report['paper_started'] and not report['positions'] and not report['trades'] and report['sessions']==0
        assert report['paper_metrics'] is None
        assert math.isclose(report['nav_sek'],20000,abs_tol=1e-7)
    first=opening('2026-11-02');assert first.weekday()==0
    result=dict(status='PASS',checked_at=datetime.now(timezone.utc).isoformat(),model_fingerprint=state['model_fingerprint'],ledger_audits=audits,
        source_coverage=report.get('coverage'),source_generated_at=report['generated_at'],paper_status=report['status'],paper_started=report['paper_started'],sessions=report['sessions'],trades=len(s['trades']),positions=len(s['shares']),nav_sek=report['nav_sek'],plan=plan,
        first_session=dict(date='2026-11-02',opening_utc=first.isoformat(),opening_stockholm=first.astimezone(ZoneInfo('Europe/Stockholm')).isoformat(),collection_times_utc=['08:17','14:47','15:47','22:17'],collection_times_stockholm=['09:17','15:47','16:47','23:17']),
        execution_capability='UNVERIFIED_UNTIL_ACTUAL_ALLOWED_OPENING_OBSERVATION',economic_status='NO_GO_INSUFFICIENT_EVIDENCE',live_approved=False,broker_orders_enabled=False)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--report',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=check(json.loads(Path(a.state).read_text()),json.loads(Path(a.report).read_text()));Path(a.output).write_text(json.dumps(result,indent=2,allow_nan=False));print('READINESS',result['status'],result['sessions'],result['trades'])
