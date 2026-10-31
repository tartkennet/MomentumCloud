"""Separate preregistered v3 selection; frozen v2 execution inherited unchanged."""
import copy
import math
import statistics
from dataclasses import dataclass

import momentum_core as core
from research_stocks10 import fee
from research_momentum10_v2 import RetentionLedger

MODEL = 'momentum10-current-trend-clusters-v3'


def population(data, day, memo, stage):
    key = (day, stage)
    if key not in memo:
        rows=[]
        records={r.get('ticker'):r for r in data.universe(day) if core.eligible(r)}
        for t in sorted(records):
            history=data.history(day,t,253)
            if len(history)!=253 or any(not b for _,b in history):continue
            price=core.number(history[0][1][1])
            dollars=[core.number(b[1])*core.number(b[2],positive=False) for _,b in history[:20]
                     if core.number(b[1]) is not None and core.number(b[2],positive=False) is not None]
            if price is None or price<10 or len(dollars)!=20 or statistics.fmean(dollars)<5_000_000:continue
            c=core.adjusted_history(data,day,t,253)
            if len(c)!=253:continue
            x=[c[i]/c[i+1]-1 for i in range(126)]
            vol=statistics.stdev(x);recent=statistics.stdev(x[:63]);momentum=c[0]/c[126]-1
            r1=c[0]/c[21]-1;r3=c[0]/c[63]-1;sma=statistics.fmean(c[:63])
            if not (vol>0 and recent>0 and momentum>0 and r1>0 and r3>0):continue
            if stage!='R' and c[0]<=sma:continue
            rows.append(dict(ticker=t,raw_price=price,adv20_usd=statistics.fmean(dollars),
                daily_volatility=recent,momentum_6m=momentum,score_volatility=vol,
                risk_normalized_score=momentum/vol,return_1m=r1,return_3m=r3,sma63=sma,
                company_name=records[t].get('name',''),_returns=x[:63]))
        rows.sort(key=lambda r:(-r['risk_normalized_score'],r['ticker']))
        memo[key]=rows
    return copy.deepcopy(memo[key])


def choose(rows, stage):
    accepted=[]
    for row in rows:
        if stage=='D':
            trial=accepted+[row];groups=[{i} for i in range(len(trial))]
            for i in range(len(trial)):
                for j in range(i):
                    if statistics.correlation(trial[i]['_returns'],trial[j]['_returns'])>=.70:
                        a=next(g for g in groups if i in g);b=next(g for g in groups if j in g)
                        if a is not b:a.update(b);groups.remove(b)
            if max(map(len,groups))>2:continue
        accepted.append(row)
        if len(accepted)==10:break
    return [{k:v for k,v in r.items() if k!='_returns'} for r in accepted] if len(accepted)==10 else []


@dataclass
class SelectionLedger(RetentionLedger):
    stage: str = 'R'

    def step_stocks(self, data, day, config, memo):
        if self.last_date and day <= self.last_date:
            raise ValueError('Sessions must increase')
        self.events_before_open(data,day)
        self.execute_open(data,day,config)
        nav, stock, claims = self.close_value(data,day)
        if len(self.shares)>10 or any(0<q<1-1e-9 for q in self.shares.values()):
            self.constraints.append({'date':day,'reason':'EXTRA_OR_SUBWHOLE_EQUITY_ENTITLEMENT',
                                      'quantities':dict(self.shares)})
        self.equity.append(dict(date=day,nav=nav,cash=self.cash,receivables=claims,stock_value=stock,
                                positions=len(self.shares),fees_cumulative=self.fees))
        month = day[:7]
        ordinary = month != self.seen_month and (int(day[5:7])-1)%self.interval == 0
        if ordinary:
            self.blacklist = []
        locked = list(self.blacklist)
        allowed = core.risk_on(data,day)
        triggered = []
        if allowed and self.stop_mode != 'none':
            for t,q in sorted(self.shares.items()):
                bar = data.bars(day).get(t)
                ref = self.references.get(t)
                if q >= 1 and ref and bar and bar[1] <= ref['level']:
                    triggered.append(t)
                    self.stop_events.append(dict(date=day,ticker=t,close=bar[1],**ref))
                    self.sell_queue.setdefault(t,{'signal_date':day,'reason':'STOP_'+self.stop_mode})
        if allowed and (ordinary or not self.previous_risk):
            # Locked names affect eligibility; freshly triggered same-close
            # stops become temporary CASH slots rather than replacements.
            rows = [r for r in population(data,day,memo,self.stage) if r['ticker'] not in locked
                    and r['raw_price']+fee(r['raw_price'],config.one_way_cost) <= nav/10
                    and r['return_1m']>0 and r['return_3m']>0]
            chosen = choose(rows,self.stage)
            for r in chosen:
                r['weight'] = .1
            scale = 1.
            signal = dict(date=day,risk_on=True,targets=chosen,signal_nav=nav,fresh=True,
                eligible_count=len(rows),ordinary=ordinary,exposure=scale,suppressed=triggered,
                blacklist=locked)
            self.targets.append(signal)
            if chosen:
                self.pending = dict(signal_date=day,targets=chosen,signal_nav=nav,exposure=scale,suppressed=triggered)
            else:
                self.blocked.append({'date':day,'reason':'FEWER_THAN_TEN_ELIGIBLE'})
        elif not allowed:
            if self.previous_risk or not self.last_date:
                self.targets.append(dict(date=day,risk_on=False,targets=[]))
            for t,q in self.shares.items():
                if q >= 1:
                    self.sell_queue[t] = self.sell_queue.get(t,{'signal_date':day,'reason':'RISK_OFF'})
        self.blacklist = sorted(set(self.blacklist)|set(triggered))
        self.decisions.append(dict(date=day,risk_on=allowed,ordinary=ordinary,stops=triggered,blacklist=self.blacklist[:]))
        self.seen_month,self.previous_risk,self.last_date = month,allowed,day
