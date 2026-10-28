"""One fixed, research-only Core risk variant; no production approval changes."""
from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field

from momentum_core import CONFIG, DataBlocked, Ledger, number

MODEL = 'momentum-core-trailing-stop10-research-v1'
STOP_FRACTION = 0.10  # Existing v4 loss threshold; never searched over outcomes.


@dataclass
class TrailingLedger(Ledger):
    high_water: dict[str, float] = field(default_factory=dict)
    stop_pending: dict[str, dict] = field(default_factory=dict)
    stopped_month: dict[str, str] = field(default_factory=dict)
    stop_signals: list[dict] = field(default_factory=list)

    def events_before_open(self, data, day):
        # Transform the basis alongside the same verified security events.
        quantities = dict(self.shares)
        for event in data.splits:
            t = event.get('ticker')
            if event['execution_date'] == day and t in quantities:
                before, after = number(event.get('split_from')), number(event.get('split_to'))
                if before is None or after is None:
                    raise DataBlocked(f'Invalid stop-basis split {t} {day}')
                quantities[t] *= after / before
                if t not in self.high_water:
                    raise DataBlocked(f'Missing entry basis {t} {day}')
                self.high_water[t] *= before / after
        for t, event in data.cash_actions.items():
            if event['effective_date'] == day and t in quantities:
                quantities.pop(t)
                self.high_water.pop(t, None)
                self.stop_pending.pop(t, None)
        for t, event in data.stock_actions.items():
            if event['effective_date'] != day or t not in quantities:
                continue
            old_qty = quantities.pop(t)
            ratio, target = event['shares_per_share'], event['successor_ticker']
            if not number(ratio) or t not in self.high_water:
                raise DataBlocked(f'Unresolved stop-basis conversion {t} {day}')
            converted, old_basis = old_qty * ratio, self.high_water.pop(t)
            existing = quantities.get(target, 0)
            basis = self.high_water.get(target)
            if existing and basis is None:
                raise DataBlocked(f'Missing successor basis {target} {day}')
            self.high_water[target] = (old_qty * old_basis + existing * (basis or 0)) / (converted + existing)
            quantities[target] = existing + converted
            if t in self.stop_pending:
                signal = self.stop_pending.pop(t)
                if target in self.stop_pending:
                    signal = min((signal, self.stop_pending[target]), key=lambda x: x['signal_date'])
                self.stop_pending[target] = signal
            if t in self.stopped_month:
                self.stopped_month[target] = max(self.stopped_month.pop(t), self.stopped_month.get(target, ''))
        super().events_before_open(data, day)
        if self.shares != quantities:
            raise AssertionError('Basis/security event transformation differs from ledger')

    def execute_open(self, data, day, config=CONFIG):
        bars = data.bars(day)
        for ticker, signal in sorted(list(self.stop_pending.items())):
            if day <= signal['signal_date']:
                raise ValueError('Stop sale must follow its signal close')
            if ticker in self.shares:
                qty = math.floor(self.shares[ticker] + 1e-9)
                if qty:
                    price = self._price(bars, ticker, 0, day)
                    fee = qty * price * config.one_way_cost
                    self.cash += qty * price - fee
                    self.shares[ticker] -= qty
                    self.fees += fee
                    self.trades.append({'date': day, 'signal_date': signal['signal_date'],
                                        'ticker': ticker, 'side': 'SELL', 'quantity': qty,
                                        'price': price, 'fee': fee, 'reason': 'TRAILING_STOP10'})
                    if abs(self.shares[ticker]) < 1e-9:
                        del self.shares[ticker]
                        self.high_water.pop(ticker, None)
            del self.stop_pending[ticker]
        previous = dict(self.shares)
        first_trade = len(self.trades)
        super().execute_open(data, day, config)
        for trade in self.trades[first_trade:]:
            ticker, side = trade['ticker'], trade['side']
            if side == 'BUY':
                old = previous.get(ticker, 0)
                quantity = trade['quantity']
                basis = self.high_water.get(ticker)
                if old and basis is None:
                    raise DataBlocked(f'Missing buy high-water basis {ticker} {day}')
                self.high_water[ticker] = max(basis or trade['price'], trade['price'])
                previous[ticker] = old + quantity
            elif side == 'SELL':
                previous[ticker] -= trade['quantity']
                if ticker not in self.shares:
                    self.high_water.pop(ticker, None)

    def step(self, data, day, config=CONFIG, *, benchmark=False):
        if benchmark:
            raise ValueError('Use the unmodified Ledger for SPY')
        super().step(data, day, config)
        bars = data.bars(day)
        for ticker, qty in sorted(self.shares.items()):
            if math.floor(qty + 1e-9) == 0:
                continue
            basis = self.high_water.get(ticker)
            if basis is None or not number(basis):
                raise DataBlocked(f'Missing held entry basis {ticker} {day}')
            close = self._price(bars, ticker, 1, day)
            basis = max(basis, close)
            self.high_water[ticker] = basis
            if close <= basis * (1 - STOP_FRACTION):
                signal = {'signal_date': day, 'ticker': ticker, 'close': close,
                          'high_water': basis, 'threshold_fraction': STOP_FRACTION}
                self.stop_pending[ticker] = signal
                self.stop_signals.append(copy.deepcopy(signal))
                self.stopped_month[ticker] = day[:7]
        if self.pending:
            # Keep stopped sleeves cash. No hindsight replacements, no daily
            # rebalance of unrelated positions, and no same-month re-entry.
            self.pending['targets'] = [r for r in self.pending['targets']
                    if self.stopped_month.get(r['ticker']) != day[:7]]
            if self.targets and self.targets[-1]['date'] == day:
                self.targets[-1]['targets'] = copy.deepcopy(self.pending['targets'])
