"""Isolated E2 observer: delayed minute paper assumptions, never broker orders."""
import copy,hashlib,json,math
from datetime import datetime,time,timedelta,timezone
from pathlib import Path
from dataclasses import replace
from quality_forward import NY,digest
from quality_sources import DataUnavailable
from research_momentum10_v2 import RetentionLedger
from research_stocks10 import fee
from momentum_core import CONFIG
from run_quality_forward import events

POLICY='BEST_V2_E2_DELAYED_MINUTE_CLOSE'
EFFECTIVE=datetime.fromisoformat('2026-11-10T00:00:00+00:00')
FILE='docs/BEST_V2_EXECUTION_POLICY_E2.md'

def policy_hash():return hashlib.sha256(Path(FILE).read_bytes()).hexdigest()
def aware(s):
    d=datetime.fromisoformat(s)
    if d.tzinfo is None:raise DataUnavailable('NAIVE_EXECUTION_TIME')
    return d

def record(state,day,now,status,reasons,**extra):
    p=state.get('pending') or {};orders=p.get('plan',{}).get('orders',[])
    outcome=dict(session=day,observed_at=now.isoformat(),status=status,commitment=p.get('sha256'),filled=0,
        orders=[dict(ticker=o['ticker'],side=o['side'],quantity=o['quantity'],status='UNFILLED',reason=reasons.get(o['ticker'],status)) for o in orders],**extra)
    state.setdefault('execution_attempts',[]).append(outcome);state['execution_outcome']=outcome
    return outcome

def missed(state,days,now,legacy=False):
    p=state.get('pending')
    if not p:return
    created=aware(p['created_at'])
    for day in days:
        deadline=datetime.combine(datetime.fromisoformat(day).date(),time(11,30) if legacy else time(15,59),NY)
        if deadline<=created or now<=deadline:continue
        if any(g.get('kind')=='MISSED_OPEN_NO_BACKFILL' and g.get('session')==day and g.get('commitment')==p['sha256'] for g in state['gaps']):continue
        g=dict(kind='MISSED_OPEN_NO_BACKFILL',session=day,observed_at=now.isoformat(),commitment=p['sha256'],recovered_diagnostic=legacy)
        state['gaps'].append(g)
        outcome=record(state,day,now,'MISSED_OPEN_NO_BACKFILL',{},diagnostic_only=True)
        state['unfilled_orders'].extend(dict(o,date=day,observed_at=now.isoformat(),commitment=p['sha256']) for o in outcome['orders'])

def register(state,data,now):
    previous=state.get('execution_policy')
    if previous:
        if previous['id']!=POLICY or previous['sha256']!=policy_hash():raise DataUnavailable('FROZEN_EXECUTION_POLICY_CHANGED')
        return
    missed(state,data.sessions,now,legacy=True)
    old=state.get('pending')
    if old:
        state.setdefault('cancelled_intentions',[]).append(dict(observed_at=now.isoformat(),commitment=old['sha256'],reason='E2_PROSPECTIVE_RECOMMIT_NO_BACKFILL'))
        state['execution_migration_members']=[r['ticker'] for r in old['targets']]
        state['pending']=None
    state['execution_policy']=dict(id=POLICY,sha256=policy_hash(),registered_at=now.isoformat(),effective_from=EFFECTIVE.isoformat(),source='Massive/Polygon unadjusted completed minute close',realtime_verified=False,max_quote_age_seconds=1200)
    state.setdefault('execution_policy_journal',[]).append(copy.deepcopy(state['execution_policy']))

def validate_bar(raw,now,committed,registered):
    t=raw.get('t')
    if type(t) is not int or t%60000:raise DataUnavailable('INVALID_MINUTE_TIMESTAMP')
    start=datetime.fromtimestamp(t/1000,timezone.utc);end=start+timedelta(minutes=1);local=start.astimezone(NY)
    if local.date()!=now.astimezone(NY).date():raise DataUnavailable('WRONG_QUOTE_SESSION')
    if local.weekday()>4 or not time(9,35)<=local.time().replace(tzinfo=None)<=time(15,40):raise DataUnavailable('OUTSIDE_REGULAR_EXECUTION_MINUTE')
    if start<=max(committed,registered,EFFECTIVE):raise DataUnavailable('QUOTE_PRECEDES_COMMITMENT_OR_POLICY')
    if end>now:raise DataUnavailable('UNFINISHED_OR_FUTURE_MINUTE')
    if (now-end).total_seconds()>1200:raise DataUnavailable('OPEN_PRICE_PROVIDER_DELAY')
    if any(type(raw.get(k)) not in (int,float) or not math.isfinite(raw[k]) or raw[k]<=0 for k in ('o','h','l','c','v')):raise DataUnavailable('INVALID_MINUTE_OHLCV')
    if not raw['l']<=min(raw['o'],raw['c'])<=max(raw['o'],raw['c'])<=raw['h']:raise DataUnavailable('INCONSISTENT_MINUTE_OHLC')
    return start,end

def quote(client,ticker,now,committed,registered):
    day=now.astimezone(NY).date().isoformat();start=datetime.combine(now.astimezone(NY).date(),time(9,35),NY)
    path=f'/v2/aggs/ticker/{ticker}/range/1/minute/{int(start.timestamp()*1000)}/{int(now.timestamp()*1000)}'
    try:body=client.get(path,{'adjusted':'false','sort':'desc','limit':1})
    except DataUnavailable as exc:
        raise DataUnavailable('OPEN_PRICE_NO_ENTITLEMENT' if str(exc)=='HTTP_403' else 'OPEN_PRICE_UNAVAILABLE') from None
    if body.get('status') not in ('OK','DELAYED') or body.get('ticker',ticker)!=ticker:raise DataUnavailable('INVALID_INTRADAY_IDENTITY_OR_STATUS')
    rows=body.get('results',[])
    if not rows:raise DataUnavailable('OPEN_PRICE_UNAVAILABLE')
    raw=rows[0];begin,end=validate_bar(raw,now,committed,registered)
    return dict(ticker=ticker,raw=raw,price_as_of=end.isoformat(),minute_start=begin.isoformat(),observed_at=now.isoformat(),source_path=path,adjusted=False,provider_status=body['status'],delay_seconds=(now-end).total_seconds(),price=raw['c'])

def observe(state,data,client,now):
    # Shared legacy observer is used ONLY with pending removed: events/closes remain
    # unchanged, but no grouped-daily or old opening execution path can run.
    from avanza10_forward import observe_account as legacy_marks
    p=state.get('pending');state['pending']=None
    try:state=legacy_marks(state,data,client,now)
    finally:state['pending']=p
    if not p:return state
    check=dict(p);sha=check.pop('sha256')
    if digest(check)!=sha:raise DataUnavailable('INVALID_COMMITMENT_HASH')
    local=now.astimezone(NY);day=local.date().isoformat();missed(state,data.sessions,now)
    if now<EFFECTIVE or local.weekday()>4 or local.time().replace(tzinfo=None)<time(9,51):
        record(state,day,now,'OPEN_PRICE_WAITING',{});return state
    if local.time().replace(tzinfo=None)>time(15,59):
        deadline=datetime.combine(local.date(),time(15,59),NY)
        due=aware(p['created_at'])<deadline and day in data.sessions
        record(state,day,now,'MISSED_OPEN_NO_BACKFILL' if due else 'OPEN_PRICE_WAITING',{});return state
    policy=state['execution_policy'];committed=aware(p['created_at']);registered=aware(policy['registered_at'])
    receipts={};reasons={}
    for ticker in sorted({o['ticker'] for o in p['plan']['orders']}|({'SPY'} if p.get('benchmark_order') and not state['benchmark']['trades'] else set())):
        try:receipts[ticker]=quote(client,ticker,now,committed,registered)
        except DataUnavailable as exc:reasons[ticker]=str(exc)
    state.setdefault('intraday_observations',[]).append(dict(session=day,observed_at=now.isoformat(),commitment=sha,quotes=copy.deepcopy(receipts),errors=copy.deepcopy(reasons)))
    if not receipts:
        record(state,day,now,'OPEN_PRICE_UNAVAILABLE',reasons);return state
    events(state,data,day)
    changed=state.get('event_changed_tickers',[]);cash=state['strategy']['cash'];projected=dict(state['strategy']['shares'])
    for order in p['plan']['orders']:
        t=order['ticker'];q=order['quantity']
        if t in changed:reasons[t]='CORPORATE_ACTION_INVALIDATED_COMMITMENT'
        if t not in receipts:continue
        price=receipts[t]['price']
        if order['side']=='BUY' and price>order['limit']:reasons[t]='OBSERVED_PRICE_EXCEEDS_COMMITTED_LIMIT'
        if order['side']=='SELL' and projected.get(t,0)<q:reasons[t]='COMMITTED_SELL_QUANTITY_UNAVAILABLE'
        cash+=q*price-fee(q*price) if order['side']=='SELL' else -q*price-fee(q*price)
        projected[t]=projected.get(t,0)+(q if order['side']=='BUY' else -q)
    if cash < -1e-8:reasons.update({o['ticker']:'ACTUAL_CASH_INSUFFICIENT' for o in p['plan']['orders'] if o['side']=='BUY'})
    nav=state['strategy']['equity'][-1]['nav'] if state['strategy']['equity'] else state['initial_usd']
    for row in p['targets']:
        t=row['ticker'];price=receipts.get(t,{}).get('price')
        if price and projected.get(t,0)*price>nav*.15+1e-8:reasons[t]='OBSERVED_ISSUER_LIMIT'
        group=[x for x in p['targets'] if x['cluster']==row['cluster']]
        if all(x['ticker'] in receipts for x in group) and sum(projected.get(x['ticker'],0)*receipts[x['ticker']]['price'] for x in group)>nav*.35+1e-8:reasons[t]='OBSERVED_CLUSTER_LIMIT'
    if reasons:
        status='OPEN_PRICE_PROVIDER_DELAY' if any(x=='OPEN_PRICE_PROVIDER_DELAY' for x in reasons.values()) else 'OPEN_PRICE_UNAVAILABLE'
        record(state,day,now,status,{o['ticker']:reasons.get(o['ticker'],'ATOMIC_BASKET_BLOCKED') for o in p['plan']['orders']},provider_errors=reasons);return state
    ledger=RetentionLedger(**state['strategy']);cfg=replace(CONFIG,positions=10)
    bars={t:[r['price'],r['price'],r['raw']['v']] for t,r in receipts.items()}
    state['opening_quotes'].append(dict(date=day,observed_at=now.isoformat(),mode='DELAYED_MINUTE_PAPER_ASSUMPTION',realtime_verified=False,bars=bars,intraday_receipts=copy.deepcopy(receipts),commitment=sha,execution_policy=POLICY))
    for order in p['plan']['orders']:
        t=order['ticker'];r=receipts[t]
        ledger._trade(day,p['signal_date'],t,order['side'],order['quantity'],r['price'],cfg,'BEST_V2_E2_'+p['kind'],decision_at=p['created_at'],execution_at=now.isoformat(),quote_observed_at=now.isoformat(),price_as_of=r['price_as_of'],execution_policy=POLICY,commitment_sha256=sha)
    state['strategy']=ledger.to_dict()
    if p.get('benchmark_order') and not state['benchmark']['trades']:
        bp=p['benchmark_order'];price=receipts['SPY']['price'];bench=RetentionLedger(**state['benchmark'])
        if price<=bp['limit'] and bp['quantity']*price+fee(bp['quantity']*price)<=bench.cash:
            bench._trade(day,p['signal_date'],'SPY','BUY',bp['quantity'],price,cfg,'BENCHMARK_E2',decision_at=p['created_at'],execution_at=now.isoformat(),quote_observed_at=now.isoformat(),price_as_of=receipts['SPY']['price_as_of'],execution_policy=POLICY,commitment_sha256=sha);state['benchmark']=bench.to_dict()
        else:state['gaps'].append(dict(kind='BENCHMARK_INTRADAY_UNFILLED',session=day,observed_at=now.isoformat()))
    outcome=record(state,day,now,'FILLED',{})
    for o in outcome['orders']:o.update(status='FILLED',reason=None)
    outcome['filled']=len(outcome['orders']);state['pending']=None;state['decision_month']=day[:7]
    state['opening_observations'].append(dict(date=day,observed_at=now.isoformat(),commitment=sha,unfilled=0,execution_policy=POLICY))
    return state
