"""Verified corporate-action settlements for validation runs only.




Prices are cash consideration available on each completed transaction date.
Unpriced CVRs are deliberately excluded.
"""
import os




CASH = """MYOV|2023-03-10|27
AIMC|2023-03-27|62
APEN|2023-04-04|10
TA|2023-05-15|86
MAXR|2023-05-03|53
SUMO|2023-05-12|12.05
CVT|2023-06-15|8.5
XM|2023-06-28|18.15
DSEY|2023-07-05|8.4
CHS|2024-01-05|7.6
MRTX|2024-01-23|58
KRTX|2024-03-18|330
PGTI|2024-03-28|42
EVBG|2024-07-02|35
ITI|2024-11-01|7.2
PLYA|2025-06-17|13.5
TGI|2025-07-24|26
VIGL|2025-08-06|8
SPTN|2025-09-22|26.9
BASE|2025-09-24|24.5
ZIMV|2025-10-20|19
ODP|2025-12-10|28
PKST|2026-05-06|21
EHAB|2026-05-15|13.8
AVNS|2026-07-27|25"""




STOCK = {
    "COMM": {"effective_date": "2026-01-14", "successor_ticker": "VISN",
             "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "ATXS": {"effective_date": "2026-01-23", "successor_ticker": "BCRX",
             "shares_per_share": 0.59, "cash_per_share": 8.55, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    "CDXC": {"effective_date": "2025-03-19", "successor_ticker": "NAGE",
             "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
}




def install_verified_exit_data(engine):
    old_cash = dict(engine.CASH_CORPORATE_ACTIONS)
    old_stock = dict(engine.STOCK_CORPORATE_ACTIONS)
    old_first = engine.first_tradable_row
    for record in CASH.splitlines():
        ticker, effective_date, cash_per_share = record.split("|")
        engine.CASH_CORPORATE_ACTIONS[ticker] = {
            "effective_date": effective_date,
            "cash_per_share": float(cash_per_share),
            "reason": "CASH_MERGER",
            "execution": "cash-settlement",
        }
    engine.STOCK_CORPORATE_ACTIONS.update(STOCK)
    client = engine.PolygonClient(os.environ["POLYGON_API_KEY"])




    def first_tradable_row(cache, trading_days, ticker, target_day, latest_day):
        day, row = old_first(cache, trading_days, ticker, target_day, latest_day)
        if row is not None or ticker != "CDXC":
            return day, row
        for day in trading_days:
            pass


import backtest_momentum_v3 as _engine
install_verified_exit_data(_engine)
