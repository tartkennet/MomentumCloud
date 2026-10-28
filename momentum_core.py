"""Frozen Core v1 rules and the shared historical/paper execution ledger.

No network, file I/O, current constituents, parameter search or live orders.
Bars are RAW (open, close, volume); dates are ISO and strictly increasing.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import asdict, dataclass, field
from typing import Protocol


MODEL = "momentum-core-v1"


class DataBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class CoreConfig:
    model: str = MODEL
    positions: int = 15
    min_price: float = 10.0
    min_adv: float = 5_000_000.0
    vol_returns: int = 63
    max_weight: float = 0.10
    one_way_cost: float = 0.0015
    initial_cash: float = 100_000.0


CONFIG = CoreConfig()


class MarketData(Protocol):
    splits: list[dict]
    dividends: list[dict]
    cash_actions: dict[str, dict]
    stock_actions: dict[str, dict]

    def bars(self, day: str) -> dict: ...
    def history(self, day: str, ticker: str, count: int) -> list: ...
    def universe(self, day: str) -> list[dict]: ...


def number(value, *, positive=True):
    try:
        value = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(value) or (value <= 0 if positive else value < 0):
        return None
    return value


def eligible(record):
    name = str(record.get("name", "")).upper()
    return bool(
        record.get("active") is True
        and record.get("type") == "CS"
        and record.get("primary_exchange") in ("XNAS", "XNYS", "XASE")
        and record.get("ticker")
        and not any(x in name for x in ("ACQUISITION", "BLANK CHECK", " SPAC"))
    )


def adjusted_history(data: MarketData, day, ticker, count):
    """Newest first. Only split events effective by this signal are observable."""
    rows = data.history(day, ticker, count)
    if len(rows) != count:
        return []
    if hasattr(data, "signal_splits"):
        source = data.signal_splits(day, ticker)
        events = [e for e in source if rows[-1][0] < e["execution_date"] <= day]
    else:
        source = getattr(data, "splits_by_ticker", {}).get(ticker, []) if hasattr(data, "splits_by_ticker") else data.splits
        events = [e for e in source if e.get("ticker") == ticker
                  and rows[-1][0] < e["execution_date"] <= day]
    result = []
    for stamp, bar in rows:
        close = number(bar[1]) if bar else None
        if close is None:
            return []
        factor = 1.0
        for event in events:
            if stamp < event["execution_date"]:
                before, after = number(event.get("split_from")), number(event.get("split_to"))
                if before is None or after is None:
                    raise DataBlocked(f"Invalid split {ticker} {event['execution_date']}")
                factor *= before / after
        result.append(close * factor)
    return result


def risk_on(data, day):
    closes = adjusted_history(data, day, "SPY", 200)
    if len(closes) != 200:
        raise DataBlocked(f"Missing SPY 200-session history at {day}")
    return closes[0] > statistics.fmean(closes)


def capped_weights(inverse_vols, cap, budget=1.0):
    """Water-fill remaining budget; never inflate a sleeve beyond the cap."""
    remaining = set(inverse_vols)
    weights = {key: 0.0 for key in sorted(remaining)}
    while remaining and budget > 1e-12:
        total = sum(inverse_vols[k] for k in sorted(remaining))
        proposed = {k: budget * inverse_vols[k] / total for k in sorted(remaining)}
        capped = {k for k in remaining if proposed[k] > cap}
        if not capped:
            weights.update(proposed)
            break
        for key in capped:
            weights[key] = cap
            budget -= cap
        remaining -= capped
    return weights


def select_targets(data, day, config=CONFIG):
    candidates = []
    records = {r.get("ticker"): r for r in data.universe(day) if eligible(r)}
    for ticker in sorted(records):
        history = data.history(day, ticker, 253)
        if len(history) != 253 or any(not row for _, row in history):
            continue
        raw_price = number(history[0][1][1])
        liquidity = [number(bar[1]) * number(bar[2], positive=False)
                     for _, bar in history[:20]
                     if number(bar[1]) is not None
                     and number(bar[2], positive=False) is not None]
        if raw_price is None or raw_price < config.min_price or len(liquidity) != 20:
            continue
        adv = statistics.fmean(liquidity)
        if adv < config.min_adv:
            continue
        closes = adjusted_history(data, day, ticker, 253)
        if not closes:
            continue
        momentum = closes[21] / closes[252] - 1.0
        returns = [closes[i] / closes[i + 1] - 1.0 for i in range(config.vol_returns)]
        volatility = statistics.stdev(returns)
        if momentum <= 0 or volatility <= 0 or not math.isfinite(volatility):
            continue
        candidates.append({"ticker": ticker, "momentum_12_2": momentum,
                           "daily_volatility": volatility, "raw_price": raw_price,
                           "adv20_usd": adv})
    candidates.sort(key=lambda item: (-item["momentum_12_2"], item["ticker"]))
    chosen = candidates[:config.positions]
    weights = capped_weights({r["ticker"]: 1 / r["daily_volatility"] for r in chosen},
                             config.max_weight, len(chosen) / config.positions)
    for row in chosen:
        row["weight"] = weights[row["ticker"]]
    return chosen, len(candidates)


@dataclass
class Ledger:
    cash: float = CONFIG.initial_cash
    shares: dict[str, float] = field(default_factory=dict)
    receivables: list[dict] = field(default_factory=list)
    pending: dict | None = None
    previous_risk: bool = False
    selection_month: str = ""
    last_date: str = ""
    trades: list[dict] = field(default_factory=list)
    targets: list[dict] = field(default_factory=list)
    equity: list[dict] = field(default_factory=list)
    fees: float = 0.0
    first_is_month_boundary: bool = False

    def _price(self, bars, ticker, index, day):
        bar = bars.get(ticker)
        price = number(bar[index]) if bar else None
        if price is None:
            raise DataBlocked(f"Missing {'open' if index == 0 else 'close'} {ticker} {day}")
        return price

    def _cash_claim(self, day, ticker, amount, pay_date, reason):
        if not math.isfinite(amount) or amount < 0:
            raise DataBlocked(f"Invalid cash claim {ticker} {day}")
        if pay_date and pay_date <= day:
            self.cash += amount
        else:
            self.receivables.append({"ticker": ticker, "amount": amount,
                                     "pay_date": pay_date, "reason": reason})

    def events_before_open(self, data, day):
        for event in data.splits:
            ticker = event.get("ticker")
            if event["execution_date"] == day and ticker in self.shares:
                before, after = number(event.get("split_from")), number(event.get("split_to"))
                if before is None or after is None:
                    raise DataBlocked(f"Invalid held split {ticker} {day}")
                self.shares[ticker] *= after / before
        # Split before dividend: ex-date cash_amount refers to that day's shares.
        for event in data.dividends:
            ticker = event.get("ticker")
            if event.get("ex_dividend_date") != day or ticker not in self.shares:
                continue
            amount = number(event.get("cash_amount"), positive=False)
            pay_date = event.get("pay_date")
            if event.get("currency", "").upper() != "USD" or amount is None or not pay_date:
                raise DataBlocked(f"Unresolved held dividend {ticker} {day}")
            if pay_date < day:
                raise DataBlocked(f"Dividend pay date precedes ex-date {ticker} {day}")
            self._cash_claim(day, ticker, amount * self.shares[ticker], pay_date, "DIVIDEND")
        paid = [r for r in self.receivables if r["pay_date"] and r["pay_date"] <= day]
        self.cash += sum(r["amount"] for r in paid)
        self.receivables = [r for r in self.receivables if r not in paid]
        for ticker, event in data.cash_actions.items():
            if event["effective_date"] == day and ticker in self.shares:
                qty = self.shares.pop(ticker)
                self._cash_claim(day, ticker, qty * event["cash_per_share"],
                                 event.get("pay_date"), "CASH_MERGER")
                if event.get("contingent_cash_per_share", 0) > 0:
                    # Preserve the contractual right without inventing its
                    # market value, milestone achievement or cash payment.
                    self.receivables.append({"ticker": ticker, "amount": 0.0,
                        "pay_date": None, "reason": "CONTINGENT_VALUE_RIGHT_UNPRICED",
                        "maximum_amount": qty * event["contingent_cash_per_share"]})
                self.trades.append({"date": day, "ticker": ticker, "side": "CASH_MERGER_CLAIM",
                                    "quantity": qty, "price": event["cash_per_share"], "fee": 0.0})
        for ticker, event in data.stock_actions.items():
            if event["effective_date"] == day and ticker in self.shares:
                qty = self.shares.pop(ticker) * event["shares_per_share"]
                successor = event["successor_ticker"]
                self.shares[successor] = self.shares.get(successor, 0.0) + qty

    def execute_open(self, data, day, config=CONFIG):
        if self.pending is None:
            return
        if day <= self.pending["signal_date"]:
            raise ValueError("Orders must execute after their signal date")
        bars = data.bars(day)
        desired = {}
        for row in self.pending["targets"]:
            ticker = row["ticker"]
            cash_event = data.cash_actions.get(ticker)
            if cash_event and self.pending["signal_date"] <= cash_event["effective_date"] <= day:
                continue
            stock_event = data.stock_actions.get(ticker)
            if stock_event and self.pending["signal_date"] <= stock_event["effective_date"] <= day:
                ticker = stock_event["successor_ticker"]
            bar = bars.get(ticker)
            opening = number(bar[0]) if bar else None
            if opening is None:
                if ticker in self.shares:
                    raise DataBlocked(f"Missing target/held open {ticker} {day}")
                self.trades.append({"date": day, "ticker": ticker, "side": "BUY_CANCELLED_NO_OPEN",
                                    "quantity": 0, "price": None, "fee": 0.0})
                continue
            budget = self.pending["signal_nav"] * row["weight"]
            desired[ticker] = desired.get(ticker, 0) + math.floor(budget / opening)
        # Sell before buys; don't manufacture a price for a missing sale.
        for ticker, current in sorted(list(self.shares.items())):
            quantity = math.floor(max(0, current - desired.get(ticker, 0)) + 1e-9)
            if quantity:
                price = self._price(bars, ticker, 0, day)
                notional = quantity * price
                fee = notional * config.one_way_cost
                self.cash += notional - fee
                self.shares[ticker] -= quantity
                if abs(self.shares[ticker]) < 1e-9:
                    del self.shares[ticker]
                self.fees += fee
                self.trades.append({"date": day, "signal_date": self.pending["signal_date"],
                                    "ticker": ticker, "side": "SELL", "quantity": quantity,
                                    "price": price, "fee": fee})
        buys = {t: max(0, math.floor(q - self.shares.get(t, 0) + 1e-9))
                for t, q in desired.items()}
        requested = sum(q * self._price(bars, t, 0, day) * (1 + config.one_way_cost)
                        for t, q in buys.items() if q)
        scale = min(1.0, max(0.0, self.cash) / requested) if requested else 0.0
        # Scale all orders before rounding, avoiding arbitrary ticker priority.
        for ticker, wanted in sorted(buys.items()):
            qty = math.floor(wanted * scale + 1e-10)
            if not qty:
                continue
            price = self._price(bars, ticker, 0, day)
            fee = qty * price * config.one_way_cost
            self.cash -= qty * price + fee
            self.shares[ticker] = self.shares.get(ticker, 0.0) + qty
            self.fees += fee
            self.trades.append({"date": day, "signal_date": self.pending["signal_date"],
                                "ticker": ticker, "side": "BUY", "quantity": qty,
                                "price": price, "fee": fee})
        if self.cash < -1e-6:
            raise AssertionError("Cash ledger borrowed capital")
        self.pending = None

    def close_value(self, data, day):
        bars = data.bars(day)
        stock = sum(q * self._price(bars, ticker, 1, day) for ticker, q in self.shares.items())
        claims = sum(r["amount"] for r in self.receivables)
        return self.cash + stock + claims, stock, claims

    def step(self, data, day, config=CONFIG, *, benchmark=False):
        if self.last_date and day <= self.last_date:
            raise ValueError("Sessions must be strictly increasing")
        self.events_before_open(data, day)
        self.execute_open(data, day, config)
        nav, stock, claims = self.close_value(data, day)
        self.equity.append({"date": day, "nav": nav, "cash": self.cash,
                            "receivables": claims, "stock_value": stock,
                            "positions": len(self.shares), "fees_cumulative": self.fees})
        if benchmark:
            if not self.last_date:
                self.pending = {"signal_date": day, "signal_nav": nav,
                                "targets": [{"ticker": "SPY", "weight": 1.0}]}
        else:
            allowed = risk_on(data, day)
            monthly = self.selection_month != day[:7]
            if allowed and (monthly or not self.previous_risk):
                targets, eligible_count = select_targets(data, day, config)
                self.pending = {"signal_date": day, "signal_nav": nav, "targets": targets}
                self.targets.append({"date": day, "risk_on": True,
                                     "eligible_count": eligible_count, "targets": targets})
                self.selection_month = day[:7]
            elif not allowed and (self.previous_risk or not self.last_date):
                self.pending = {"signal_date": day, "signal_nav": nav, "targets": []}
                self.targets.append({"date": day, "risk_on": False,
                                     "eligible_count": 0, "targets": []})
            self.previous_risk = allowed
        self.last_date = day

    def to_dict(self):
        return asdict(self)


def metrics(ledger, benchmark):
    if not ledger.equity or len(benchmark.equity) != len(ledger.equity):
        raise DataBlocked("Not enough aligned strategy/benchmark sessions")
    initial = ledger.equity[0]["nav"]
    total = 100 * (ledger.equity[-1]["nav"] / initial - 1)
    spy = 100 * (benchmark.equity[-1]["nav"] / benchmark.equity[0]["nav"] - 1)
    peak = initial
    drawdown = 0.0
    for row in ledger.equity:
        peak = max(peak, row["nav"])
        drawdown = min(drawdown, 100 * (row["nav"] / peak - 1))
    # Complete intervals between first session closes; no partial terminal month.
    boundaries = []
    for i, row in enumerate(ledger.equity):
        if i and row["date"][:7] != ledger.equity[i - 1]["date"][:7]:
            boundaries.append(row)
    # The first replay date may be mid-month. Include it only when the caller
    # establishes that it was the calendar's first trading session.
    if getattr(ledger, "first_is_month_boundary", False):
        boundaries.insert(0, ledger.equity[0])
    periods = [{"start": a["date"], "end": b["date"],
                "net_return_pct": 100 * (b["nav"] / a["nav"] - 1)}
               for a, b in zip(boundaries, boundaries[1:])]
    hit = 100 * sum(r["net_return_pct"] > 0 for r in periods) / len(periods) if periods else 0.0
    result = {"Periods": len(periods), "TotalReturn_pct": total,
              "SPYTotalReturn_pct": spy, "TotalEdgeVsSPY_pct": total - spy,
              "DailyMaxDrawdown_pct": drawdown, "PeriodHitRate_pct": hit,
              "ActualFees_USD": ledger.fees, "FinalNAV_USD": ledger.equity[-1]["nav"]}
    return result, periods


def gates(result):
    specifications = [
        ("at_least_30_periods", "Periods", ">= 30", lambda x: x >= 30),
        ("positive_net_return", "TotalReturn_pct", "> 0", lambda x: x > 0),
        ("beats_spy", "TotalEdgeVsSPY_pct", "> 0", lambda x: x > 0),
        ("drawdown", "DailyMaxDrawdown_pct", ">= -20%", lambda x: x >= -20),
        ("hit_rate", "PeriodHitRate_pct", ">= 50%", lambda x: x >= 50),
    ]
    return [{"gate": name, "metric": key, "value": result.get(key), "requirement": rule,
             "pass": (isinstance(result.get(key), (int, float))
                      and math.isfinite(result[key]) and test(result[key]))}
            for name, key, rule, test in specifications]
