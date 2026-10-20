"""Install one price-unit conversion for audit exits and daily valuations.

The caller supplies verified paired factors. This module makes no network calls.
"""
from audit_corporate_action_basis import convert_stock_row
from datetime import datetime, timezone
import math


def install_compatible_action_prices(engine, paired_factor, observed_successors=None):
    execution_rows = {}
    for ticker, evidence in (observed_successors or {}).items():
        action = engine.STOCK_CORPORATE_ACTIONS[ticker]
        if any(evidence[key] != action[key] for key in ('effective_date', 'successor_ticker')):
            raise ValueError('Execution observations do not match the dated action')
        rows = {}
        raw = {bar['t']:bar for bar in evidence['bases']['false']['results']}
        for adjusted in evidence['bases']['true']['results']:
            original = raw.get(adjusted['t'])
            day = datetime.fromtimestamp(adjusted['t']/1000,timezone.utc).date().isoformat()
            if day < action['effective_date'] or original is None:
                raise ValueError('Missing paired or prematurely dated successor observation')
            for bar in (adjusted, original):
                if any(not math.isfinite(float(bar[key])) or float(bar[key]) <= 0 for key in ('o','h','l','c','v')):
                    raise ValueError('Successor observation requires positive finite OHLCV')
            rows[day] = {field:float(adjusted[key]) for field,key in
                         [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v')]}
        execution_rows[ticker] = (action, rows)

    def execution_view(cache, ticker, entry):
        if ticker not in execution_rows:
            return cache
        action, rows = execution_rows[ticker]
        if entry is not None and entry >= action['effective_date']:
            return cache
        # Copy only execution views. Never splice a short successor window
        # into the histories from which this or another stock is ranked.
        view = dict(cache)
        for day, row in rows.items():
            if day in cache:
                view[day] = {**cache[day], action['successor_ticker']:row}
        return view

    original_resolver = engine.resolve_exit_execution

    def compatible_exit(cache, days, ticker, target, entry, latest):
        cache = execution_view(cache, ticker, entry)
        resolved_day, row, action = original_resolver(cache, days, ticker, target, entry, latest)
        if not action or row is None:
            return resolved_day, row, action
        # Preserve legal closing dates on holidays, but value cash on an
        # available session within the permitted execution window.
        if action.get("reason") == "CASH_MERGER" and resolved_day not in days:
            available = [day for day in days if resolved_day <= day <= latest]
            if not available:
                return None, None, None
            resolved_day = min(available)
        effective = str(action["effective_date"])
        original_days = [day for day in days if entry <= day < effective
                         and engine.get_from_map(cache.get(day, {}), ticker)]
        if not original_days:
            raise RuntimeError(f"No original pre-action basis: {ticker} {effective}")
        original_factor = paired_factor(cache, ticker, max(original_days))
        successor = action.get("valuation_ticker")
        if successor:
            successor_effective = str(action.get('successor_effective_date', effective))
            successor_days = [day for day in days if successor_effective <= day <= resolved_day
                              and engine.get_from_map(cache.get(day, {}), successor)]
            if not successor_days:
                raise RuntimeError(f"No successor action basis: {successor} {effective}")
            successor_factor = paired_factor(cache, successor, min(successor_days))
            successor_row = engine.get_from_map(cache[resolved_day], successor)
            row = convert_stock_row(successor_row, action["shares_per_share"],
                                    action.get("cash_per_share", 0.0),
                                    original_factor, successor_factor)
        else:
            row = {field: float(value) * original_factor for field, value in row.items()}
        action = {**action, "original_adjustment_factor": original_factor,
                  "basis_validation": "PAIRED_RAW_ADJUSTED"}
        return resolved_day, row, action

    engine.resolve_exit_execution = compatible_exit

    original_close = engine.position_close_on_day

    def compatible_close(cache, ticker, day, entry=None):
        cache = execution_view(cache, ticker, entry)
        value_ticker, ratio, action = (engine.valuation_identity(ticker, day, entry)
                                       if entry is not None else engine.valuation_identity(ticker, day))
        if not action:
            return original_close(cache, ticker, day)
        row = engine.get_from_map(cache.get(day, {}), value_ticker)
        if not row:
            return None, action
        effective = str(action["effective_date"])
        original_days = [d for d in cache if d < effective
                         and engine.get_from_map(cache[d], ticker)]
        successor_effective = str(action.get('successor_effective_date', effective))
        successor_days = [d for d in cache if successor_effective <= d <= day
                          and engine.get_from_map(cache[d], value_ticker)]
        if not original_days or not successor_days:
            raise RuntimeError(f"No compatible daily action basis: {ticker} {day}")
        original_factor = paired_factor(cache, ticker, max(original_days))
        successor_factor = paired_factor(cache, value_ticker, min(successor_days))
        converted = convert_stock_row(row, ratio, action.get("cash_per_share", 0.0),
                                      original_factor, successor_factor)
        return float(converted["close"]), action

    engine.position_close_on_day = compatible_close

