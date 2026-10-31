"""Separate whole-lot stocks-only study. Never imported by H3 or Buy Now."""
import copy
import math
from dataclasses import dataclass, field, replace

import momentum_core as core
from research_core_formation import select_targets as formation_population
from research_core_ledger import ResearchLedger

MODEL = 'stocks10-whole-lots-v1'

# This newly held name was absent from the old H3 selections. The missing
# close is a verified cash merger, never a made-up quote. No payment date is
# asserted; locked and all prespecified payment sensitivities are retained.
APGE_COMPLETION = {'effective_date': '2026-09-03', 'cash_per_share': 135.11,
    'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-607',
    'sec_url': 'https://www.sec.gov/Archives/edgar/data/1974640/000114036126035537/ef20081397_8k.htm'}


def fee(notional, execution=.0015):
    return max(1., notional * .0025) + notional * (.0025 + execution) if notional else 0.


def population(data, day, memo):
    if day not in memo:
        rows, _ = formation_population(data, day, replace(core.CONFIG, positions=100000))
        for row in rows:
            closes = core.adjusted_history(data, day, row['ticker'], 64)
            row['return_1m'] = closes[0] / closes[21] - 1
            row['return_3m'] = closes[0] / closes[63] - 1
        memo[day] = rows
    return copy.deepcopy(memo[day])


def select(data, day, nav, fresh, execution, memo):
    rows = [r for r in population(data, day, memo)
            if r['raw_price'] + fee(r['raw_price'], execution) <= nav / 10
            and (not fresh or (r['return_1m'] > 0 and r['return_3m'] > 0))]
    chosen = rows[:10]
    if len(chosen) != 10:
        return [], len(rows)
    for r in chosen:
        r['weight'] = .1
    return chosen, len(rows)


@dataclass
class Stocks10Ledger(ResearchLedger):
    fresh: bool = False
    benchmark_account: bool = False
    blocked: list = field(default_factory=list)

    def execute_open(self, data, day, config=core.CONFIG):
        if self.pending is None:
            return
        signal = self.pending['signal_date']
        if signal >= day:
            raise ValueError('A signal must precede its fill')
        bars = data.bars(day)
        targets = self.pending['targets']
        names = [r['ticker'] for r in targets]
        # Corporate actions between close and open invalidate this exact basket;
        # the inherited event book still handles existing entitlements.
        bad_event = any(e['effective_date'] == day and t in names
                        for actions in (data.cash_actions, data.stock_actions)
                        for t, e in actions.items())
        missing = [t for t in set(names) | set(self.shares) if not bars.get(t) or core.number(bars[t][0]) is None]
        slots = 1 if self.benchmark_account else 10
        if bad_event or missing or (targets and len(set(names)) != slots):
            self.blocked.append({'date': day, 'signal_date': signal, 'reason': 'EVENT_OR_MISSING_OPEN', 'tickers': missing})
            self.pending = None
            return
        openings = {t: bars[t][0] for t in set(names) | set(self.shares)}
        desired = {t: max(1, math.floor(self.pending['signal_nav'] / slots / openings[t])) for t in names}

        def cash_after(plan):
            result = self.cash
            for t in set(plan) | set(self.shares):
                current = self.shares.get(t, 0)
                # Fractional corporate entitlements are retained, never traded.
                selling = math.floor(max(0, current - plan.get(t, 0)) + 1e-9)
                buying = max(0, math.ceil(plan.get(t, 0) - current - 1e-9))
                if selling:
                    value = selling * openings[t]
                    result += value - fee(value, config.one_way_cost)
                if buying:
                    value = buying * openings[t]
                    result -= value + fee(value, config.one_way_cost)
            return result

        minimum = {t: 1 for t in names}
        if targets and cash_after(minimum) < -1e-7:
            self.blocked.append({'date': day, 'signal_date': signal, 'reason': 'TEN_MINIMUM_LOTS_UNAFFORDABLE'})
            self.pending = None
            return
        # Deterministic, no ticker-priority cash drain: reduce the most
        # overweight target by one share until the complete basket is funded.
        while cash_after(desired) < -1e-7:
            reducible = [t for t in names if desired[t] > 1]
            if not reducible:
                raise core.DataBlocked('Cannot fund prechecked minimum basket')
            t = max(reducible, key=lambda t: (desired[t] * openings[t], t))
            desired[t] -= 1
        for side in ('SELL', 'BUY'):
            for t in sorted(set(desired) | set(self.shares)):
                current = self.shares.get(t, 0)
                q = (math.floor(max(0, current - desired.get(t, 0)) + 1e-9) if side == 'SELL'
                     else max(0, math.ceil(desired.get(t, 0) - current - 1e-9)))
                if not q:
                    continue
                value = q * openings[t]
                charge = fee(value, config.one_way_cost)
                self.cash += value - charge if side == 'SELL' else -value - charge
                self.shares[t] = current + (q if side == 'BUY' else -q)
                if abs(self.shares[t]) < 1e-9:
                    del self.shares[t]
                self.fees += charge
                self.trades.append({'date': day, 'signal_date': signal, 'ticker': t, 'side': side,
                                    'quantity': q, 'price': openings[t], 'fee': charge})
        if self.cash < -1e-6:
            raise AssertionError('Unfunded whole-lot basket')
        self.pending = None

    def step_stocks(self, data, day, config, memo):
        if self.last_date and day <= self.last_date:
            raise ValueError('Sessions must increase')
        self.events_before_open(data, day)
        self.execute_open(data, day, config)
        nav, stock, claims = self.close_value(data, day)
        self.equity.append({'date': day, 'nav': nav, 'cash': self.cash, 'receivables': claims,
                            'stock_value': stock, 'positions': len(self.shares), 'fees_cumulative': self.fees})
        allowed = core.risk_on(data, day)
        if allowed and (self.selection_month != day[:7] or not self.previous_risk):
            targets, count = select(data, day, nav, self.fresh, config.one_way_cost, memo)
            signal = {'date': day, 'risk_on': True, 'eligible_count': count,
                      'signal_nav': nav, 'targets': targets, 'fresh': self.fresh}
            self.targets.append(signal)
            if targets:
                self.pending = {'signal_date': day, 'signal_nav': nav, 'targets': targets}
            else:
                self.blocked.append({'date': day, 'reason': 'FEWER_THAN_TEN_ELIGIBLE_STOCKS'})
            self.selection_month = day[:7]
        elif not allowed and (self.previous_risk or not self.last_date):
            self.pending = {'signal_date': day, 'signal_nav': nav, 'targets': []}
            self.targets.append({'date': day, 'risk_on': False, 'targets': []})
        self.previous_risk = allowed
        self.last_date = day
