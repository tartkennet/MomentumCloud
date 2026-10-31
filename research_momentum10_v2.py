"""Frozen, separate retention/frequency/close-stop experiment; no live orders."""
import math
import statistics
from dataclasses import dataclass, field

import momentum_core as core
from research_stocks10 import Stocks10Ledger, fee, select

MODEL = 'momentum10-retention-risk-v2'
PRIMARY = (('M1', 1, 'none'), ('M2', 2, 'none'), ('M3', 3, 'none'),
           ('Q10', 3, 'fixed10'), ('QV', 3, 'vol'))
PRIORITY = ('M3', 'Q10', 'QV', 'M2', 'M1', 'C')


def exposure(data, day, targets):
    columns = []
    for r in targets:
        c = core.adjusted_history(data, day, r['ticker'], 64)
        if len(c) != 64:
            raise core.DataBlocked('Risk budget history missing')
        columns.append([c[i] / c[i+1] - 1 for i in range(63)])
    returns = [statistics.fmean(x[i] for x in columns) for i in range(63)]
    sigma = statistics.stdev(returns) * math.sqrt(252)
    return min(1., .10 / sigma) if sigma > 0 else 1.


@dataclass
class RetentionLedger(Stocks10Ledger):
    interval: int = 1
    stop_mode: str = 'none'
    risk_budget: bool = False
    seen_month: str = ''
    references: dict = field(default_factory=dict)
    blacklist: list = field(default_factory=list)
    sell_queue: dict = field(default_factory=dict)
    stop_events: list = field(default_factory=list)
    decisions: list = field(default_factory=list)
    constraints: list = field(default_factory=list)

    def events_before_open(self, data, day):
        before = dict(self.shares)
        for e in data.splits:
            t = e['ticker']
            if e['execution_date'] == day and t in self.references:
                ratio = e['split_to'] / e['split_from']
                if t in before:
                    before[t] *= ratio
                for key in ('reference', 'level'):
                    self.references[t][key] /= ratio
        for e in data.dividends:
            t = e['ticker']
            if e['ex_dividend_date'] == day and t in self.references:
                self.references[t]['level'] -= e['cash_amount']
        super().events_before_open(data, day)
        for t, e in data.stock_actions.items():
            if e['effective_date'] != day or not before.get(t):
                continue
            successor = e['successor_ticker']
            ref = self.references.pop(t, None)
            if ref:
                old_successor_q = before.get(successor, 0)
                r = e['shares_per_share']
                converted = dict(ref, reference=(ref['reference'] - e.get('cash_per_share', 0))/r,
                                 level=(ref['level'] - e.get('cash_per_share', 0))/r)
                if old_successor_q and successor in self.references:
                    new_q = before[t] * r
                    for key in ('reference', 'level'):
                        converted[key] = (converted[key]*new_q+self.references[successor][key]*old_successor_q)/(new_q+old_successor_q)
                self.references[successor] = converted
            if t in self.sell_queue:
                self.sell_queue[successor] = self.sell_queue.pop(t)
        for t in list(self.references):
            if t not in self.shares:
                self.references.pop(t)
        for e in getattr(data, 'distributions', []):
            t = e['recipient']
            if e['ex_date'] == day and self.shares.get(t, 0) >= 1 and t not in self.references and self.stop_mode != 'none':
                self.constraints.append({'date': day, 'ticker': t, 'reason': 'UNRESOLVED_SPINOFF_STOP_BASIS'})

    def _trade(self, day, signal, t, side, q, price, config, reason, **extra):
        if not q:
            return
        charge = fee(q * price, config.one_way_cost)
        self.cash += q*price-charge if side == 'SELL' else -q*price-charge
        self.shares[t] = self.shares.get(t, 0) + (q if side == 'BUY' else -q)
        if abs(self.shares[t]) < 1e-9:
            self.shares.pop(t)
            self.references.pop(t, None)
        self.fees += charge
        self.trades.append(dict(date=day, signal_date=signal, ticker=t, side=side, quantity=q,
                                price=price, fee=charge, reason=reason, **extra))

    def execute_open(self, data, day, config=core.CONFIG):
        bars = data.bars(day)
        for t, order in sorted(list(self.sell_queue.items())):
            if day <= order['signal_date']:
                raise ValueError('A close decision cannot fill at its own open')
            q = math.floor(self.shares.get(t, 0) + 1e-9)
            if not q:
                self.sell_queue.pop(t)
                continue
            opening = core.number(bars[t][0]) if bars.get(t) else None
            if opening is None:
                self.blocked.append({'date': day, 'ticker': t, 'reason': 'MISSING_QUEUED_SELL_OPEN'})
                continue
            ref = dict(self.references.get(t, {}))
            self._trade(day, order['signal_date'], t, 'SELL', q, opening, config, order['reason'],
                        stop_level=ref.get('level'), entry_reference=ref.get('reference'))
            self.sell_queue.pop(t)
        if self.pending is None:
            return
        p = self.pending
        if p['signal_date'] >= day:
            raise ValueError('A basket must follow its close decision')
        targets = {r['ticker']: r for r in p['targets'] if r['ticker'] not in p.get('suppressed', [])}
        names = set(targets)
        changed = any(e['effective_date'] == day and t in names
                      for actions in (data.cash_actions, data.stock_actions) for t, e in actions.items())
        missing = [t for t in names | self.shares.keys() if not bars.get(t) or core.number(bars[t][0]) is None]
        if changed or missing:
            self.blocked.append({'date': day, 'reason': 'BASKET_EVENT_OR_MISSING_OPEN', 'tickers': missing})
            self.pending = None
            return
        prices = {t: bars[t][0] for t in names | self.shares.keys()}
        retained = {t for t in names if self.shares.get(t, 0) >= 1}
        plan = dict(self.shares)
        sales = {}
        for t, q in self.shares.items():
            wanted = q if t in retained else q - math.floor(q + 1e-9)
            if self.risk_budget and t in retained:
                wanted = min(q, max(1, math.floor(p['signal_nav']*p['exposure']/10/prices[t])))
            selling = math.floor(max(0, q-wanted) + 1e-9)
            if selling:
                sales[t] = selling
                plan[t] = q-selling
        cash = self.cash + sum(q*prices[t]-fee(q*prices[t],config.one_way_cost) for t,q in sales.items())
        new = names-retained
        budget = cash
        if self.risk_budget or p.get('suppressed'):
            budget = min(cash, max(0, p['signal_nav']*p['exposure']*len(names)/10 - sum(plan.get(t,0)*prices[t] for t in retained)))
        minimum = sum(prices[t]+fee(prices[t],config.one_way_cost) for t in new)
        if minimum > budget + 1e-7:
            self.blocked.append({'date': day, 'reason': 'MINIMUM_COMPLETE_BASKET_UNFUNDED', 'minimum': minimum, 'budget': budget})
            self.pending = None
            return
        quantities = {t: max(1, math.floor(budget/len(new)/prices[t])) for t in new}
        def requested():
            return sum(q*prices[t]+fee(q*prices[t],config.one_way_cost) for t,q in quantities.items())
        while requested() > budget + 1e-7:
            adjustable = [t for t,q in quantities.items() if q > 1]
            if not adjustable:
                raise core.DataBlocked('Minimum-lot precheck contradicted allocation')
            t = max(adjustable, key=lambda t: (quantities[t]*prices[t],t))
            quantities[t] -= 1
        for t,q in sorted(sales.items()):
            self._trade(day,p['signal_date'],t,'SELL',q,prices[t],config,'RISK_BUDGET' if t in retained else 'MEMBERSHIP_EXIT')
        for t,q in sorted(quantities.items()):
            old_q, old_ref = self.shares.get(t,0), self.references.get(t)
            self._trade(day,p['signal_date'],t,'BUY',q,prices[t],config,'MEMBERSHIP_ENTRY')
            distance = .10 if self.stop_mode == 'fixed10' else 2*targets[t]['daily_volatility']*math.sqrt(21)
            self.references[t] = {'reference': prices[t], 'level': prices[t]*max(0,1-distance),
                                  'distance': distance, 'basis_signal': p['signal_date']}
            if old_q and old_ref:
                for key in ('reference','level'):
                    self.references[t][key] = (old_q*old_ref[key]+q*self.references[t][key])/(old_q+q)
            if self.stop_mode != 'none' and distance >= 1:
                self.constraints.append({'date': day,'ticker':t,'reason':'INEFFECTIVE_NONPOSITIVE_STOP'})
        if self.cash < -1e-6:
            raise AssertionError('Borrowed cash')
        self.pending = None

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
            from research_stocks10 import population
            rows = [r for r in population(data,day,memo) if r['ticker'] not in locked
                    and r['raw_price']+fee(r['raw_price'],config.one_way_cost) <= nav/10
                    and r['return_1m']>0 and r['return_3m']>0]
            chosen = rows[:10] if len(rows)>=10 else []
            for r in chosen:
                r['weight'] = .1
            scale = exposure(data,day,chosen) if self.risk_budget and chosen else 1.
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
