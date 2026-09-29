"""Verified corporate-action settlements for validation runs only.

Cash values are completed transaction consideration. No price is invented for
halted, unpriced or otherwise non-executable securities.
"""

CASH_SETTLEMENTS = {
    "MYOV": ("2023-03-10", 27.00), "AIMC": ("2023-03-27", 62.00),
    "APEN": ("2023-04-04", 10.00), "TA": ("2023-05-15", 86.00),
    "MAXR": ("2023-05-03", 53.00), "SUMO": ("2023-05-12", 12.05),
    "CVT": ("2023-06-15", 8.50), "XM": ("2023-06-28", 18.15),
    "DSEY": ("2023-07-05", 8.40), "ARCE": ("2023-12-07", 14.00),
    "THRN": ("2023-10-16", 10.20), "CHS": ("2024-01-05", 7.60),
    "MRTX": ("2024-01-23", 58.00), "AYX": ("2024-03-13", 48.25),
    "TGH": ("2024-03-14", 50.00), "SPLK": ("2024-03-18", 157.00),
    "KRTX": ("2024-03-18", 330.00), "PGTI": ("2024-03-28", 42.00),
    "DSKE": ("2024-04-01", 8.30), "TCN": ("2024-05-01", 11.25),
    "TAST": ("2024-05-16", 9.55), "SLCA": ("2024-07-31", 15.50),
    "EVBG": ("2024-07-02", 35.00), "AAN": ("2024-10-03", 10.10),
    "PWSC": ("2024-10-01", 22.80), "PRFT": ("2024-10-02", 76.00),
    "SQSP": ("2024-10-17", 46.50), "ITI": ("2024-11-01", 7.20),
    "SRCL": ("2024-11-04", 62.00), "INST": ("2024-11-13", 23.60),
    "RCM": ("2024-11-19", 14.30), "SMAR": ("2025-01-22", 56.50),
    "ZUO": ("2025-02-14", 10.00), "ALTR": ("2025-03-26", 113.00),
    "PLYA": ("2025-06-17", 13.50), "TGI": ("2025-07-24", 26.00),
    "VIGL": ("2025-08-06", 8.00), "SPTN": ("2025-09-22", 26.90),
    "BASE": ("2025-09-24", 24.50), "AVDX": ("2025-10-15", 10.00),
    "ZIMV": ("2025-10-20", 19.00), "INFA": ("2025-11-18", 25.00),
    "ODP": ("2025-12-10", 28.00), "SPNS": ("2025-12-17", 43.50),
    "CIO": ("2026-01-09", 7.00), "GES": ("2026-01-23", 16.75),
    "HI": ("2026-02-10", 32.00), "PKST": ("2026-05-06", 21.00),
    "CSGS": ("2026-05-14", 80.70), "EHAB": ("2026-05-15", 13.80),
    "MASI": ("2026-06-10", 180.00), "JHG": ("2026-06-30", 52.00),
    "AVNS": ("2026-07-27", 25.00), "TALK": ("2026-08-17", 5.25),
    "ALOT": ("2026-08-27", 29.00),
}

STOCK_SETTLEMENTS = {
    "COMM": {"effective_date": "2026-01-14", "successor_ticker": "VISN", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "ATXS": {"effective_date": "2026-01-23", "successor_ticker": "BCRX", "shares_per_share": 0.59, "cash_per_share": 8.55, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    "CDXC": {"effective_date": "2025-03-19", "successor_ticker": "NAGE", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "MFH": {"effective_date": "2025-11-13", "successor_ticker": "CD", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
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


import backtest_momentum_v3 as _engine
install_verified_exit_data(_engine)
