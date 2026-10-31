"""Offline finite, preregistered Momentum10 v3 experiment register."""
import argparse
import copy
import hashlib
import json
import math
import socket
import statistics
import subprocess
from collections import Counter
from dataclasses import replace
from pathlib import Path

import momentum_core as core
from momentum_core_data import atomic_json
from research_core_actions import supplement
from research_core_ledger import complete_data
from research_core_diagnostics import performance,describe
from run_core_normalized_research import verify_inputs,payment_policy
from run_core_risk_research import make_data,EXTENSION_END,DELAYS
from research_stocks10 import Stocks10Ledger,APGE_COMPLETION
from run_stocks10_research import fx_rows,prior_fx,converted
from research_momentum10_v3 import SelectionLedger,MODEL
from audit_momentum10_v3 import audit
from diagnose_momentum10_v3 import signal_risk
from run_portfolio_forward import qualify,fingerprint as h3_fingerprint
from research_momentum10_fx import ReferenceFX,supplement_native_dividend

FILES=('research_momentum10_v3.py','audit_momentum10_v3.py','run_momentum10_v3.py',
       'diagnose_momentum10_v3.py','docs/MOMENTUM10_V3_PROTOCOL_20261031.md','tests/test_momentum10_v3.py')


def recovery(rows):
    peak=rows[0];worst=0.;pair=(peak,peak)
    for row in rows:
        if row['nav']>peak['nav']:peak=row
        dd=row['nav']/peak['nav']-1
        if dd<worst:worst=dd;pair=(peak,row)
    a,b=pair
    recovered=next((r['date'] for r in rows if r['date']>b['date'] and r['nav']>=a['nav']),None)
    return dict(peak=a['date'],trough=b['date'],drawdown_pct=worst*100,recovered=recovered)


def diagnostics(data,s):
    orders=[t for t in s.trades if t['side'] in ('BUY','SELL')]
    gross=sum(t['price']*t['quantity'] for t in orders)
    mean=statistics.fmean(r['nav'] for r in s.equity)
    stops=[t for t in orders if t['reason'].startswith('STOP_')]
    shadow=[]
    for t in stops:
        item={'date':t['date'],'ticker':t['ticker'],'fill_open':t['price'],
              'entry_reference':t['entry_reference'],'stop_level':t['stop_level'],
              'gap_below_level_pct':100*(t['price']/t['stop_level']-1) if t['stop_level'] and t['stop_level']>0 else None,
              'price_only_entry_return_pct':100*(t['price']/t['entry_reference']-1) if t['entry_reference'] and t['entry_reference']>0 else None}
        begin=data.index[t['date']]
        for horizon in (21,63):
            field=str(horizon)
            if begin+horizon>=len(data.days):item[field]={'status':'END_OF_WINDOW'};continue
            days=data.days[begin+1:begin+horizon+1]
            symbol=t['ticker']
            actions=list(data.cash_actions.items())+list(data.stock_actions.items())
            if any(symbol==a and t['date']<e['effective_date']<=days[-1] for a,e in actions):
                item[field]={'status':'CORPORATE_ACTION_NOT_COMPARABLE'};continue
            factor=1.;prices=[]
            events={e['execution_date']:e for e in data.source.splits_by_ticker.get(symbol,[])}
            for day in days:
                if day in events:factor*=events[day]['split_to']/events[day]['split_from']
                bar=data.bars(day).get(symbol)
                if not bar:prices=[];break
                prices.append(bar[1]*factor)
            item[field]=({'status':'OBSERVED_PRICE_ONLY','return_pct':100*(prices[-1]/t['price']-1),
                          'regained_entry_within_horizon':bool(t['entry_reference'] and max(prices)>=t['entry_reference'])}
                         if prices else {'status':'MISSING_QUOTE'})
        shadow.append(item)
    return dict(gross_notional_usd=gross,gross_turnover_annual_pct=gross/mean*252/max(1,len(s.equity)-1)*100,
        one_way_turnover_annual_pct=gross/mean*126/max(1,len(s.equity)-1)*100,
        market_orders=len(orders),order_reasons=dict(Counter(t['reason'] for t in orders)),
        individual_stop_fills=len(stops),ordinary_selections=sum(t.get('ordinary',False) for t in s.targets),
        regime_reentry_selections=sum(t['risk_on'] and not t.get('ordinary',False) for t in s.targets),
        maximum_drawdown_episode=recovery(s.equity),stop_shadow=shadow,
        shadow_convention='Descriptive future split-neutral PRICE ONLY, no dividends/costs, no portfolio returns or decision input.')


def run(args):
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    if (out/'results.json').exists():raise ValueError('Use a fresh evidence directory')
    old=json.loads((Path(args.prior)/'results.json').read_text())
    assert old['completed'] and len(old['attempts'])==40
    for name,digest in old['source_files'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    rates=fx_rows(Path(args.prior)/'ecb-history.xml')
    assert hashlib.sha256((Path(args.prior)/'ecb-history.xml').read_bytes()).hexdigest()==old['fx_sha256']
    (out/'ecb-history.xml').write_bytes((Path(args.prior)/'ecb-history.xml').read_bytes())
    manifest=verify_inputs(args.cache,args.manifest)
    data=complete_data(supplement(make_data(args.cache,EXTENSION_END,True)))
    data.source.cash_actions=dict(data.source.cash_actions,APGE=copy.deepcopy(APGE_COMPLETION))
    data.source.cash_actions['RAPT']=dict(effective_date='2026-03-03',cash_per_share=58.,
        source_url='https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-124',
        sec_url='https://www.sec.gov/Archives/edgar/data/1131399/000165495426001801/a1763v.htm')
    data.fx_xml=Path(args.prior)/'ecb-history.xml'
    data.native_usd=ReferenceFX(data.fx_xml).usd
    native_repair=supplement_native_dividend(data)
    initial=20000/prior_fx(rates,data.sessions[0])['usdsek']
    assert math.isclose(initial,20000/old['initial_fx']['usdsek'])
    report=dict(model=MODEL,status='RUNNING',completed=False,evidence_class='DEVELOPMENT_RESEARCH',
        untouched_out_of_sample=False,live_approved=False,broker_orders_enabled=False,
        forward_paper_started=False,start=data.sessions[0],end=data.sessions[-1],initial_sek=20000,
        preregistered_commit='1f6a077f5ada25eda13731fec66a4034f398cc2c',
        source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        sources={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in FILES},
        input_manifest=manifest,fx_sha256=old['fx_sha256'],h3_development=qualify(),h3_forward=h3_fingerprint(),
        prior_release='stocks10-research-41180905339-1',comparators=old['comparators'],attempts=[],variants=[])
    report['native_dividend_repair']=native_repair
    from diagnose_momentum10_v3 import diagnose
    report['baseline_diagnostic']=diagnose(data,Path(args.v2),out)
    v2=json.loads((Path(args.v2)/'results.json').read_text())
    assert v2['completed'] and len(v2['attempts'])==120
    for f,h in v2['sources'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
    report['prior_v2_source']=v2['source_commit']
    report['prior_stocks10']={v:next(a for a in old['attempts'] if a['name']==f'{v}_5_last_quote_0.0015') for v in ('A','B')}
    report['hypothesis_order']=['R']
    memo,independent={},{}
    specs=[('R_M1_none',1,'none')]
    for identifier,interval,stop in specs:
        stage=identifier[0]
        for mark in ('last_quote','offer_value'):
            complete_data(data,mark)
            for delay in DELAYS:
                assumptions=payment_policy(data,delay)
                for execution in (.0015,.003):
                    name=f'{identifier}_{delay}_{mark}_{round(execution*10000)}'
                    case=dict(name=name,variant=identifier,interval=interval,stop=stop,delay=delay,
                              mark=mark,execution=execution,selection_stage=stage,payment_assumptions=assumptions,status='RUNNING')
                    report['attempts'].append(case);atomic_json(out/'results.json',report)
                    print('START '+name,flush=True)
                    try:
                        config=replace(core.CONFIG,model=MODEL,initial_cash=initial,positions=10,one_way_cost=execution)
                        s=SelectionLedger(cash=initial,interval=interval,stop_mode=stop,stage=stage)
                        b=Stocks10Ledger(cash=initial,benchmark_account=True)
                        s.first_is_month_boundary=data.first_is_month_boundary()
                        for day in data.sessions:
                            data.set_day(day);b.step(data,day,config,benchmark=True);s.step_stocks(data,day,config,memo)
                        metrics,periods=core.metrics(s,b)
                        metrics['DailySharpe_zero_rf']=performance(s.equity)['daily_sharpe_zero_rf']
                        checks=audit(data,config,s,b,metrics,independent)
                        gates=core.gates(metrics);finance=all(g['pass'] for g in gates)
                        operational=not s.blocked and not s.constraints and checks['accounting']['max_volume_participation']<=.01
                        case.update(status='COMPLETE',metrics=metrics,gates=gates,audit=checks,
                            financial_pass=finance,operational_pass=operational,
                            decision='PAPER_ONLY' if finance and operational else 'NO_GO',
                            sek=performance(converted(s,rates)),spy_sek=performance(converted(b,rates)),
                            fee_initial_capital_pct=s.fees/initial*100,blocked=s.blocked,
                            operational_constraints=s.constraints,
                            trading=diagnostics(data,s),signal_risk=signal_risk(data,s),
                            calendar=describe([dict(r,spy_nav=z['nav']) for r,z in zip(s.equity,b.equity)]))
                        folder=out/name;folder.mkdir()
                        atomic_json(folder/'strategy.json',s.to_dict());atomic_json(folder/'benchmark.json',b.to_dict())
                        atomic_json(folder/'result.json',case)
                        # Export observed cached marks now, avoiding any later price API.
                        atomic_json(folder/'final_marks.json',{t:data.bars(data.sessions[-1])[t][1] for t in s.shares})
                        atomic_json(folder/'curve.json',[dict(date=r['date'],nav_sek=r['nav']*prior_fx(rates,r['date'])['usdsek'],
                            spy_sek=z['nav']*prior_fx(rates,z['date'])['usdsek']) for r,z in zip(s.equity,b.equity)])
                        print('DONE '+name+' '+json.dumps(dict(metrics=metrics,fees=s.fees,orders=case['trading']['market_orders'],paper=case['decision'])),flush=True)
                    except Exception as e:
                        checkpoint=out/(name+'_TECHNICAL_PARTIAL');checkpoint.mkdir(exist_ok=True)
                        atomic_json(checkpoint/'strategy.json',s.to_dict());atomic_json(checkpoint/'benchmark.json',b.to_dict())
                        case.update(status='TECHNICAL_BLOCK',error=type(e).__name__+': '+str(e))
                        report['status']='TECHNICAL_BLOCK';atomic_json(out/'results.json',report)
                        print('BLOCKED '+name+' '+case['error'],flush=True);raise
                    atomic_json(out/'results.json',report)
        cases=[a for a in report['attempts'] if a['variant']==identifier]
        report['variants'].append(dict(variant=identifier,financial_pass=all(a['financial_pass'] for a in cases),
            paper_pass=all(a['decision']=='PAPER_ONLY' for a in cases),scenarios=len(cases)))
        atomic_json(out/'results.json',report)
        if interval==1 and stop=='none':
            admitted=report['variants'][-1]['paper_pass']
            if not admitted and stage in ('R','T'):
                next_stage={'R':'T','T':'D'}[stage]
                specs.append((next_stage+'_M1_none',1,'none'));report['hypothesis_order'].append(next_stage)
            else:
                for risk in ('none','fixed10','vol'):
                    for frequency in (1,2,3):
                        if frequency==1 and risk=='none':continue
                        specs.append((stage+f'_M{frequency}_'+risk,frequency,risk))
        atomic_json(out/'results.json',report)
    qualified={v['variant'] for v in report['variants'] if v['paper_pass']}
    financial={v['variant'] for v in report['variants'] if v['financial_pass']}
    report['paper_candidate']=next((v[0] for v in specs if v[0] in qualified),None)
    report['financial_candidate']=next((v[0] for v in specs if v[0] in financial),None)
    report['publication_variant']=report['paper_candidate'] or specs[-9][0]
    report['status']='PAPER_ONLY' if report['paper_candidate'] else 'NO_GO'
    report['completed']=True;atomic_json(out/'results.json',report)
    print('FINAL '+json.dumps(report['variants']),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('cache','manifest','prior','v2','output'):p.add_argument('--'+name,required=True)
    args=p.parse_args()
    def offline(*a,**kw):raise RuntimeError('Network forbidden in Momentum10 v3 replay')
    socket.socket.connect=offline;socket.create_connection=offline
    run(args)
