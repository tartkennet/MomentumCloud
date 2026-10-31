"""Future-only precommitted whole-share paper orders. No broker client exists."""
import copy
import hashlib
import json
from datetime import datetime,time,timezone
from zoneinfo import ZoneInfo
from dataclasses import replace
from types import SimpleNamespace

from momentum_core import CONFIG
from research_momentum10_v2 import RetentionLedger
from quality_strategy import plan_orders
from quality_sources import DataUnavailable

NY=ZoneInfo('America/New_York')


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def opening(day):return datetime.combine(datetime.fromisoformat(day).date(),time(9,30),NY).astimezone(timezone.utc)

def opening_window(now):
    t=now.astimezone(NY)
    return t.weekday()<5 and time(9,30)<=t.time().replace(tzinfo=None)<=time(11,30)


def commit_plan(state,report,now,prices):
    s=RetentionLedger(**state['strategy']);targets=report['targets']
    plan=plan_orders(targets,s.shares,report['initial_usd'] if not s.equity else s.equity[-1]['nav'],s.cash,prices)
    intention=dict(created_at=now.isoformat(),signal_date=report['price_as_of'],targets=targets,plan=plan,
        model_fingerprint=state['model_fingerprint'],sources=[r['fundamental']['sha256'] for r in targets])
    intention['sha256']=digest(intention);state['pending']=intention;state['decision_month']=now.astimezone(NY).strftime('%Y-%m')
    state['decisions'].append(copy.deepcopy(intention));return intention


def execute_pending(state,bars,day,now):
    p=state.get('pending')
    if not p:return
    check=dict(p);h=check.pop('sha256');assert digest(check)==h
    if not opening_window(now) or now.astimezone(NY).date().isoformat()!=day:raise DataUnavailable('NOT_AN_OBSERVED_OPENING_WINDOW')
    if datetime.fromisoformat(p['created_at'])>=opening(day):raise DataUnavailable('DECISION_WAS_NOT_BEFORE_OPEN')
    if p['model_fingerprint']!=state['model_fingerprint']:raise DataUnavailable('CHANGED_FROZEN_MODEL')
    s=RetentionLedger(**state['strategy']);config=replace(CONFIG,positions=10)
    orders=p['plan']['orders'];unfilled=[]
    for order in orders:
        t=order['ticker'];bar=bars.get(t);price=bar[0] if bar else None
        if not price or (order['side']=='BUY' and price>order['limit']):unfilled.append(dict(order,reason='MISSING_OPEN_OR_BUY_LIMIT'));continue
        if order['side']=='BUY' and any(o['side']=='SELL' for o in unfilled):unfilled.append(dict(order,reason='EXIT_NOT_FILLED'));continue
        q=order['quantity']
        if order['side']=='SELL' and s.shares.get(t,0)<q:raise DataUnavailable('CORPORATE_ACTION_CHANGED_COMMITTED_QUANTITY')
        from research_stocks10 import fee
        if order['side']=='BUY' and q*price+fee(q*price)>s.cash+1e-8:unfilled.append(dict(order,reason='ACTUAL_CASH_INSUFFICIENT'));continue
        s._trade(day,p['signal_date'],t,order['side'],q,price,config,'QUALITY_MEMBERSHIP',
            decision_at=p['created_at'],execution_at=opening(day).isoformat(),quote_observed_at=now.isoformat(),commitment_sha256=h)
    state['strategy']=s.to_dict();state['pending']=None;state['unfilled_orders'].extend(dict(o,date=day,observed_at=now.isoformat()) for o in unfilled)
    state['decision_month']=day[:7];state['opening_observations'].append(dict(date=day,observed_at=now.isoformat(),commitment=h,unfilled=len(unfilled)))


def bootstrap(report,fingerprint,now):
    return dict(schema_version=1,model_fingerprint=fingerprint,initialized_at=now.isoformat(),initial_usd=report['initial_usd'],initial_fx=report['fx'],
        strategy=RetentionLedger(cash=report['initial_usd']).to_dict(),benchmark=RetentionLedger(cash=report['initial_usd']).to_dict(),
        decisions=[],pending=None,unfilled_orders=[],opening_observations=[],valuation_observations=[],event_through=now.astimezone(NY).date().isoformat(),
        decision_month='',gaps=[],previous_state_sha256=None)


def process(state,report,now,market_days,bars=None):
    """Exact commit/fill timing state machine; never reconstruct missed orders."""
    state=copy.deepcopy(state);state['previous_state_sha256']=digest(state)
    pending=state.get('pending')
    if pending:
        eligible=[d for d in market_days if opening(d)>datetime.fromisoformat(pending['created_at']) and opening(d)<=now]
        if eligible:
            first=min(eligible);today=now.astimezone(NY).date().isoformat()
            if first!=today or not opening_window(now):
                state['gaps'].append(dict(kind='MISSED_OPEN_NO_BACKFILL',session=first,observed_at=now.isoformat(),commitment=pending['sha256']));state['pending']=None
            elif bars:execute_pending(state,bars,today,now)
    return state
