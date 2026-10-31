"""Publish only completed independently reconciled, source-bound v3 evidence."""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from momentum_core_data import atomic_json
from build_momentum10_v2_view import compact,turnover
from run_stocks10_research import fx_rows,prior_fx


def build(args):
    root=Path(args.evidence);r=json.loads((root/'results.json').read_text())
    assert r['completed'] and len(r['attempts'])==20*len(r['variants'])
    assert all(a['status']=='COMPLETE' and a['audit']['status']=='PASS' for a in r['attempts'])
    for f,h in r['sources'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
    rates=fx_rows(root/'ecb-history.xml')
    assert hashlib.sha256((root/'ecb-history.xml').read_bytes()).hexdigest()==r['fx_sha256']
    prior=json.loads(Path('public/data/momentum10-v2.json').read_text())
    assert prior['completed'] and prior['source_commit']==r['prior_v2_source']
    for f,h in prior['sources'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
    initial=20000/prior_fx(rates,r['start'])['usdsek'];fx=prior_fx(rates,r['end'])['usdsek']
    out=Path('public/data/momentum10-v3');out.mkdir(parents=True,exist_ok=True)
    variants=[]
    for v in r['variants']:
        a=next(a for a in r['attempts'] if a['name']==v['variant']+'_5_last_quote_15')
        folder=root/a['name'];s=json.loads((folder/'strategy.json').read_text());b=json.loads((folder/'benchmark.json').read_text())
        marks=json.loads((folder/'final_marks.json').read_text());curve=json.loads((folder/'curve.json').read_text())
        assert math.isclose(sum(q*marks[t] for t,q in s['shares'].items()),s['equity'][-1]['stock_value'],abs_tol=1e-6)
        assert len(curve)==len(s['equity']) and curve[-1]['date']==r['end']
        positions=[dict(ticker=t,quantity=q,close_usd=marks[t],value_sek=q*marks[t]*fx,
                       weight_pct=q*marks[t]/s['equity'][-1]['nav']*100,reference=s['references'].get(t)) for t,q in s['shares'].items()]
        payload=dict(variant=v['variant'],result=a,start=r['start'],end=r['end'],source_commit=r['source_commit'],workflow_run=str(args.run),
            curve=curve,positions=sorted(positions,key=lambda p:-p['value_sek']),trades=s['trades'],native_fx_payments=s['fx_payments'],
            targets=s['targets'],cash_sek=s['cash']*fx,claims_sek=sum(c['amount'] for c in s['receivables'])*fx,
            turnover=turnover(s,initial),benchmark_turnover=turnover(b,initial),benchmark_fees_usd=b['fees'])
        atomic_json(out/(v['variant']+'.json'),payload)
        main=compact(a)|dict(trading={k:z for k,z in a['trading'].items() if k!='stop_shadow'},
            fee_initial_capital_pct=a['fee_initial_capital_pct'],turnover=payload['turnover'],sek=a['sek'],signal_risk=a['signal_risk'])
        variants.append(dict(v,main=main))
    manifest={k:r[k] for k in ('model','status','completed','start','end','source_commit','sources','input_manifest','fx_sha256',
        'h3_development','h3_forward','preregistered_commit','paper_candidate','financial_candidate','publication_variant','evidence_class','untouched_out_of_sample',
        'live_approved','broker_orders_enabled','forward_paper_started','hypothesis_order','baseline_diagnostic')}
    attribution=json.loads(Path('docs/MOMENTUM10_V3_ATTRIBUTION_20261031.json').read_text())
    assert attribution['status']=='PASS' and not attribution['strategy_replay']
    for a in attribution['variants'].values():assert math.isclose(sum(p for t,p in a['drawdown_contribution_usd']),a['episode']['net_pnl_usd'],abs_tol=1e-7)
    manifest.update(baseline_attribution=attribution,workflow_run=str(args.run),variants=variants,attempts=[compact(a) for a in r['attempts']],
        prior_stocks10=prior['prior_stocks10'],prior_v2=prior['variants'],comparators=prior['comparators'],spy_comparison=prior['spy_comparison'],
        baseline_order_diagnostic=json.loads(Path('docs/MOMENTUM10_V3_BASELINE_DIAGNOSTIC_20261031.json').read_text()))
    atomic_json(Path('public/data/momentum10-v3.json'),manifest)
    lines=['# Momentum 10 v3 — complete issue #33 research results','',f"Status: **{r['status']}**. {len(r['attempts'])} completed scenarios. Source `{r['source_commit']}`; [run](https://github.com/tartkennet/MomentumCloud/actions/runs/{args.run}).",
        '', 'Reviewed historical DEVELOPMENT data, not untouched OOS. Frozen hypothesis order: '+', '.join(r['hypothesis_order'])+'. No source/parameter/gate tuning after outcomes.','',
        '| Attempt | Net USD % | DD % | Sharpe | Fees USD | Orders | Gross turnover / mean NAV / year % | Net SEK % | DD SEK % | Financial /20 | Paper /20 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in variants:
        a=v['main'];m=a['metrics'];cases=[z for z in r['attempts'] if z['variant']==v['variant']]
        lines.append(f"| {v['variant']} | {m['TotalReturn_pct']:.2f} | {m['DailyMaxDrawdown_pct']:.2f} | {m['DailySharpe_zero_rf']:.2f} | {m['ActualFees_USD']:.2f} | {a['trading']['market_orders']} | {a['turnover']['gross_turnover_annual_pct']:.2f} | {a['sek']['return_pct']:.2f} | {a['sek']['max_drawdown_pct']:.2f} | {sum(c['financial_pass'] for c in cases)} | {sum(c['decision']=='PAPER_ONLY' for c in cases)} |")
    lines += ['', 'Main case: assumed payment after five sessions, confirmed-halt last quote, 15bp execution reserve PLUS max(1USD,.25%) commission and .25% FX reserve. Stress execution30bp. Whole-share cash accounts start SEK20,000 with the same strictly prior-date ECB input. Gross turnover is buys+sells including initial purchases; one-way is half.','',
        '## Failed gates and operational constraints','']
    for v in variants:
        cases=[a for a in r['attempts'] if a['variant']==v['variant']]
        failed=Counter(g['gate'] for a in cases for g in a['gates'] if not g['pass'])
        reasons=Counter(e['reason'] for a in cases for e in a['blocked']+a['operational_constraints'])
        lines.append(f"* {v['variant']}: financial failures {dict(failed)}; operational observations {dict(reasons)}.")
    lines += ['', '## Saved comparators — no repeated prior experiments','', '| Model | Net USD % | DD USD % | Sharpe | Fees USD |', '|---|---:|---:|---:|---:|']
    entries=[('SPY same small account',dict(TotalReturn_pct=prior['spy_comparison']['return_pct'],DailyMaxDrawdown_pct=prior['spy_comparison']['max_drawdown_pct'],DailySharpe_zero_rf=prior['spy_comparison']['sharpe'],ActualFees_USD=prior['spy_comparison']['fees_usd']))]
    entries += [('Stocks10 '+k,a['metrics']) for k,a in prior['prior_stocks10'].items()]
    entries += [('v2 '+v['variant'],v['main']['metrics']) for v in prior['variants']]
    entries += [(k+' (100k USD, 15bp costs)',a['metrics']) for k,a in prior['comparators'].items()]
    for name,m in entries:lines.append(f"| {name} | {m['TotalReturn_pct']:.2f} | {m['DailyMaxDrawdown_pct']:.2f} | {m['DailySharpe_zero_rf']:.2f} | {m['ActualFees_USD']:.2f} |")
    lines += ['', 'H3/Core are saved large-account research controls with different capital/cost conditions. SPY is never a Momentum10 holding. Financial gates remain USD; SEK DD is shown separately and is not hidden.','',
        '## Drawdown, concentration, stops and independent checks','']
    for v in variants:
        a=next(a for a in r['attempts'] if a['name']==v['main']['name']);risk=a['signal_risk'];t=a['trading']
        lines.append(f"* {v['variant']}: worst episode {t['maximum_drawdown_episode']}; {t['individual_stop_fills']} stop fills, {sum(e['gap_below_level_pct'] is not None and e['gap_below_level_pct']<0 for e in t['stop_shadow'])} below barrier. Max mean pair correlation at selection {risk['max_mean_pair_correlation']}; max biopharma-name hint slots {risk['max_biopharma_named_slots']} (unverified/incomplete).")
    lines += ['', 'See the separately reconciled per-stock baseline drawdown attribution in `MOMENTUM10_V3_ATTRIBUTION_20261031.md` and its complete JSON. Monthly v2 AXTI contributed USD -513.59 (34.67% of its net drawdown-period loss); peak observed single-name weight reached 26.10%. Retained quantities permit weight drift.']
    maxerr=max(a['audit']['accounting']['max_nav_error_usd'] for a in r['attempts'])
    lines += ['',f'All independent checks PASS. Largest daily accounting residual {maxerr:.12g} USD. Full raw opening fills, fees, integer market quantities, native claims/FX, NAV, rankings, trend/cluster rules, retention, calendars, stop basis/blacklists and financial gates were checked. Same vendor is not independent market data.',
        '', 'Historical sector labels remain unavailable: no current SIC/GICS was injected into historical signals. Return clusters are observable risk groups, not industry classification. PIT-name hints are incomplete diagnostics only; they never affect decisions.',
        '',f"Paper candidate: {r['paper_candidate']}; financial candidate: {r['financial_candidate']}. No new paper account was started unless separately frozen for future-only observation; no broker orders/live approval.",
        '', 'All three preregistered selection mechanisms and the final finite 3×3 interval/stop matrix are preserved. If none qualifies, the supported register is exhausted: a more flattering historical combination is not a justified fourth hypothesis. Additional selection factors need new causal evidence and fresh preregistration, not reuse of these results as untouched validation.','']
    Path('docs/MOMENTUM10_V3_RESULTS_20261031.md').write_text('\n'.join(lines))
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--run',required=True);build(p.parse_args())
