"""Build a versioned public research view from complete authenticated evidence."""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from momentum_core_data import atomic_json
from run_stocks10_research import fx_rows,prior_fx


def turnover(state,initial):
    orders=[t for t in state['trades'] if t['side'] in ('BUY','SELL')]
    gross=sum(t['price']*t['quantity'] for t in orders)
    annual=252/(len(state['equity'])-1)
    mean=sum(r['nav'] for r in state['equity'])/len(state['equity'])
    return dict(market_orders=len(orders),gross_notional_usd=gross,
                gross_turnover_annual_pct=100*gross/mean*annual,
                gross_initial_capital_annual_pct=100*gross/initial*annual)


def compact(a):
    return {k:a[k] for k in ('name','variant','interval','stop','delay','mark','execution','status','metrics',
        'gates','financial_pass','operational_pass','decision')}|{
        'audit':{'status':a['audit']['status'],'retained_quantity_checks':a['audit']['retained_quantity_checks'],
                 'stop_fills_checked':a['audit']['stop_fills_checked']},
        'blocked_count':len(a['blocked']),'operational_constraint_count':len(a['operational_constraints']),
        'reused_from_run':a.get('reused_from_run'),'original_case_source':a.get('original_case_source')}


def build(args):
    root=Path(args.evidence);r=json.loads((root/'results.json').read_text())
    assert r['completed'] and len(r['attempts'])==20*len(r['variants'])
    for f,h in r['sources'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
    assert all(a['status']=='COMPLETE' and a['audit']['status']=='PASS' for a in r['attempts'])
    rates=fx_rows(root/'ecb-history.xml')
    assert hashlib.sha256((root/'ecb-history.xml').read_bytes()).hexdigest()==r['fx_sha256']
    oldroot=Path(args.prior)
    old=json.loads((oldroot/'results.json').read_text())
    assert old['completed'] and len(old['attempts'])==40
    initial=20000/prior_fx(rates,r['start'])['usdsek']
    variants=[];spy_comparison=None
    out=Path('public/data/momentum10-v2');out.mkdir(parents=True,exist_ok=True)
    for v in r['variants']:
        a=next(a for a in r['attempts'] if a['name']==f"{v['variant']}_5_last_quote_15")
        folder=root/a['name']
        s=json.loads((folder/'strategy.json').read_text());b=json.loads((folder/'benchmark.json').read_text())
        marks=json.loads((folder/'final_marks.json').read_text())
        curve=json.loads((folder/'curve.json').read_text())
        fx=prior_fx(rates,r['end'])['usdsek']
        stock=sum(q*marks[t] for t,q in s['shares'].items())
        assert math.isclose(stock,s['equity'][-1]['stock_value'],abs_tol=1e-6)
        assert len(curve)==len(s['equity']) and curve[-1]['date']==r['end']
        positions=[dict(ticker=t,quantity=q,close_usd=marks[t],value_sek=q*marks[t]*fx,
                        weight_pct=q*marks[t]/s['equity'][-1]['nav']*100,reference=s['references'].get(t))
                   for t,q in s['shares'].items()]
        payload=dict(variant=v['variant'],result=a,start=r['start'],end=r['end'],
            source_commit=r['source_commit'],workflow_run=str(args.run),
            curve=curve,positions=sorted(positions,key=lambda p:-p['value_sek']),trades=s['trades'],
            native_fx_payments=s.get('fx_payments',[]),cash_sek=s['cash']*fx,claims_sek=sum(c['amount'] for c in s['receivables'])*fx,
            turnover=turnover(s,initial),benchmark_turnover=turnover(b,initial),benchmark_fees_usd=b['fees'])
        atomic_json(out/(v['variant']+'.json'),payload)
        if spy_comparison is None:
            spy=a['calendar']['full']['SPY']
            spy_comparison=dict(return_pct=spy['return_pct'],max_drawdown_pct=spy['max_drawdown_pct'],
                sharpe=spy['daily_sharpe_zero_rf'],fees_usd=b['fees'],turnover=turnover(b,initial))
        main=compact(a)|{'trading':{k:z for k,z in a['trading'].items() if k!='stop_shadow'},
                         'fee_initial_capital_pct':a['fee_initial_capital_pct'],
                         'turnover':payload['turnover'],'sek':a['sek']}
        variants.append(dict(v,main=main))
    prior={}
    for v in ('A','B'):
        a=next(a for a in old['attempts'] if a['name']==f'{v}_5_last_quote_0.0015')
        state=json.loads((oldroot/a['name']/'strategy.json').read_text())
        prior[v]={'metrics':a['metrics'],'gates':a['gates'],'turnover':turnover(state,initial),
                  'fee_initial_capital_pct':a['metrics']['ActualFees_USD']/initial*100}
    comparators=r['comparators']
    saved_h3=json.loads(Path('docs/CORE_PORTFOLIO_H3_RESULTS_20261029.json').read_text())
    control=next(a for a in saved_h3['attempts'] if a['phase']=='extension' and a['name']=='formation_assumed_5_15bps_last_quote')['control_diagnostics']['full']['strategy']
    assert math.isclose(control['return_pct'],comparators['Core']['metrics']['TotalReturn_pct'],abs_tol=1e-9)
    assert math.isclose(control['max_drawdown_pct'],comparators['Core']['metrics']['DailyMaxDrawdown_pct'],abs_tol=1e-9)
    comparators['Core']['metrics']['DailySharpe_zero_rf']=control['daily_sharpe_zero_rf']
    comparators['Core']['sharpe_source']='Verified saved H3 control diagnostics; no replay'
    for name,c in comparators.items():
        # The original H3/Core fee is exactly .0015 * each market notional.
        # State that different fee model; do not imply identical retail costs.
        c['gross_notional_inferred_usd']=c['metrics']['ActualFees_USD']/.0015
        c['gross_initial_capital_annual_pct']=100*c['gross_notional_inferred_usd']/100000*252/(len(curve)-1)
    manifest={k:r[k] for k in ('model','status','completed','start','end','source_commit','sources','input_manifest',
        'fx_sha256','h3_development','h3_forward','paper_candidate','financial_candidate','publication_variant',
        'evidence_class','untouched_out_of_sample','live_approved','broker_orders_enabled','forward_paper_started','hypothesis_order')}
    manifest['native_dividend_repair']=r.get('native_dividend_repair')
    manifest.update(workflow_run=str(args.run),artifact_zip_sha256=args.artifact_sha,variants=variants,
                    prior_stocks10=prior,comparators=comparators,spy_comparison=spy_comparison,attempts=[compact(a) for a in r['attempts']])
    atomic_json('public/data/momentum10-v2.json',manifest)
    lines=['# Momentum10 v2 — completed retention and stop research','',
        f"**Status: {r['status']}**. Prospective paper started: false. Broker orders/live approved: false.",'',
        f"Original frozen protocol/source: `f156b4175ad59a119b6f0e7071c90e928366637b`. Executed source: `{r['source_commit']}`.",
        f"[Complete evidence run {args.run}](https://github.com/tartkennet/MomentumCloud/actions/runs/{args.run}); immutable draft release `m10v2-research-{args.run}-1`.",
        f'Artifact ZIP SHA256 `{args.artifact_sha}`. Saved inputs and original ECB fixing reused offline.',
        'All results are reused DEVELOPMENT history, not untouched OOS. H3 and Stocks10 A/B unchanged.',
        'Completed M1/M2 states from the first run are reused with new full independent reconciliation; native-currency payments must be zero and financial metrics identical. Native TD repair and its independent audit apply only to the new study.','',
        '| Main case | Net USD % | DD USD % | Sharpe | Fees USD | Orders | Gross turnover / avg NAV / year % | Net SEK % | DD SEK % |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in variants:
        a=v['main'];m=a['metrics']
        lines.append(f"| {v['variant']} | {m['TotalReturn_pct']:.2f} | {m['DailyMaxDrawdown_pct']:.2f} | {m['DailySharpe_zero_rf']:.2f} | {m['ActualFees_USD']:.2f} | {a['trading']['market_orders']} | {a['turnover']['gross_turnover_annual_pct']:.2f} | {a['sek']['return_pct']:.2f} | {a['sek']['max_drawdown_pct']:.2f} |")
    lines+=['','Main case = 5-session assumed merger payment, last observed confirmed-halt mark, 15bp execution reserve PLUS max(1USD,.25%) commission and .25% FX reserve. Stress uses 30bp execution reserve. Gross turnover counts buys+sells, including initial purchases; one-way is half.','',
        '## All financial and operational decisions','',
        '| Variant | Financial pass / 20 | Paper pass / 20 | Failed financial gates (scenario counts) | Operational reasons |',
        '|---|---:|---:|---|---|']
    for v in variants:
        cases=[a for a in r['attempts'] if a['variant']==v['variant']]
        failed=Counter(g['gate'] for a in cases for g in a['gates'] if not g['pass'])
        operations=Counter(e['reason'] for a in cases for e in a['blocked']+a['operational_constraints'])
        lines.append(f"| {v['variant']} | {sum(a['financial_pass'] for a in cases)} | {sum(a['decision']=='PAPER_ONLY' for a in cases)} | {dict(failed)} | {dict(operations)} |")
    lines+=['','## Comparison without rerunning completed experiments','',
        '| Saved model | Net USD % | DD USD % | Sharpe | Fees USD | Gross notional / initial capital / year % |',
        '|---|---:|---:|---:|---:|---:|']
    for v,a in prior.items():
        m=a['metrics'];lines.append(f"| Stocks10 {v} | {m['TotalReturn_pct']:.2f} | {m['DailyMaxDrawdown_pct']:.2f} | {m['DailySharpe_zero_rf']:.2f} | {m['ActualFees_USD']:.2f} | {a['turnover']['gross_initial_capital_annual_pct']:.2f} |")
    for v,c in comparators.items():
        m=c['metrics'];sh=m.get('DailySharpe_zero_rf');lines.append(f"| {v} (100k USD, different 15bp fees) | {m['TotalReturn_pct']:.2f} | {m['DailyMaxDrawdown_pct']:.2f} | {sh if sh is not None else 'not in saved summary'} | {m['ActualFees_USD']:.2f} | {c['gross_initial_capital_annual_pct']:.2f} |")
    spy=variants[0]['main']['metrics']['SPYTotalReturn_pct']
    lines+=['',f'Same-small-account SPY total return: {spy:.2f}% USD; DD {spy_comparison['max_drawdown_pct']:.2f}%; Sharpe {spy_comparison['sharpe']:.2f}; fees {spy_comparison['fees_usd']:.2f} USD. It is only a comparator, never a Momentum10 asset.',
        'H3/Core turnover is inferred from their verified proportional fee function and reported on INITIAL capital, not average NAV. This preserves honest comparability of definitions; retail fees differ.','',
        '## Interpretation, recovery and limitations','',
        'C is INFEASIBLE at the declared risk budget: its low trading cost and lower drawdown must be read together with eleven blocked complete baskets in the main case. It cannot be presented as a successful risk solution. QV has three entries whose prescribed stop distance is at least 100%, giving no positive stop barrier; these fail operational admission.','']
    base=next(v for v in variants if v['variant']=='M3')['main'];b0=prior['B']['metrics']
    lines += [f"The PRESELECTED quarterly retention case M3 pays {base['metrics']['ActualFees_USD']:.2f} USD versus B's {b0['ActualFees_USD']:.2f}, with {base['trading']['market_orders']} market orders versus B's {prior['B']['turnover']['market_orders']}. Its net-return difference is {base['metrics']['TotalReturn_pct']-b0['TotalReturn_pct']:.2f} percentage points; DD difference is {base['metrics']['DailyMaxDrawdown_pct']-b0['DailyMaxDrawdown_pct']:.2f} points. Do not select frequency by the largest historical return.",
        'M1/M2/M3 isolate selection frequency while retaining quantities. Q10/QV compare close-stop principles at the prechosen quarter. Same-close stops create cash slots, not immediate replacement or repurchase. C, if present, is the preregistered next portfolio-exposure hypothesis, not an optimized extra stop setting.','']
    for v in variants:
        a=next(a for a in r['attempts'] if a['name']==v['main']['name']);t=a['trading'];sh=t['stop_shadow'];parts=[]
        for h in ('21','63'):
            observed=[e[h] for e in sh if e[h]['status']=='OBSERVED_PRICE_ONLY']
            parts.append(f"{h} sessions: {len(observed)} comparable, {sum(e['return_pct']>0 for e in observed)} end above exit price, {sum(e['regained_entry_within_horizon'] for e in observed)} regain entry within horizon")
        lines.append(f"* {v['variant']}: worst episode {t['maximum_drawdown_episode']}. Individual stop fills {len(sh)}; {sum(e['gap_below_level_pct'] is not None and e['gap_below_level_pct']<0 for e in sh)} below the then-current barrier. {'; '.join(parts)}.")
    lines += ['', 'Post-stop returns are price-only, split-neutral DESCRIPTIVE shadows; no future quote feeds a decision, no dividends/costs are credited, incomplete/delisted windows stay missing.',
        'All cash/claims/corporate events and NAV, full eligible ranks, retention, calendar, stop basis/blacklist/timing, actual opening prices and financial measures are independently reconciled. Same vendor, not independent vendor confirmation.',
        f"Paper candidate under the frozen priority: {r['paper_candidate']}. Financial candidate before operational screens: {r['financial_candidate']}. If none is admitted, no new prospective account is created and no past trade is relabelled as new paper evidence.",
        'Operational reason counts are daily observations, not counts of independent incidents. Native dividend claims stay in their declared currency until payment, are marked with prior-date ECB crosses, and incur the disclosed conversion reserve; no actual bank FX rate is invented.',
        'Extra/subwhole corporate entitlements and missing quotes remain visible and fail operational admission. Low cost alone is not a financial GO. Closing-price stop tests cannot establish intraday broker-stop performance or guarantee a maximum future loss.',
        'No gate, interval anchor, stop multiplier, reference-price rule or ranking parameter was tuned after results. If the one conditional risk-budget case also fails, its failure remains part of the register; do not silently invent a seventh variant.','']
    Path('docs/MOMENTUM10_V2_RESULTS_20261031.md').write_text('\n'.join(lines))
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('evidence','prior','run','artifact-sha'):p.add_argument('--'+n,required=True)
    build(p.parse_args())
