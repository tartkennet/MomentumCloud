"""Compatible adjusted-price units for audit-only corporate-action valuations."""
import math


def adjustment_factor(adjusted_close, raw_close):
    values = (float(adjusted_close), float(raw_close))
    if any(not math.isfinite(v) or v <= 0 for v in values):
        raise RuntimeError("Invalid paired corporate-action basis prices")
    return values[0] / values[1]


def convert_stock_row(row, shares_per_share, cash_per_share, original_factor, successor_factor):
    if any(not math.isfinite(float(f)) or float(f) <= 0 for f in (original_factor, successor_factor)):
        raise RuntimeError("Unverified corporate-action adjustment basis")
    converted = dict(row)
    for field in ("open", "high", "low", "close"):
        if converted.get(field) is not None:
            converted[field] = (float(converted[field]) * float(shares_per_share)
                                * original_factor / successor_factor
                                + float(cash_per_share) * original_factor)
    return converted
