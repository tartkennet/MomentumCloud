"""Separate prospective Avanza account, reusing the audited opening/event ledger.

No broker client. No retrospective opening fills. Selection never sees capital.
The frozen Quality account and its approval gates are untouched.
"""
import argparse
import copy
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from momentum_core_data import atomic_json, read_json
from quality_forward import NY, bootstrap, digest
from quality_strategy import plan_orders
from quality_audit import audit_plan
from quality_account_audit import audit_account
from research_stocks10 import fee
from run_quality_forward import data_for, observe
from h3_display import rate_on

MODEL = 'avanza10-observed-paper-v1'
POLICY = dict(model=MODEL, selection='avanza10-paper-v2', retention='KEEP_QUALIFYING_WHOLE_SHARES',
              execution='NEXT_OBSERVED_OPEN_0930_1130_NY_NO_BACKFILL', rebalance='MONTHLY',
              risk='DAILY_SPY_SMA200_CASH_OFF', costs='MIN_1_USD_OR_25BP_PLUS_40BP',
              max_position=.20, max_industry=.30, max_division=.50, live_approved=False)


def membership(rows):
    selected=[]
    for r in rows:
        if (r['ticker']=='SPY' or any(x['cik']==r['cik'] for x in selected) or
                sum(str(x['sic'])[:2]==str(r['sic'])[:2] for x in selected)>=2 or
                sum(x['division']==r['division'] for x in selected)>=4):
            continue
        selected.append(copy.deepcopy(r))
        if len(selected)==10:break
    return selected


def cancel(state, now, reason):
    if state.get('pending'):
        state.setdefault('cancelled_intentions', []).append(dict(observed_at=now.isoformat(),
            commitment=state['pending']['sha256'], reason=reason))
        state['pending']=None


def decide(state, report, snapshot, data, now):
    """Commit exact quantities before an opening exists, or explain the block."""
    on=report.get('risk_on');month=now.astimezone(NY).strftime('%Y-%m')
    state['blockers']=[]
    valid=(snapshot.get('market_verified') is True and snapshot.get('quotes_as_of')==report.get('price_as_of')
           and report.get('status')!='COLLECTION_FAILED' and not report.get('errors')
           and 0 <= (now-datetime.fromisoformat(report['generated_at'])).total_seconds() < 1800)
    if not valid or not isinstance(on,bool):
        cancel(state,now,'UNVERIFIED_INPUT');state['blockers']=['DATA_BLOCKED'];return
    if on and (not snapshot.get('selection_verified') or snapshot.get('coverage',0)<.90):
        cancel(state,now,'SELECTION_NOT_VERIFIED');state['blockers']=['SELECTION_BLOCKED_90PCT_REQUIRED'];return
    p=state.get('pending')
    if p and ((not on and p['kind']!='RISK_OFF') or p['created_at'][:7]!=month):
        cancel(state,now,'RISK_OFF_OR_MONTH_CHANGED')
    state['risk_checked_at']=now.isoformat();state['risk_on']=on
    if state.get('pending'):return
    if not on:
        state['previous_risk']=False
        if not state['strategy']['shares']:return
        orders=[dict(ticker=t,side='SELL',quantity=int(q)) for t,q in sorted(state['strategy']['shares'].items())]
        if any(q<1 or not float(q).is_integer() for q in state['strategy']['shares'].values()):
            state['blockers']=['CORPORATE_ENTITLEMENT_REQUIRES_REVIEW'];return
        p=dict(created_at=now.isoformat(),signal_date=report['price_as_of'],targets=[],
               plan=dict(orders=orders),kind='RISK_OFF',model_fingerprint=state['model_fingerprint'],sources=[])
    else:
        selection=snapshot.get('selection') or {}
        if not (snapshot.get('selection_verified') and snapshot.get('coverage',0)>=.90
                and selection.get('month')==month):
            state['blockers']=['SELECTION_BLOCKED_90PCT_REQUIRED'];return
        targets=membership(selection.get('rows',[]));state['ranked_targets']=targets
        if len(targets)!=10:
            state['blockers']=['TEN_INDIVIDUAL_STOCKS_REQUIRED'];return
        if state.get('decision_month')==month and state.get('previous_risk') is not False:
            if len(state['strategy']['shares'])!=10:
                state['blockers']=['PARTIAL_FILL_REVIEW_REQUIRED']
            return
        try:
            # Refresh prices without changing the locked membership.
            for r in targets:r['price_usd']=snapshot['quotes'][r['ticker']]
            prices={t:data.bars(report['price_as_of'])[t][1] for t in state['strategy']['shares']}
            nav=(state['strategy']['equity'][-1]['nav'] if state['strategy']['equity'] else state['initial_usd'])
            plan=plan_orders(targets,state['strategy']['shares'],nav,state['strategy']['cash'],prices)
            audit_plan(targets,plan,state['strategy']['shares'],state['strategy']['cash'],nav,prices)
        except (KeyError, ValueError) as exc:
            state['blockers']=[str(exc) if isinstance(exc,ValueError) else 'MISSING_HELD_OR_TARGET_PRICE'];return
        p=dict(created_at=now.isoformat(),signal_date=report['price_as_of'],targets=targets,plan=plan,
               kind='MEMBERSHIP',model_fingerprint=state['model_fingerprint'],sources=[digest(snapshot)])
        if not state['benchmark']['trades']:
            limit=data.bars(report['price_as_of'])['SPY'][1]*1.02
            q=math.floor(state['benchmark']['cash']/limit)
            while q and q*limit+fee(q*limit)>state['benchmark']['cash']:q-=1
            if q:p['benchmark_order']=dict(quantity=q,limit=limit)
    p['sha256']=digest(p);state['pending']=p;state['decisions'].append(copy.deepcopy(p))
    state['previous_risk']=on


def summarize(state, snapshot, now):
    s=state['strategy'];b=state['benchmark'];initial=state['initial_sek']
    curve=[]
    benchmark_valid=bool(b['trades']) and bool(s['trades']) and b['trades'][0]['date']==s['trades'][0]['date']
    for row in s['equity']:
        rate=state['valuation_fx'][row['date']]['usdsek']
        other=next((x for x in b['equity'] if x['date']==row['date']),None)
        curve.append(dict(date=row['date'],nav_sek=row['nav']*rate,
                          spy_nav_sek=other['nav']*rate if other and benchmark_valid else None,
                          usdsek=rate,fx_date=state['valuation_fx'][row['date']]['date'],
                          observed_at=state['valuation_quotes'][row['date']]['observed_at']))
    last=curve[-1] if curve else None
    pending_value=bool(s['trades']) and (not last or any(t['date']>last['date'] for t in s['trades']) or
                    s['shares']!=state['valuation_quotes'][last['date']]['shares'])
    nav=None if pending_value else last['nav_sek'] if last else initial
    rate=last['usdsek'] if last else state['initial_fx']['usdsek']
    positions=[]
    for ticker,q in sorted(s['shares'].items()):
        price=None if pending_value else state['valuation_quotes'][last['date']]['prices'].get(ticker) if last else None
        # Basis is shown only when cash trades explain the current quantity.
        trades=[t for t in s['trades'] if t['ticker']==ticker and t['side'] in ('BUY','SELL')]
        quantity=0;basis=0;buy_usd=0
        for t in trades:
            if t['side']=='BUY':
                quantity+=t['quantity'];basis+=(t['quantity']*t['price']+t['fee'])*state['trade_fx'][t['date']]['usdsek'];buy_usd+=t['quantity']*t['price']
            elif quantity:
                factor=(quantity-t['quantity'])/quantity;basis*=factor;buy_usd*=factor;quantity-=t['quantity']
        basis_ok=math.isclose(quantity,q) and quantity>0
        value=q*price*rate if price else None
        positions.append(dict(ticker=ticker,quantity=q,price_usd=price,value_sek=value,
            purchase_price_usd=buy_usd/q if basis_ok else None,cost_basis_sek=basis if basis_ok else None,
            return_sek=value-basis if basis_ok and value is not None else None,
            return_pct=100*(value/basis-1) if basis_ok and value is not None and basis else None,
            weight=value/nav if value is not None and nav else None))
    peak=initial;drawdown=0
    for r in curve:peak=max(peak,r['nav_sek']);drawdown=min(drawdown,100*(r['nav_sek']/peak-1))
    costs=sum(t['fee']*state['trade_fx'][t['date']]['usdsek'] for t in s['trades'] if t['side'] in ('BUY','SELL'))
    completed={o['commitment'] for o in state['opening_observations'] if o['unfilled']==0}
    rebalances=[d for d in state['decisions'] if d['kind']=='MEMBERSHIP' and d['sha256'] in completed]
    blockers=state.get('blockers',[])
    status='BLOCKED' if blockers else 'AWAITING_OBSERVED_OPEN' if state.get('pending') else 'RISK_OFF_CASH' if state.get('risk_on') is False else 'MONITORING'
    return dict(schema_version=1,model=MODEL,policy=POLICY,model_fingerprint=state['model_fingerprint'],
        mode='PAPER_ONLY',live_approved=False,broker_orders_enabled=False,economic_status='NO_GO_INSUFFICIENT_EVIDENCE',
        initialized_at=state['initialized_at'],generated_at=now.isoformat(),status=status,blockers=blockers,
        initial_sek=initial,paper_started=bool(s['trades']),first_trade_at=s['trades'][0].get('execution_at') if s['trades'] else None,
        risk_on=state.get('risk_on'),risk_checked_at=state.get('risk_checked_at'),selection=snapshot.get('selection'),
        nav_sek=nav,cash_sek=s['cash']*rate,cash_fx_date=last['fx_date'] if last else state['initial_fx']['date'],
        return_sek=nav-initial if nav is not None else None,return_pct=100*(nav/initial-1) if nav is not None else None,
        drawdown_pct=drawdown,costs_sek=costs,positions=positions,trades=s['trades'],curve=curve,
        valuation_pending=pending_value,valuation_as_of=last['date'] if last else None,
        pending_intention=state.get('pending'),decisions=state['decisions'],cancelled_intentions=state.get('cancelled_intentions',[]),
        unfilled_orders=state['unfilled_orders'],gaps=state['gaps'],rebalances=len(rebalances),
        benchmark_valid=benchmark_valid,audits=state['audits'],journal_sha256=digest(state))


def run(args):
    now=datetime.now(timezone.utc);out=Path(args.output);previous=Path(args.previous)
    report=read_json(out/'quality.json');snapshot=read_json(out/'avanza10.json')
    prior=read_json(previous/'avanza-state.json') if (previous/'avanza-state.json').exists() else None
    state=copy.deepcopy(prior)
    try:
        data,client=data_for(Path(args.cache),now)
        if data.sessions[-1]!=snapshot.get('quotes_as_of'):raise ValueError('AVANZA_MARKET_CLOCK_MISMATCH')
        if not state:
            if not snapshot.get('market_verified') or not report.get('fx'):raise ValueError('NO_VERIFIED_INITIAL_FX')
            initial=float(os.environ.get('AVANZA_INITIAL_SEK') or 20000)
            if not math.isfinite(initial) or not 0<initial<=1e9:raise ValueError('INVALID_INITIAL_CAPITAL')
            state=bootstrap(dict(initial_usd=initial/report['fx']['usdsek'],fx=report['fx']),digest(POLICY),now)
            state.update(initial_sek=initial,opening_quotes=[],valuation_fx={},trade_fx={},ranked_targets=[])
        if state['model_fingerprint']!=digest(POLICY):raise ValueError('POLICY_CHANGED_REQUIRES_NEW_COHORT')
        # Cancel unsafe intentions BEFORE the observer can execute an opening.
        decide(state,report,snapshot,data,now)
        state=observe(state,data,client,now)
        for day in {r['date'] for r in state['strategy']['equity']} | {t['date'] for t in state['strategy']['trades']}:
            fx=rate_on(report.get('fx_history',{}),day)
            if not fx:raise ValueError('MISSING_DATED_FX')
            state['valuation_fx'].setdefault(day,fx);state['trade_fx'].setdefault(day,fx)
        decide(state,report,snapshot,data,now)
        state['audits']={k:audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
        if prior:
            for k in ('strategy','benchmark'):
                for field in ('trades','equity'):assert state[k][field][:len(prior[k][field])]==prior[k][field]
            assert state['decisions'][:len(prior['decisions'])]==prior['decisions']
        state['previous_state_sha256']=digest(prior) if prior else None
        result=summarize(state,snapshot,now)
        atomic_json(out/'avanza-state.json',state)
    except Exception as exc:
        # Fail closed; never publish an unaudited mutation or a fabricated fill.
        result=(read_json(previous/'avanza-paper.json') if (previous/'avanza-paper.json').exists() else
                dict(schema_version=1,model=MODEL,mode='PAPER_ONLY',live_approved=False,broker_orders_enabled=False,
                     paper_started=False,positions=[],trades=[],curve=[],initial_sek=20000))
        result.update(status='BLOCKED',generated_at=now.isoformat(),blockers=[str(exc) if isinstance(exc,ValueError) else type(exc).__name__])
        if prior:
            prior['previous_state_sha256']=digest(prior)
            result['journal_sha256']=digest(prior)
            atomic_json(out/'avanza-state.json',prior)
    atomic_json(out/'avanza-paper.json',result)
    print('AVANZA_PAPER',result['status'],result.get('blockers',[]),len(result['trades']))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cache','previous','output'):p.add_argument('--'+name,required=True)
    run(p.parse_args())
