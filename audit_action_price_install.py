"""Install one price-unit conversion for audit exits and daily valuations.

The caller supplies verified paired factors. This module makes no network calls.
"""
from audit_corporate_action_basis import convert_stock_row


def install_compatible_action_prices(engine, paired_factor):
    original_resolver = engine.resolve_exit_execution

    def compatible_exit(cache, days, ticker, target, entry, latest):
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
            successor_days = [day for day in days if effective <= day <= resolved_day
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

    def compatible_close(cache, ticker, day):
        value_ticker, ratio, action = engine.valuation_identity(ticker, day)
        if not action:
            return original_close(cache, ticker, day)
        row = engine.get_from_map(cache.get(day, {}), value_ticker)
        if not row:
            return None, action
        effective = str(action["effective_date"])
        original_days = [d for d in cache if d < effective
                         and engine.get_from_map(cache[d], ticker)]
        successor_days = [d for d in cache if effective <= d <= day
                          and engine.get_from_map(cache[d], value_ticker)]
        if not original_days or not successor_days:
            raise RuntimeError(f"No compatible daily action basis: {ticker} {day}")
        original_factor = paired_factor(cache, ticker, max(original_days))
        successor_factor = paired_factor(cache, value_ticker, min(successor_days))
        converted = convert_stock_row(row, ratio, action.get("cash_per_share", 0.0),
                                      original_factor, successor_factor)
        return float(converted["close"]), action

    engine.position_close_on_day = compatible_close
