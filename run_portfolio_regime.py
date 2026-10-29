"""Replay the frozen portfolio-wide regime H3 hypothesis, reusing audited base selections."""
import argparse
import copy
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import run_core_normalized_research as base
import research_portfolio_regime as candidate
from audit_portfolio_regime import audit_targets

EXTRA_FILES=('research_portfolio_risk.py','audit_portfolio_risk.py','run_portfolio_risk_research.py',
             'tests/test_portfolio_risk.py','docs/CORE_PORTFOLIO_RISK_H1_20261029.md',
             'research_portfolio_diversified.py','audit_portfolio_diversified.py','run_portfolio_diversified.py',
             'tests/test_portfolio_diversified.py','docs/CORE_PORTFOLIO_RISK_H2_20261029.md',
             'research_portfolio_regime.py','audit_portfolio_regime.py','run_portfolio_regime.py',
             'tests/test_portfolio_regime.py','docs/CORE_PORTFOLIO_RISK_H3_20261029.md')


@contextmanager
def hypothesis(reference,h1_reference,h2_reference):
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
    h2=json.loads((Path(h2_reference)/'attempts.json').read_text())
    h2_verified=json.loads((base.ROOT/'docs/CORE_PORTFOLIO_H2_RESULTS_20261029.json').read_text())
    assert h2['all_attempts_completed'] and len(h2['attempts'])==40
    h2_cases={(a['phase'],a['name']):a for a in h2['attempts']}
    for a in h2_verified['attempts']:
        m=h2_cases[a['phase'],a['name']]
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
            a['h2_control_metrics']=h2_cases[a['phase'],a['name']]['metrics']
            a['h2_control_gates']=h2_cases[a['phase'],a['name']]['gates']
            a['h2_control_diagnostics']=h2_cases[a['phase'],a['name']]['diagnostics']
        register['hypothesis']='H3 diversified equal-risk portfolio with existing global risk-off'
        register['formation_controls_reused_without_replay']=40
        saved_bindings[4](register,path)
        text=Path(path).read_text()
        text+='\n## Completed PR23 comparator, identical assumptions\n\n| Phase | Policy/mark | Cost bp | PR23 net % | PR23 DD % | New net % | New DD % | H1 net % | H1 DD % | H2 net % | H2 DD % |\n|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n'
        for a in register['attempts']:
            if a['status']=='COMPLETE':
                m,b=a['metrics'],a['formation_control_metrics']
                text+=f"| {a['phase']} | {a['policy']}/{a['halt_mark_policy']} | {a['cost']*10000:.0f} | {b['TotalReturn_pct']:.4f} | {b['DailyMaxDrawdown_pct']:.4f} | {m['TotalReturn_pct']:.4f} | {m['DailyMaxDrawdown_pct']:.4f} | {a['h1_control_metrics']['TotalReturn_pct']:.4f} | {a['h1_control_metrics']['DailyMaxDrawdown_pct']:.4f} | {a['h2_control_metrics']['TotalReturn_pct']:.4f} | {a['h2_control_metrics']['DailyMaxDrawdown_pct']:.4f} |\n"
        Path(path).write_text(text)
    base.formation_model.MODEL=candidate.MODEL
    base.formation_model.select_targets=selector
    base.audit_targets=validator; base.FILES=base.FILES+EXTRA_FILES; base.render_report=report
    base.ResearchLedger=candidate.PortfolioLedger
    try:
        yield
    finally:
        (base.formation_model.MODEL,base.formation_model.select_targets,
         base.audit_targets,base.FILES,base.render_report,base.ResearchLedger,base.scan_holding_inputs)=saved_bindings


def run(args):
    args=copy.copy(args); args.formation=True
    with hypothesis(args.formation_dir,args.h1_dir,args.h2_dir):
        result=base.run(args)
        # Last report enriches the register with matched PR23 controls.
        base.atomic_json(Path(args.output_dir)/'attempts.json',result)
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache-dir','manifest','controls-dir','output-dir','normalized-dir','formation-dir','h1-dir','h2-dir'):
        p.add_argument('--'+n,required=True)
    args=p.parse_args()
    def blocked(*a,**kw): raise RuntimeError('Network forbidden in frozen portfolio-risk replay')
    socket.socket.connect=blocked; socket.create_connection=blocked
    run(args)
