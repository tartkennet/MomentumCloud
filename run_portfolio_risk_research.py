"""Replay one frozen portfolio-risk hypothesis, reusing audited base selections."""
import argparse
import copy
import json
import socket
from contextlib import contextmanager
from pathlib import Path

import run_core_normalized_research as base
import research_portfolio_risk as candidate
from audit_portfolio_risk import audit_targets

EXTRA_FILES=('research_portfolio_risk.py','audit_portfolio_risk.py','run_portfolio_risk_research.py',
             'tests/test_portfolio_risk.py','docs/CORE_PORTFOLIO_RISK_H1_20261029.md')


@contextmanager
def hypothesis(reference):
    root=Path(reference)
    saved=json.loads((root/'attempts.json').read_text())
    verified=json.loads((base.ROOT/'docs/CORE_FORMATION_RESULTS_20261029.json').read_text())
    assert saved['all_attempts_completed'] and len(saved['attempts'])==40
    cases={(a['phase'],a['name']):a for a in saved['attempts']}
    for a in verified['attempts']:
        match=cases[a['phase'],a['name']]
        assert match['metrics']==a['metrics'] and match['gates']==a['gates']
        assert match['selection_audit']['status']=='PASS' and match['accounting_audit']=='PASS'
    signals=json.loads((root/'holding_input_preflight.json').read_text())['all_signals']
    references={s['date']:s for s in signals}
    assert len(references)==len(signals)
    saved_bindings=(base.formation_model.MODEL,base.formation_model.select_targets,
                    base.audit_targets,base.FILES,base.render_report)
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
        register['hypothesis']='H1 benchmark-referenced aggregate risk budget'
        register['formation_controls_reused_without_replay']=40
        saved_bindings[4](register,path)
        text=Path(path).read_text()
        text+='\n## Completed PR23 comparator, identical assumptions\n\n| Phase | Policy/mark | Cost bp | PR23 net % | PR23 DD % | New net % | New DD % |\n|---|---|---:|---:|---:|---:|---:|\n'
        for a in register['attempts']:
            if a['status']=='COMPLETE':
                m,b=a['metrics'],a['formation_control_metrics']
                text+=f"| {a['phase']} | {a['policy']}/{a['halt_mark_policy']} | {a['cost']*10000:.0f} | {b['TotalReturn_pct']:.4f} | {b['DailyMaxDrawdown_pct']:.4f} | {m['TotalReturn_pct']:.4f} | {m['DailyMaxDrawdown_pct']:.4f} |\n"
        Path(path).write_text(text)
    base.formation_model.MODEL=candidate.MODEL
    base.formation_model.select_targets=selector
    base.audit_targets=validator; base.FILES=base.FILES+EXTRA_FILES; base.render_report=report
    try:
        yield
    finally:
        (base.formation_model.MODEL,base.formation_model.select_targets,
         base.audit_targets,base.FILES,base.render_report)=saved_bindings


def run(args):
    args=copy.copy(args); args.formation=True
    with hypothesis(args.formation_dir):
        result=base.run(args)
        # Last report enriches the register with matched PR23 controls.
        base.atomic_json(Path(args.output_dir)/'attempts.json',result)
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('cache-dir','manifest','controls-dir','output-dir','normalized-dir','formation-dir'):
        p.add_argument('--'+n,required=True)
    args=p.parse_args()
    def blocked(*a,**kw): raise RuntimeError('Network forbidden in frozen portfolio-risk replay')
    socket.socket.connect=blocked; socket.create_connection=blocked
    run(args)
