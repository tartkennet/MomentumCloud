"""Replay the frozen diversified H2 hypothesis, reusing audited base selections."""
import argparse
import copy
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import run_core_normalized_research as base
import research_portfolio_diversified as candidate
from audit_portfolio_diversified import audit_targets

EXTRA_FILES=('research_portfolio_risk.py','audit_portfolio_risk.py','run_portfolio_risk_research.py',
             'tests/test_portfolio_risk.py','docs/CORE_PORTFOLIO_RISK_H1_20261029.md',
             'research_portfolio_diversified.py','audit_portfolio_diversified.py','run_portfolio_diversified.py',
             'tests/test_portfolio_diversified.py','docs/CORE_PORTFOLIO_RISK_H2_20261029.md')


@contextmanager
def hypothesis(reference,h1_reference):
    root=Path(reference)
    saved=json.loads((root/'attempts.json').read_text())
    verified=json.loads((base.ROOT/'docs/CORE_FORMATION_RESULTS_20261029.json').read_text())
    assert saved['all_attempts_completed'] and len(saved['attempts'])==40
    cases={(a['phase'],a['name']):a for a in saved['attempts']}
    for a in verified['attempts']:
        match=cases[a['phase'],a['name']]
        assert match['metrics']==a['metrics'] and match['gates']==a['gates']
        assert match['selection_audit']['status']=='PASS' and match['accounting_audit']=='PASS'
    h1=json.loads((Path(h1_reference)/'attempts.json').read_text())
    h1_verified=json.loads((base.ROOT/'docs/CORE_PORTFOLIO_H1_RESULTS_20261029.json').read_text())
    assert h1['all_attempts_completed'] and len(h1['attempts'])==40
    h1_cases={(a['phase'],a['name']):a for a in h1['attempts']}
    for a in h1_verified['attempts']:
        m=h1_cases[a['phase'],a['name']]
        assert m['metrics']==a['metrics'] and m['gates']==a['gates']
        assert m['accounting_audit']=='PASS' and m['selection_audit']['status']=='PASS'
    signals=json.loads((root/'holding_input_preflight.json').read_text())['all_signals']
    references={s['date']:s for s in signals}
    assert len(references)==len(signals)
    saved_bindings=(base.formation_model.MODEL,base.formation_model.select_targets,
                    base.audit_targets,base.FILES,base.render_report,base.ResearchLedger,base.scan_holding_inputs)
    def selector(data,day,config):
        return candidate.select_targets(data,day,config,saved_signal=references[day])
    def validator(data,config,targets,trades=(),memo=None,**kwargs):
        return audit_targets(data,config,targets,references,trades,memo)
    def scan(data,config):
        result=saved_bindings[6](data,config)
        fraction=1.
        for signal in result['all_signals']:
            if signal['risk_on']:
                fraction=next(r['weight'] for r in signal['targets'] if r.get('benchmark_core'))
            else:
                signal['targets']=[candidate.core_target(fraction)]
        result['scope']+=' SPY core remains during risk-off; every raw session already requires SPY.'
        return result
    def report(register,path):
        for a in register['attempts']:
            match=cases[a['phase'],a['name']]
            a['formation_control_metrics']=match['metrics']
            a['formation_control_gates']=match['gates']
            a['formation_control_diagnostics']=match['diagnostics']
            prior=h1_cases[a['phase'],a['name']]
            a['h1_control_metrics']=prior['metrics']
            a['h1_control_gates']=prior['gates']
            a['h1_control_diagnostics']=prior['diagnostics']
            if a['status']=='COMPLETE':
                folder=Path(path).parent/a['phase']/a['name']
                state=json.loads((folder/'Momentum_core_state.json').read_text())
                assert abs(state['benchmark_core_weight']-a['selection_audit']['last_benchmark_core_weight'])<1e-10
        register['hypothesis']='H2 equal-risk diversified benchmark core and momentum sleeve'
        register['formation_controls_reused_without_replay']=40
        saved_bindings[4](register,path)
        text=Path(path).read_text()
        text+='\n## Completed PR23 comparator, identical assumptions\n\n| Phase | Policy/mark | Cost bp | PR23 net % | PR23 DD % | New net % | New DD % | H1 net % | H1 DD % |\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n'
        for a in register['attempts']:
            if a['status']=='COMPLETE':
                m,b=a['metrics'],a['formation_control_metrics']
                text+=f"| {a['phase']} | {a['policy']}/{a['halt_mark_policy']} | {a['cost']*10000:.0f} | {b['TotalReturn_pct']:.4f} | {b['DailyMaxDrawdown_pct']:.4f} | {m['TotalReturn_pct']:.4f} | {m['DailyMaxDrawdown_pct']:.4f} | {a['h1_control_metrics']['TotalReturn_pct']:.4f} | {a['h1_control_metrics']['DailyMaxDrawdown_pct']:.4f} |\n"
        Path(path).write_text(text)
    base.formation_model.MODEL=candidate.MODEL
    base.formation_model.select_targets=selector
    base.audit_targets=validator; base.FILES=base.FILES+EXTRA_FILES; base.render_report=report
    base.ResearchLedger=candidate.DiversifiedLedger; base.scan_holding_inputs=scan
    try:
        yield
    finally:
        (base.formation_model.MODEL,base.formation_model.select_targets,
         base.audit_targets,base.FILES,base.render_report,base.ResearchLedger,base.scan_holding_inputs)=saved_bindings


def run(args):
    args=copy.copy(args); args.formation=True
    with hypothesis(args.formation_dir,args.h1_dir):
        result=base.run(args)
        # Last report enriches the register with matched PR23 controls.
        base.atomic_json(Path(args.output_dir)/'attempts.json',result)
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache-dir','manifest','controls-dir','output-dir','normalized-dir','formation-dir','h1-dir'):
        p.add_argument('--'+n,required=True)
    args=p.parse_args()
    def blocked(*a,**kw): raise RuntimeError('Network forbidden in frozen portfolio-risk replay')
    socket.socket.connect=blocked; socket.create_connection=blocked
    run(args)
