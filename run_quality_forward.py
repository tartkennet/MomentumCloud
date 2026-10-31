"""Observed-only Quality paper controller. No broker endpoint or real order path."""
import argparse,copy,gzip,hashlib,json,math,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from dataclasses import replace
import requests
from momentum_core import CONFIG,gates,metrics
from momentum_core_data import atomic_json,read_json
from research_momentum10_v2 import RetentionLedger
from research_stocks10 import fee
from research_core_actions import supplement
from research_momentum10_fx import ReferenceFX
from run_core_risk_research import make_data
from collect_quality import collect,extend_events,PriceProvider
from quality_forward import bootstrap,commit_plan,digest,opening_window,process,NY
from quality_sources import DataUnavailable
from quality_account_audit import audit_account,audit_statistics
from quality_strategy import MODEL

FROZEN=('quality_sources.py','quality_fundamentals.py','quality_strategy.py','quality_audit.py','quality_forward.py','quality_account_audit.py','run_quality_forward.py','collect_quality.py','docs/QUALITY_EARNINGS_PROTOCOL_20261031.md','momentum_core.py','momentum_core_data.py','research_core_ledger.py','research_momentum10_v2.py','research_stocks10.py','research_momentum10_fx.py','research_core_actions.py','run_core_risk_research.py','h3_display.py','run_stocks10_research.py','run_core_normalized_research.py','audit_core_normalized.py','backtest_momentum_v3.py','momentum_config.py','momentum_strategy.py','requirements.txt')


def fingerprint():return digest({f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in FROZEN})


def data_for(cache,now):
    import run_core_risk_research as adapter
    client=PriceProvider();end=(now.date()-timedelta(days=1)).isoformat();extend_events(cache,now.astimezone(NY).date().isoformat(),client)
    adapter.PolygonClient=lambda key:client
    data=supplement(make_data(cache,end,False))
    for kind,column in [('splits','execution_date'),('dividends','ex_dividend_date')]:
        paths=sorted(cache.glob(kind+'-*-v1.json.gz'));rows=read_json(paths[-1]);setattr(data.source,kind,rows)
        groups={}
        for e in rows:groups.setdefault(e[column],[]).append(e)
        setattr(data,kind+'_by_day',groups)
    path=cache/'quality-fx.xml'
    r=requests.get('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml',timeout=(3,10))
    if r.status_code!=200:raise DataUnavailable('FX_HTTP_'+str(r.status_code))
    path.write_bytes(r.content);data.native_usd=ReferenceFX(path).usd
    return data,client


def events(state,data,day):
    if day<=state['event_through']:return
    data.set_day(day)
    currencies={'USD'}|{r.get('currency','USD').upper() for k in ('strategy','benchmark') for r in state[k]['receivables']}|{r.get('currency','USD').upper() for r in data.dividends if any(state[k]['shares'].get(r['ticker']) for k in ('strategy','benchmark'))}
    state['event_journal'].append(dict(date=day,observed_at=datetime.now(timezone.utc).isoformat(),splits=data.splits,dividends=data.dividends,cash_actions=data.cash_actions,stock_actions=data.stock_actions,distributions=getattr(data,'distributions',[]),fx={c:data.native_usd(day,c) for c in currencies}))
    state['event_changed_tickers']=[r['ticker'] for r in data.splits]+[t for actions in (data.cash_actions,data.stock_actions) for t,e in actions.items() if e['effective_date']==day]
    for k in ('strategy','benchmark'):
        ledger=RetentionLedger(**state[k]);ledger.events_before_open(data,day);state[k]=ledger.to_dict()
    state['event_through']=day


def observe(state,data,client,now):
    today=now.astimezone(NY).date().isoformat();market_days=list(data.sessions);opening_bars=None
    # Today's unfinished daily bar is NEVER written into the final-close cache.
    if state.get('pending') and opening_window(now):
        raw=client.get('/v2/aggs/grouped/locale/us/market/stocks/'+today,{'adjusted':'false','include_otc':'false'})
        opening_bars={r['T']:[r.get('o'),r.get('c'),r.get('v')] for r in raw.get('results',[]) if r.get('T')}
        if not opening_bars.get('SPY',[None])[0]:raise DataUnavailable('CURRENT_OPEN_NOT_OBSERVED')
        market_days.append(today)
    last=data.sessions[-1]
    for day in [d for d in data.sessions if state['event_through']<d<=last]:events(state,data,day)
    last=data.sessions[-1];init=state['initialized_at'][:10]
    valued={r['date'] for r in state['strategy']['equity']}
    if last>=init and last not in valued:
        missing=[d for d in data.sessions if d>=init and d<last and d not in valued]
        for d in missing:
            if not any(g.get('session')==d and g['kind']=='MISSED_VALUATION_NO_BACKFILL' for g in state['gaps']):state['gaps'].append(dict(kind='MISSED_VALUATION_NO_BACKFILL',session=d,observed_at=now.isoformat()))
        prices={t:data.bars(last)[t][1] for k in ('strategy','benchmark') for t in state[k]['shares']}
        if any(not p or p<=0 for p in prices.values()):raise DataUnavailable('MISSING_HELD_CLOSE')
        state['valuation_quotes'][last]=dict(observed_at=now.isoformat(),prices=prices)
        for k in ('strategy','benchmark'):
            l=RetentionLedger(**state[k]);nav,stock,claims=l.close_value(data,last)
            l.equity.append(dict(date=last,nav=nav,cash=l.cash,stock_value=stock,receivables=claims,positions=len(l.shares),fees_cumulative=l.fees));state[k]=l.to_dict()
        state['valuation_observations'].append(dict(date=last,observed_at=now.isoformat()))
    if today in market_days and today>last:
        events(state,data,today)
        if not state['strategy']['trades'] and last[:7]!=today[:7]:
            for k in ('strategy','benchmark'):state[k]['first_is_month_boundary']=True
    state=process(state,{},now,market_days,opening_bars)
    if opening_bars and any(o['date']==today for o in state['opening_observations']):
        needed={t['ticker'] for k in ('strategy','benchmark') for t in state[k]['trades'] if t['date']==today}
        if not any(q['date']==today for q in state['opening_quotes']):state['opening_quotes'].append(dict(date=today,observed_at=now.isoformat(),mode='OBSERVED_RAW_OPEN_PAPER_ASSUMPTION',realtime_verified=False,bars={t:opening_bars[t] for t in needed}))
    return state


def decide(state,report,data,now):
    month=now.astimezone(NY).strftime('%Y-%m');on=report.get('risk_on')
    if on is None:return
    pending=state.get('pending')
    if pending:
        buying=any(o['side']=='BUY' for o in pending['plan']['orders'])
        rollover=pending['created_at'][:7]!=month and pending.get('kind')!='RISK_OFF'
        if (not on and buying) or rollover:
            state.setdefault('cancelled_intentions',[]).append(dict(observed_at=now.isoformat(),commitment=pending['sha256'],reason='RISK_OFF' if not on else 'NEW_MONTH_REQUIRES_FRESH_SELECTION'))
            state['pending']=None
        else:return
    if not on and state['strategy']['shares']:
        plan=dict(orders=[dict(ticker=t,side='SELL',quantity=math.floor(q+1e-9)) for t,q in sorted(state['strategy']['shares'].items()) if q>=1])
        p=dict(created_at=now.isoformat(),signal_date=report['price_as_of'],targets=[],plan=plan,kind='RISK_OFF',model_fingerprint=state['model_fingerprint'],sources=[])
        p['sha256']=digest(p);state['pending']=p;state['decisions'].append(copy.deepcopy(p))
    elif on and report.get('paper_start_permit') and (state['decision_month']!=month or state['previous_risk'] is False):
        # The collector has used this account's latest audited NAV and cash.
        p=commit_plan(state,report,now,{t:data.bars(report['price_as_of'])[t][1] for t in state['strategy']['shares']})
        if not state['benchmark']['trades']:
            price=data.bars(report['price_as_of'])['SPY'][1];limit=price*1.02;q=math.floor(state['benchmark']['cash']/limit)
            while q and q*limit+fee(q*limit)>state['benchmark']['cash']:q-=1
            if q:p['benchmark_order']=dict(quantity=q,limit=limit)
            p.pop('sha256');p['sha256']=digest(p);state['decisions'][-1]=copy.deepcopy(p)
    state['previous_risk']=on


def export(report,state,now):
    report=copy.deepcopy(report);s=state['strategy'];b=state['benchmark'];fx=report.get('fx',state['initial_fx'])
    report['initial_usd']=state['initial_usd'];report['initial_fx']=state['initial_fx']
    collection_status=report.get('status')
    report['collection_status']=collection_status
    report['daily_observed_targets']=report.get('targets',[])
    cancelled={d['commitment'] for d in state.get('cancelled_intentions',[])}
    accepted=[d for d in state['decisions'] if d['sha256'] not in cancelled]
    if accepted:
        selected=accepted[-1]
        report['targets']=selected['targets'];report['selection_as_of']=selected['signal_date']
        report['selection_fx']=selected.get('signal_fx',state['initial_fx']);report['selection_nav_usd']=selected.get('signal_nav_usd',state['initial_usd'])
        report['proposed_orders']=selected['plan'] if selected.get('kind')=='MEMBERSHIP' else None
    else:report['targets']=[];report['proposed_orders']=None
    report['cancelled_intentions']=state.get('cancelled_intentions',[])
    curve=[]
    benchmark_valid=bool(b['trades']) and bool(state['opening_observations']) and b['trades'][0]['date']==state['opening_observations'][0]['date']
    report['benchmark_valid']=benchmark_valid
    for a,bb in zip(s['equity'],b['equity']):
        rate=state['valuation_fx'][a['date']]
        curve.append(dict(date=a['date'],nav_sek=a['nav']*rate['usdsek'],spy_nav_sek=bb['nav']*rate['usdsek'] if benchmark_valid else None))
    report.update(paper_started=bool(state['opening_observations']),sessions=len(s['equity']),paper_initialized_at=state['initialized_at'],model_fingerprint=state['model_fingerprint'],pending_intention=state.get('pending'),cash_usd=s['cash'],fees_usd=s['fees'],trades=s['trades'],curve=curve,gaps=state['gaps'],unfilled_orders=state['unfilled_orders'],paper_metrics=None,positions=[],accounting_audits=state['audits'])
    last=s['equity'][-1] if s['equity'] else None
    report['nav_sek']=last['nav']*state['valuation_fx'][last['date']]['usdsek'] if last else 20000
    if last:
        for t,q in sorted(s['shares'].items()):
            price=state['valuation_quotes'][last['date']]['prices'].get(t)
            report['positions'].append(dict(ticker=t,quantity=q,price_usd=price,value_sek=q*price*state['valuation_fx'][last['date']]['usdsek'] if price else None,weight=q*price/last['nav'] if price else None))
    else:
        # Opening positions exist before the first closing valuation. Show them
        # without attaching a fabricated close or a backdated portfolio value.
        for t,q in sorted(s['shares'].items()):report['positions'].append(dict(ticker=t,quantity=q,price_usd=None,value_sek=None,weight=None))
    report['valuation_pending']=bool(s['shares']) and (not last or max(t['date'] for t in s['trades'])>last['date'])
    if report['valuation_pending']:report['nav_sek']=None
    result=None;periods=[]
    if last and benchmark_valid:
        result,periods=metrics(RetentionLedger(**s),RetentionLedger(**b))
        # Return includes initial trading costs rather than normalising them away.
        result['TotalReturn_pct']=100*(last['nav']/state['initial_usd']-1);result['SPYTotalReturn_pct']=100*(b['equity'][-1]['nav']/state['initial_usd']-1);result['TotalEdgeVsSPY_pct']=result['TotalReturn_pct']-result['SPYTotalReturn_pct']
        peak=state['initial_usd'];dd=0
        for r in s['equity']:peak=max(peak,r['nav']);dd=min(dd,100*(r['nav']/peak-1))
        result['DailyMaxDrawdown_pct']=dd;report['paper_metrics']=result
    checks=gates(result) if result else [dict(name=n,value=None,pass_=False) for n in ('30_complete_months','positive_net_return','beats_SPY','drawdown_within_20pct','positive_months_50pct')]
    report['validation']=dict(status='NO_GO_INSUFFICIENT_EVIDENCE',complete_months=len(periods),remaining_months=max(0,30-len(periods)),gates=checks,continuity_pass=not state['gaps'],live_approved=False)
    report['observations_remaining']=max(0,30-len(periods))
    report['gross_turnover_initial_capital_pct']=100*sum(t['quantity']*t['price'] for t in s['trades'] if t['side'] in ('BUY','SELL'))/state['initial_usd']
    report['sharpe']=None
    if len(s['equity'])>=20 and not state['gaps']:
        import statistics
        navs=[state['initial_usd']]+[r['nav'] for r in s['equity']];returns=[bb/a-1 for a,bb in zip(navs,navs[1:])]
        sigma=statistics.stdev(returns)
        if sigma:report['sharpe']=statistics.mean(returns)/sigma*math.sqrt(252)
    report['valuation_as_of']=last['date'] if last else None
    report['cost_stress_status']='PENDING_INDEPENDENT_FUTURE_ASSESSMENT'
    report['live_approved']=False;report['broker_orders_enabled']=False
    if state['opening_observations']:report['status']='PAPER_ACTIVE' if len(s['shares'])==10 else 'PAPER_CASH' if not s['shares'] else 'PAPER_PARTIAL'
    if state['gaps']:report['status']='PAPER_REVIEW_REQUIRED'
    if state['opening_observations'] and collection_status in ('DATA_BLOCKED','SELECTION_BLOCKED','COLLECTION_FAILED'):
        report['status']='PAPER_DATA_BLOCKED';report.setdefault('errors',[]).append('Nya köp är spärrade. Senast accepterade paper-innehav och daterad värdering visas.')
    report['generated_at']=now.isoformat();report['paper_journal_sha256']=digest(state)
    report['independent_statistics']=audit_statistics(state,report)
    return report


def run(args):
    now=datetime.now(timezone.utc);out=Path(args.output);out.mkdir(exist_ok=True,parents=True);previous=Path(args.previous)
    state=read_json(previous/'state.json') if (previous/'state.json').exists() else None
    fp=fingerprint();prior=copy.deepcopy(state)
    if state and state['model_fingerprint']!=fp:raise DataUnavailable('FROZEN_SOURCE_CHANGED_REQUIRES_NEW_COHORT')
    data,client=data_for(Path(args.cache),now)
    if state:
        # A newer known market close may cancel stale buys before any fill.
        # Protective exits need no fresh business facts, but still cannot use
        # an opening that precedes their actual commitment timestamp.
        import momentum_core as core
        spy=core.adjusted_history(data,data.sessions[-1],'SPY',200)
        if len(spy)!=200:raise DataUnavailable('INCOMPLETE_CURRENT_REGIME')
        if spy[0]<=sum(spy)/200:decide(state,dict(risk_on=False,price_as_of=data.sessions[-1]),data,now)
        elif state.get('pending') and state['pending']['created_at'][:7]!=now.astimezone(NY).strftime('%Y-%m'):
            p=state['pending'];state.setdefault('cancelled_intentions',[]).append(dict(observed_at=now.isoformat(),commitment=p['sha256'],reason='NEW_MONTH_REQUIRES_FRESH_SELECTION'));state['pending']=None
        state=observe(state,data,client,now)
        # Audit cash and events BEFORE collecting a new business selection.
        state['audits']={k:audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
        state['previous_state_sha256']=digest(prior)
        atomic_json(out/'state.json',state)
    args.fundamentals=str(out/'originals');args.capital_usd=(state['strategy']['equity'][-1]['nav'] if state and state['strategy']['equity'] else state['initial_usd'] if state else None)
    report=collect(args)
    now=datetime.now(timezone.utc)
    if not state and report.get('paper_start_permit'):
        state=bootstrap(report,fp,now);state.update(opening_quotes=[],valuation_fx={})
    if state:
        for row in state['strategy']['equity']:
            if row['date'] not in state['valuation_fx']:
                from h3_display import rate_on
                rate=rate_on(report.get('fx_history',{}),row['date'])
                if not rate:raise DataUnavailable('MISSING_VALUATION_FX')
                state['valuation_fx'][row['date']]=rate
        decide(state,report,data,now)
        state['audits']={k:audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
        if prior:
            for k in ('strategy','benchmark'):
                for f in ('trades','equity'):
                    assert state[k][f][:len(prior[k][f])]==prior[k][f],'Changed accepted history'
            assert state['decisions'][:len(prior['decisions'])]==prior['decisions']
        state['previous_state_sha256']=digest(prior) if prior else None
        atomic_json(out/'state.json',state);report=export(report,state,now)
    atomic_json(out/'quality.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('cache','manifest','previous','output'):p.add_argument('--'+n,required=True)
    import signal
    def deadline(signum,frame):raise DataUnavailable('COLLECTION_DEADLINE_EXCEEDED')
    signal.signal(signal.SIGTERM,deadline)
    args=p.parse_args()
    try:run(args)
    except Exception as exc:
        # Keep the last independently accepted ledger; record the actual outage.
        # A source failure must not erase a previously observed opening fill.
        out=Path(args.output);out.mkdir(parents=True,exist_ok=True);prev=Path(args.previous)
        state=read_json(out/'state.json') if (out/'state.json').exists() else read_json(prev/'state.json') if (prev/'state.json').exists() else None
        old=read_json(prev/'quality.json') if (prev/'quality.json').exists() else read_json('public/data/quality-earnings.json')
        old.update(status='COLLECTION_FAILED',generated_at=datetime.now(timezone.utc).isoformat(),paper_start_permit=False,errors=[str(exc) if isinstance(exc,DataUnavailable) else type(exc).__name__])
        if state:
            try:
                state['audits']={k:audit_account(state,k,k=='benchmark') for k in ('strategy','benchmark')}
                prior=read_json(prev/'state.json') if (prev/'state.json').exists() else None
                state['previous_state_sha256']=digest(prior) if prior else None
                atomic_json(out/'state.json',state);old=export(old,state,datetime.now(timezone.utc));old['status']='COLLECTION_FAILED'
            except Exception:
                raise RuntimeError('Independent journal audit failed; refusing publication') from None
        atomic_json(out/'quality.json',old);print('COLLECTION_BLOCKED',old['errors'])
