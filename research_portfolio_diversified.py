"""H2: equal risk between a broad SPY core and the unchanged momentum basket."""
import copy
import math
import statistics
from dataclasses import dataclass

from momentum_core import CONFIG, DataBlocked
from research_core_formation import select_targets as formation_targets
from research_core_ledger import ResearchLedger
from research_portfolio_risk import price_returns

MODEL='momentum-diversified-core-research-v1'


def core_target(weight):
    return {'ticker':'SPY','weight':weight,'benchmark_core':True}


def risk_budget(data,day,targets,config=CONFIG):
    if not targets:
        return [core_target(1.)]
    rows=copy.deepcopy(targets)
    portfolio=[0.]*config.vol_returns
    for row in rows:
        for i,r in enumerate(price_returns(data,day,row['ticker'],config.vol_returns)):
            portfolio[i]+=row['weight']*r
    pvol=statistics.stdev(portfolio)
    svol=statistics.stdev(price_returns(data,day,'SPY',config.vol_returns))
    if not (pvol>0 and svol>0 and math.isfinite(pvol+svol)):
        raise DataBlocked('Invalid sleeve variance')
    stock_fraction=svol/(pvol+svol)
    for row in rows:
        row.update(weight=row['weight']*stock_fraction, momentum_sleeve_fraction=stock_fraction,
                   portfolio_vol63=pvol,benchmark_vol63=svol)
    rows.append(core_target(1-stock_fraction))
    return rows


def select_targets(data,day,config=CONFIG,*,saved_signal=None):
    if saved_signal is None:
        rows,count=formation_targets(data,day,config)
    else:
        assert saved_signal['date']==day and saved_signal['risk_on']
        rows,count=saved_signal['targets'],saved_signal['eligible_count']
    return risk_budget(data,day,rows,config),count


@dataclass
class DiversifiedLedger(ResearchLedger):
    benchmark_core_weight: float=1.

    def step(self,data,day,config=CONFIG,*,benchmark=False):
        super().step(data,day,config,benchmark=benchmark)
        if benchmark or not self.targets or self.targets[-1]['date']!=day:
            return
        signal=self.targets[-1]
        if signal['risk_on']:
            core=[r for r in signal['targets'] if r.get('benchmark_core')]
            assert len(core)==1
            self.benchmark_core_weight=core[0]['weight']
        else:
            targets=[core_target(self.benchmark_core_weight)]
            signal['targets']=copy.deepcopy(targets)
            self.pending['targets']=targets
