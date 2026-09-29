"""Verified corporate-action settlements for validation runs only.

Cash values are completed transaction consideration. No price is invented for
halted, unpriced or otherwise non-executable securities.
"""

CASH_SETTLEMENTS = {
    "MYOV": ("2023-03-10", 27.00),
    "AIMC": ("2023-03-27", 62.00),
    "APEN": ("2023-04-04", 10.00),
    "TA": ("2023-05-15", 86.00),
    "MAXR": ("2023-05-03", 53.00),
    "SUMO": ("2023-05-12", 12.05),
    "CVT": ("2023-06-15", 8.50),
    "XM": ("2023-06-28", 18.15),
    "DSEY": ("2023-07-05", 8.40),
    "THRN": ("2023-10-16", 10.20),
    "CHS": ("2024-01-05", 7.60),
    "MRTX": ("2024-01-23", 58.00),
    "KRTX": ("2024-03-18", 330.00),
    "PGTI": ("2024-03-28", 42.00),
    "EVBG": ("2024-07-02", 35.00),
    "ITI": ("2024-11-01", 7.20),
    "PLYA": ("2025-06-17", 13.50),
    "TGI": ("2025-07-24", 26.00),
    "VIGL": ("2025-08-06", 8.00),
    "SPTN": ("2025-09-22", 26.90),
    "BASE": ("2025-09-24", 24.50),
    "ZIMV": ("2025-10-20", 19.00),
    "ODP": ("2025-12-10", 28.00),
    "PKST": ("2026-05-06", 21.00),
    "EHAB": ("2026-05-15", 13.80),
    "AVNS": ("2026-07-27", 25.00),
    "ALOT": ("2026-08-27", 29.00),
}

STOCK_SETTLEMENTS = {
    "COMM": {"effective_date": "2026-01-14", "successor_ticker": "VISN",
             "shares_per_share": 1.0, "cash_per_share": 0.0,
             "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "ATXS": {"effective_date": "2026-01-23", "successor_ticker": "BCRX",
             "shares_per_share": 0.59, "cash_per_share": 8.55,
             "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    "CDXC": {"effective_date": "2025-03-19", "successor_ticker": "NAGE",
             "shares_per_share": 1.0, "cash_per_share": 0.0,
             "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "MFH": {"effective_date": "2025-11-13", "successor_ticker": "CD",
            "shares_per_share": 1.0, "cash_per_share": 0.0,
            "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
}


def install_verified_exit_data(engine):
    for ticker, (effective_date, cash_per_share) in CASH_SETTLEMENTS.items():
        engine.CASH_CORPORATE_ACTIONS[ticker] = {
            "effective_date": effective_date,
            "cash_per_share": cash_per_share,
            "reason": "CASH_MERGER",
            "execution": "cash-settlement",
        }
    engine.STOCK_CORPORATE_ACTIONS.update(STOCK_SETTLEMENTS)


# The candidate runner imports this module before engine.run.
import backtest_momentum_v3 as _engine
install_verified_exit_data(_engine)
