"""Verified corporate-action settlements for validation runs only.


Cash values are completed transaction consideration. No price is invented for
halted, unpriced or otherwise non-executable securities. The additions below
are sourced from issuer announcements or SEC completion filings; WBA excludes
its non-transferable, unpriced contingent DAP right and INFN uses the documented
non-electing cash consideration.
"""


CASH_SETTLEMENTS = {
    "VVNT": ("2023-03-10", 12.00), "MYOV": ("2023-03-10", 27.00), "AIMC": ("2023-03-27", 62.00),
    "APEN": ("2023-04-04", 10.00), "TA": ("2023-05-15", 86.00),
    "MAXR": ("2023-05-03", 53.00), "SUMO": ("2023-05-12", 12.05),
    "CVT": ("2023-06-15", 8.50), "XM": ("2023-06-28", 18.15),
    "DSEY": ("2023-07-05", 8.40), "ARCE": ("2023-12-07", 14.00),
    "THRN": ("2023-10-16", 10.20), "SGEN": ("2023-12-14", 229.00), "CHS": ("2024-01-05", 7.60),
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
    "APGE": ("2026-09-03", 135.11),
    "WSR": ("2026-07-14", 19.00),
    "SGFY": ("2023-03-29", 30.50),
    "AAWW": ("2023-03-17", 102.50),
    "COWN": ("2023-03-01", 39.00), "ATCO": ("2023-03-28", 15.50),
    "INDT": ("2023-06-29", 67.00), "UNVR": ("2023-08-01", 36.15),
    "GLOP": ("2023-07-13", 8.65), "FRG": ("2023-08-21", 30.00),
    "AMK": ("2024-09-05", 35.25), "ENV": ("2024-11-25", 63.15),
    "HAYN": ("2024-11-21", 61.00), "VZIO": ("2024-12-03", 11.50),
    "CTLT": ("2024-12-18", 63.50), "SCWX": ("2025-02-03", 8.50),
    "INFN": ("2025-02-28", 6.65), "AGS": ("2025-06-30", 12.50),
    "WBA": ("2025-08-28", 11.45), "AMED": ("2025-08-14", 101.00),
    "SKX": ("2025-09-12", 63.00), "WOW": ("2025-12-31", 5.20),
    "ALE": ("2025-12-15", 67.00), "CWAN": ("2026-06-25", 24.55),
    "EA": ("2026-08-04", 210.00), "GBTG": ("2026-09-29", 9.50),
    # AstraZeneca completed Fusion Pharmaceuticals on 2024-06-04 for
    # $21.00 cash plus an unpriced, non-transferable $3.00 CVR.  Only the
    # fixed executable cash consideration is included here.
    # https://www.sec.gov/Archives/edgar/data/1805890/000119312524154275/d827973d8k.htm
    "FUSN": ("2024-06-04", 21.00),
    # Alkermes completed Avadel on 2026-02-12 for $21.00 cash plus an
    # unpriced, non-transferable $1.50 CVR.  Only fixed cash is executable.
    # https://www.sec.gov/Archives/edgar/data/1520262/000119312526047682/d43532d8k.htm
    "AVDL": ("2026-02-12", 21.00),
    # Completion filings supporting the fixed consideration below:
    # RXDX https://www.sec.gov/Archives/edgar/data/1718852/000119312523168524/d466468d8k.htm
    # RETA https://www.sec.gov/Archives/edgar/data/875045/000087504524000009/biib-20231231.htm
    # BVH  https://www.sec.gov/Archives/edgar/data/1674168/000114036125030585/ny20053112x2_ex99-2.htm
    # IMGN https://www.sec.gov/Archives/edgar/data/1551152/000110465924013692/tm245657d1_99-1.htm
    # AMAM https://www.sec.gov/Archives/edgar/data/1990550/000119312524061543/d750145d8k.htm
    # HARP https://www.sec.gov/Archives/edgar/data/1708493/000119312524064395/d808382d8k.htm
    # LBPH https://www.sec.gov/Archives/edgar/data/1832168/000114036124048133/ef20039392_8k.htm
    # CDTX https://www.sec.gov/Archives/edgar/data/1610618/000119312526005513/d55695dex99a5vi.htm
    # VTYX https://www.sec.gov/Archives/edgar/data/1851194/000119312526090059/d116049d8k.htm
    # RAPT https://www.sec.gov/Archives/edgar/data/1673772/000119312526086878/d69681d8k.htm
    "RXDX": ("2023-06-16", 200.00),
    "RETA": ("2023-09-26", 172.50),
    "BVH": ("2024-01-17", 75.00),
    "IMGN": ("2024-02-12", 31.26),
    "AMAM": ("2024-03-07", 28.00),
    "HARP": ("2024-03-11", 23.00),
    "LBPH": ("2024-12-02", 60.00),
    "CDTX": ("2026-01-07", 221.50),
    "VTYX": ("2026-03-04", 14.00),
    "RAPT": ("2026-03-03", 58.00),
}


STOCK_SETTLEMENTS = {
    # SEC verified same common shares, name/symbol change: https://www.sec.gov/Archives/edgar/data/1083446/0001104659-24-027198.txt
    "AMEH": {"effective_date": "2024-02-26", "successor_ticker": "ASTH", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC verified same common shares, name/symbol change: https://www.sec.gov/Archives/edgar/data/890564/0000890564-26-000025.txt
    "ASGN": {"effective_date": "2026-04-24", "successor_ticker": "EFOR", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC verified same common shares, name/symbol change: https://www.sec.gov/Archives/edgar/data/837465/0001193125-26-014581.txt
    "MODG": {"effective_date": "2026-01-16", "successor_ticker": "CALY", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC verified one-for-one holding-company reorganization: https://www.sec.gov/Archives/edgar/data/1498828/0001104659-23-090461.txt
    "HHC": {"effective_date": "2023-08-11", "successor_ticker": "HHH", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # SEC issuer name/symbol change, same common shares: https://www.sec.gov/Archives/edgar/data/789460/0001628280-23-022711.txt
    "INT": {"effective_date": "2023-06-16", "successor_ticker": "WKC", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC issuer name/symbol change, same common shares: https://www.sec.gov/Archives/edgar/data/1175454/0001628280-24-010593.txt
    "FLT": {"effective_date": "2024-03-25", "successor_ticker": "CPAY", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC issuer name/symbol change, same common shares: https://www.sec.gov/Archives/edgar/data/1206264/0001206264-25-000037.txt
    "TPX": {"effective_date": "2025-02-18", "successor_ticker": "SGI", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "WRK": {"effective_date": "2024-07-05", "successor_ticker": "SW", "shares_per_share": 1.0, "cash_per_share": 5.00, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    "ETRN": {"effective_date": "2024-07-22", "successor_ticker": "EQT", "shares_per_share": 0.3504, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    "SKYT": {"effective_date": "2026-07-31", "successor_ticker": "IONQ", "shares_per_share": 0.4883, "cash_per_share": 15.00, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    "COMM": {"effective_date": "2026-01-14", "successor_ticker": "VISN", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "ATXS": {"effective_date": "2026-01-23", "successor_ticker": "BCRX", "shares_per_share": 0.59, "cash_per_share": 8.55, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    "CDXC": {"effective_date": "2025-03-19", "successor_ticker": "NAGE", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "MFH": {"effective_date": "2025-11-13", "successor_ticker": "CD", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "STEL": {"effective_date": "2026-07-01", "successor_ticker": "PB", "shares_per_share": 0.3803, "cash_per_share": 11.36, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    "WBS": {"effective_date": "2026-08-20", "successor_ticker": "SAN", "shares_per_share": 2.0548, "cash_per_share": 48.75, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    # Pure one-for-one symbol changes, not acquisitions or return-based fixes.
    # BREA/SLMT: SEC annual filing; FORD/FWDI: SEC 10-K; GLTO/DMRA: issuer 8-K exhibit.
    "BREA": {"effective_date": "2025-10-03", "successor_ticker": "SLMT", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "FORD": {"effective_date": "2025-11-17", "successor_ticker": "FWDI", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    "GLTO": {"effective_date": "2026-03-10", "successor_ticker": "DMRA", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
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
