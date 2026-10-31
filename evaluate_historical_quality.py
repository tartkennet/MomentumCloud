"""Isolated historical reconstruction; imports no prospective account/controller."""
import argparse,copy,json,math,hashlib
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timezone
import momentum_core as core
from momentum_core_data import atomic_json,read_json
from collect_quality import market_universe
from collect_quality_history import data,START,END
from quality_strategy import choose,plan_orders
from quality_audit import audit_selection,audit_plan
from research_momentum10_v2 import RetentionLedger
from research_stocks10 import fee,APGE_COMPLETION
from research_core_ledger import complete_data
from research_momentum10_fx import ReferenceFX
from run_stocks10_research import fx_rows,prior_fx
from research_core_diagnostics import performance
from audit_quality_history_account import native_account
from audit_momentum10_v2 import independent_fx


def selection(d,day,nav,root,allow_partial=False):
    prior=d.days[d.index[day]-1];rows,_,risk=market_universe(d,prior,nav)
    path=root/(day+'.panel.json')
    if not path.exists():raise ValueError('MISSING_SIGNAL_PANEL:'+day)
    panel=read_json(path);mapping={r['ticker']:r for r in panel['rows']};needed=[r['ticker'] for r in rows]
    if any(t not in mapping for t in needed):raise ValueError('INCOMPLETE_CAPACITY_POOL:'+day)
    actual=[mapping[t] for t in needed];coverage=sum(r['resolved'] for r in actual)/len(actual)
    valid=[r for r in actual if r['data_status']=='VERIFIED'];targets=choose(valid,nav);check=audit_selection(valid,targets,nav)
    result=dict(date=day,price_as_of=prior,coverage=coverage,capacity=len(actual),qualified=sum(r['fundamental']['qualified'] for r in valid),targets=targets,audit=check,gaps=[dict(ticker=r['ticker'],reason=r.get('reason')) for r in actual if not r['resolved']])
    if coverage<.90 and not allow_partial:raise PanelBlocked(result,'SOURCE_COVERAGE_BELOW_90')
    if len(targets)!=10:raise PanelBlocked(result,'FEWER_THAN_TEN_FUNDED_TARGETS')
    return result

class PanelBlocked(ValueError):
    def __init__(self,panel,reason):self.panel=panel;super().__init__(reason)


def replay(d,root,fx,start,end,spread,allow_partial=False):
    days=[x for x in d.sessions if start<=x<=end];prior=d.days[d.index[days[0]]-1];initial_fx=prior_fx(fx,days[0]);initial=20000/initial_fx['usdsek'];cfg=replace(core.CONFIG,initial_cash=initial,positions=10,one_way_cost=spread)
    s=RetentionLedger(cash=initial);b=RetentionLedger(cash=initial)
    baseline=dict(date=prior,nav=initial,cash=initial,stock_value=0,receivables=0,positions=0,fees_cumulative=0)
    s.equity=[copy.deepcopy(baseline)];b.equity=[copy.deepcopy(baseline)];month='';previous=False;selections=[];unfilled=[];blocked=None
    for day in days:
        signal=d.days[d.index[day]-1];spy=core.adjusted_history(d,signal,'SPY',200);on=spy[0]>sum(spy)/200
        nav=s.equity[-1]['nav'];plan=None;targets=[]
        if on and (month!=day[:7] or not previous):
            try:
                panel=selection(d,day,nav,root,allow_partial);targets=panel['targets'];prices={t:d.bars(signal)[t][1] for t in s.shares}
                plan=plan_orders(targets,s.shares,nav,s.cash,prices);audit_plan(targets,plan,s.shares,s.cash,nav,prices)
                selections.append(panel)
            except (ValueError,AssertionError) as e:
                blocked=dict(date=day,reason=str(e),panel=e.panel if isinstance(e,PanelBlocked) else None);break
        elif not on and s.shares:plan=dict(orders=[dict(ticker=t,side='SELL',quantity=math.floor(q)) for t,q in sorted(s.shares.items()) if q>=1])
        d.set_day(day);before=dict(s.shares);s.events_before_open(d,day);b.events_before_open(d,day);bars=d.bars(day)
        changed=before!=s.shares
        if plan:
            exits_failed=False
            for order in plan['orders']:
                t=order['ticker'];bar=bars.get(t);p=bar[0] if bar else None;q=order['quantity'];side=order['side']
                if changed or not p or not bar[2] or (side=='BUY' and (exits_failed or p>order['limit'] or q*p+fee(q*p,spread)>s.cash+1e-8)):
                    unfilled.append(dict(date=day,**order,reason='EVENT_MISSING_OPEN_LIMIT_OR_ACTUAL_FUNDING'))
                    if side=='SELL':exits_failed=True
                    continue
                s._trade(day,signal,t,side,q,p,cfg,'HISTORICAL_'+('MEMBERSHIP' if on else 'RISK_OFF'),decision_at=day+'T08:17:00+00:00',historical_simulation=True,input_acquired_at=datetime.now(timezone.utc).isoformat())
            month=day[:7]
        if day==days[0]:
            p=bars['SPY'][0];limit=d.bars(signal)['SPY'][1]*1.02;q=math.floor(initial/limit)
            while q and q*limit+fee(q*limit,spread)>initial:q-=1
            if q and p<=limit:b._trade(day,signal,'SPY','BUY',q,p,cfg,'HISTORICAL_BENCHMARK',historical_simulation=True)
            else:blocked=dict(date=day,reason='BENCHMARK_INITIAL_LIMIT_NOT_FILLED');break
        for l in (s,b):
            nav,stock,claims=l.close_value(d,day);l.equity.append(dict(date=day,nav=nav,cash=l.cash,stock_value=stock,receivables=claims,positions=len(l.shares),fees_cumulative=l.fees))
        previous=on
    def summary(l):
        m=performance(l.equity);m.update(fees_usd=l.fees,market_orders=sum(t['side'] in ('BUY','SELL') for t in l.trades),gross_turnover_initial_pct=100*sum(t['quantity']*t['price'] for t in l.trades if t['side'] in ('BUY','SELL'))/initial,final_nav_usd=l.equity[-1]['nav'])
        series=[dict(r,nav=20000 if i==0 else r['nav']*prior_fx(fx,r['date'])['usdsek']) for i,r in enumerate(l.equity)];m['sek']=performance(series);return m
    actual_end=s.equity[-1]['date'];verified=len(s.equity)>1
    result=dict(requested_start=start,requested_end=end,start=days[0],end=actual_end,execution_reserve=spread,status='PARTIAL_CONDITIONAL' if verified else 'DATA_BLOCKED',financial_go=False,live_approved=False,broker_orders_enabled=False,block=blocked,selections=selections,unfilled=unfilled,initial_sek=20000,initial_fx=initial_fx,initial_usd=initial,strategy=summary(s) if verified else None,benchmark=summary(b) if verified else None)
    if verified:
        checker=independent_fx(d);result['account_audit']=native_account(d,cfg,s,checker);result['benchmark_audit']=native_account(d,cfg,b,checker,True)
        independent=100*(s.equity[-1]['nav']/initial-1);assert abs(independent-result['strategy']['return_pct'])<1e-9
        metrics,periods=core.metrics(s,b);result['gates']=core.gates(metrics);result['monthly_intervals']=len(periods)
    return result,s,b


def run(cache,root,out):
    root=Path(root);out=Path(out);out.mkdir(exist_ok=True);d=complete_data(data(cache,True));d.source.cash_actions=dict(d.source.cash_actions,APGE=copy.deepcopy(APGE_COMPLETION));d.cash_actions=copy.deepcopy(d.source.cash_actions)
    d.fx_xml=root/'ecb-history.xml';d.native_usd=ReferenceFX(d.fx_xml).usd;fx=fx_rows(d.fx_xml)
    report=dict(model='quality-earnings-historical-reconstruction-v1',strategy_model='momentum10-quality-earnings-net-v1',status='PARTIAL_CONDITIONAL',historical_backtest_certified=False,untouched_out_of_sample=False,financial_go=False,live_approved=False,broker_orders_enabled=False,generated_at=datetime.now(timezone.utc).isoformat(),limitations=['Only July–October2026 development-data window, far below30 complete monthly intervals.','Original facts and publication times verified; provider SIC vintage is NOT independently certified.','Price-adjusted universes and original filings are acquired retrospectively; this is not prospective paper trading.','Native-currency claims/fees are included; unresolved merger cash remains locked.'],cases=[])
    starts=[START,'2026-08-03','2026-09-01','2026-10-01']
    for mode in ('frozen_source_gate','coverage_restricted_diagnostic'):
      for spread in (.0015,.003):
        for start in starts:
            end=END if start==START else max(day for day in d.sessions if start[:7]==day[:7] and day<=END)
            name=mode+'_'+start+'_'+str(spread);print('REPLAY',name,flush=True)
            try:
                result,s,b=replay(d,root,fx,start,end,spread,mode!='frozen_source_gate');result['name']=name;result['data_mode']=mode;report['cases'].append(result)
                atomic_json(out/(name+'.strategy.json'),s.to_dict());atomic_json(out/(name+'.benchmark.json'),b.to_dict())
                if start==START and spread==.0015 and mode=='coverage_restricted_diagnostic':report['primary']=result;report['curve']=[dict(date=a['date'],nav_sek=20000 if i==0 else a['nav']*prior_fx(fx,a['date'])['usdsek'],spy_nav_sek=20000 if i==0 else bb['nav']*prior_fx(fx,a['date'])['usdsek']) for i,(a,bb) in enumerate(zip(s.equity,b.equity))];report['trades']=s.trades
            except Exception as e:report['cases'].append(dict(name=name,status='BLOCKED',error=type(e).__name__+': '+str(e)))
            atomic_json(out/'quality-history.json',report)
    report['minimum_source_gate_relaxed_for_diagnostic_only']=True
    report['diagnostic_warning']='The coverage-restricted diagnostic excludes unresolved fundamentals; its ranking can differ from the complete frozen model. It is NOT a strategy backtest or evidence of historical GO.'
    atomic_json(out/'quality-history.json',report);print('HISTORY_DONE',json.dumps([{k:r.get(k) for k in ('name','status','strategy','block','error')} for r in report['cases']]),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',default='.history_market');p.add_argument('--root',default='history_output');p.add_argument('--output',default='history_results');a=p.parse_args();run(a.cache,a.root,a.output)
