"""Verified corporate-action settlements for validation runs only.


Cash values are completed transaction consideration. No price is invented for
halted, unpriced or otherwise non-executable securities. The additions below
are sourced from issuer announcements or SEC completion filings; WBA excludes
its non-transferable, unpriced contingent DAP right and INFN uses the documented
non-electing cash consideration.
"""


CASH_SETTLEMENTS = {
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1721386/0001140361-25-023577.txt
    'LSEA': ('2025-06-25', 11.3),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/917491/0001193125-25-161621.txt
    'FARO': ('2025-07-21', 44.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1786205/0001104659-26-050318.txt
    # Unpriced CVR excluded from fixed consideration.
    'ACLX': ('2026-04-28', 115.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1889956/0001193125-26-136043.txt
    'OS': ('2026-04-01', 24.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1834494/0001140361-25-039178.txt
    'MLNK': ('2025-10-24', 20.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/896429/0001140361-26-020064.txt
    'CTLP': ('2026-05-08', 11.2),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1408100/0001140361-26-025340.txt
    'KW': ('2026-06-16', 10.9),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1820877/0001140361-24-032015.txt
    'AIRC': ('2024-06-28', 39.12),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1515816/0001193125-26-024519.txt
    'PLYM': ('2026-01-28', 22.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1725057/0001140361-26-003628.txt
    'DAY': ('2026-02-04', 70.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1545654/0001104659-26-029533.txt
    'ALEX': ('2026-03-12', 20.85),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1397702/0001140361-24-041264.txt
    'SILK': ('2024-09-17', 27.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1786255/0001104659-24-025251.txt
    # Unpriced CVR excluded from fixed consideration.
    'ICVX': ('2024-02-19', 15.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/850460/0000850460-24-000070.txt
    'WIRE': ('2024-07-02', 290.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1407623/0001193125-25-025059.txt
    'ROIC': ('2025-02-12', 17.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1465740/0001104659-26-100622.txt
    'TWO': ('2026-08-25', 12.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1744659/0001140361-25-044946.txt
    # Unpriced CVR excluded from fixed consideration.
    'AKRO': ('2025-12-09', 54.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/894081/0000950103-25-004720.txt
    'ATSG': ('2025-04-11', 22.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/701288/0001104659-24-091469.txt
    'ATRI': ('2024-08-21', 460.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1808665/0001104659-26-074619.txt
    'ASRT': ('2026-06-16', 23.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1597264/0001193125-25-160804.txt
    # Unpriced CVR excluded from fixed consideration.
    'BPMC': ('2025-07-18', 129.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1141103/0000950103-26-011218.txt
    'CCRN': ('2026-07-21', 13.25),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1178879/0001140361-26-016968.txt
    'FOLD': ('2026-04-27', 14.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1845337/0001193125-26-171997.txt
    'DAWN': ('2026-04-23', 21.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/850209/0001104659-25-088056.txt
    'FL': ('2025-09-08', 24.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1766363/0001193125-25-060947.txt
    'EDR': ('2025-03-24', 27.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1785173/0001193125-25-257616.txt
    # Unpriced CVR excluded from fixed consideration.
    'ETNB': ('2025-10-30', 14.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1627014/0001193125-23-228148.txt
    'BKI': ('2023-09-05', 75.867),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1621563/0000950103-25-001807.txt
    'SUM': ('2025-02-10', 52.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1831840/0001140361-26-017299.txt
    'SEMR': ('2026-04-28', 12.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1658247/0001140361-26-035195.txt
    'CRNX': ('2026-09-01', 85.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1642545/0001193125-24-151730.txt
    'SWAV': ('2024-05-31', 335.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1172222/0001193125-24-221104.txt
    'HA': ('2024-09-18', 18.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/931584/0001193125-25-011290.txt
    'USAP': ('2025-01-23', 45.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1567514/0001193125-25-071325.txt
    'ITCI': ('2025-04-02', 132.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1043604/0001193125-25-154400.txt
    'JNPR': ('2025-07-02', 40.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1066605/0001193125-25-313582.txt
    'HSII': ('2025-12-10', 59.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1561680/0001193125-26-222960.txt
    'TPH': ('2026-05-14', 47.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1169445/0001193125-26-299668.txt
    'TBRG': ('2026-07-09', 26.25),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1861560/0001193125-26-304126.txt
    'NUVL': ('2026-07-15', 124.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1372020/0001193125-26-136214.txt
    'GLDD': ('2026-04-01', 17.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1600438/0001140361-25-033989.txt
    'GMS': ('2025-09-04', 110.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1811764/0001193125-23-303512.txt
    'PNT': ('2023-12-27', 12.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1679363/0001193125-24-202123.txt
    'MORF': ('2024-08-16', 57.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1840574/0001193125-25-165462.txt
    # Unpriced CVR excluded from fixed consideration.
    'VERV': ('2025-07-25', 10.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1827506/0001104659-25-102971.txt
    'TRML': ('2025-10-28', 48.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1348911/0001140361-26-024949.txt
    'KALV': ('2026-06-11', 27.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1369568/0001193125-26-304984.txt
    'CPRX': ('2026-07-15', 31.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1562476/0001193125-26-316037.txt
    'TMHC': ('2026-07-27', 72.5),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1527508/0000950170-25-048426.txt
    'PTVE': ('2025-04-01', 18.0),
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1807846/0000950103-25-004975.txt
    # Unpriced CVR excluded from fixed consideration.
    'ML': ('2025-04-17', 82.0),
    # Unpriced CVR excluded; fixed cash only. https://www.sec.gov/Archives/edgar/data/1808865/0001193125-25-192031.txt
    'ITOS': ('2025-08-29', 10.047),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1029142/0001193125-26-043821.txt
    'DVAX': ('2026-02-10', 15.5),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1419041/0001140361-26-034698.txt
    'FBRX': ('2026-08-27', 77),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1567925/0001140361-26-027203.txt
    'SILA': ('2026-07-01', 30.38),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1118417/0001193125-24-170493.txt
    'MODN': ('2024-06-27', 30),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1195734/0001193125-25-248610.txt
    'PBPB': ('2025-10-23', 17.12),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/891024/0001193125-25-083614.txt
    'PDCO': ('2025-04-17', 31.35),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1749704/0001193125-24-132655.txt
    'AGTI': ('2024-05-07', 10),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1863105/0001193125-24-016530.txt
    'ESMT': ('2024-01-26', 23),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1166388/0001193125-25-299093.txt
    'VRNT': ('2025-11-26', 20.5),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1431695/0001140361-25-034771.txt
    'OLO': ('2025-09-12', 10.25),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/1124941/0001213900-25-036794.txt
    'BECN': ('2025-04-29', 124.35),
    # Completed common-share cash consideration. https://www.sec.gov/Archives/edgar/data/59440/0001104659-24-106511.txt
    'VGR': ('2024-10-07', 15),
    # Completed fixed common-share cash: https://www.sec.gov/Archives/edgar/data/1131399/000165495423008498/a2788e.htm
    'BLU': ('2023-06-28', 14.75),

    # Completed fixed common-share cash: https://www.sec.gov/Archives/edgar/data/1071058/000119312523195379/d499928dex991.htm
    'ABST': ('2023-07-27', 11.5),

    # Completed fixed common-share consideration: https://www.sec.gov/Archives/edgar/data/1645569/000119312523206894/d502246d8k.htm
    'DICE': ('2023-08-09', 48),
    # Completed fixed common-share consideration: https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2023-240
    'PRVB': ('2023-04-27', 25),
    # Completed fixed common-share consideration: https://www.syneoshealth.com/news/releases/syneos-health-closes-transaction-private-investment-firms
    'SYNH': ('2023-09-28', 43),
    # Completed fixed common-share consideration: https://www.sec.gov/Archives/edgar/data/54381/000114036124020740/ef20027261_8k.htm
    'KAMN': ('2024-04-19', 46),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1059262/0001193125-24-140235.txt
    "SP": ('2024-05-16', 54),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1017480/0001140361-24-034113.txt
    "HIBB": ('2024-07-25', 87.5),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/704562/0001140361-25-003108.txt
    "CDMO": ('2025-02-05', 12.5),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1842718/0001140361-25-046475.txt
    "IAS": ('2025-12-23', 10.3),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/924901/0001104659-26-066981.txt
    "VRE": ('2026-05-27', 19),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1127703/0001127703-26-000032.txt
    "PRA": ('2026-06-26', 25),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1320414/0001104659-26-079643.txt
    "SEM": ('2026-06-30', 16.5),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1835256/0001193125-24-284941.txt
    "NAPA": ('2024-12-24', 11.1),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1739942/0001193125-25-082231.txt
    "SWI": ('2025-04-16', 18.5),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/912603/0001140361-25-025485.txt
    "RDUS": ('2025-07-10', 30),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1839439/0000950103-25-004791.txt
    "PYCR": ('2025-04-14', 22.5),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/55067/0001193125-25-315130.txt
    "K": ('2025-12-11', 83.5),
    # Unpriced CVR excluded; fixed cash only.
    # https://www.sec.gov/Archives/edgar/data/1320695/0001320695-26-000014.txt
    "THS": ('2026-02-11', 22.5),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1012100/0001193125-26-148959.txt
    "SEE": ('2026-04-09', 42.15),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1524931/0001524931-24-000102.txt
    "CHUY": ('2024-10-11', 37.5),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1634997/0001193125-24-284174.txt
    "AGR": ('2024-12-23', 35.75),
    # Unpriced CVR excluded; fixed cash only.
    # https://www.sec.gov/Archives/edgar/data/1531978/0000950157-25-000330.txt
    "FNA": ('2025-04-21', 13),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1392972/0001193125-25-312044.txt
    "PRO": ('2025-12-08', 23.25),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/45876/0001193125-26-251741.txt
    "NVRI": ('2026-06-01', 15),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/773141/0000950142-24-001115.txt
    "MDC": ('2024-04-19', 63),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1668673/0001104659-24-111319.txt
    "PETQ": ('2024-10-25', 31),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1959348/0001193125-25-219988.txt
    "KLG": ('2025-09-26', 23),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/39899/0001104659-26-032772.txt
    "TGNA": ('2026-03-19', 22),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1282977/0001140361-23-055598.txt
    "GHL": ('2023-12-01', 15),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1679688/0001104659-26-112148.txt
    "DBRG": ('2026-09-30', 16),
    # Completed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/72333/0001104659-25-050982.txt
    "JWN": ('2025-05-20', 24.25),
    # Unpriced CVR excluded; fixed cash only.
    # https://www.sec.gov/Archives/edgar/data/859737/0001193125-26-144632.txt
    "HOLX": ('2026-04-07', 76),
    # Unpriced CVR excluded; fixed cash only.
    # https://www.sec.gov/Archives/edgar/data/791908/0001193125-26-302648.txt
    "XOMA": ('2026-07-14', 39),
    # Unpriced CVR excluded; fixed cash only.
    # https://www.sec.gov/Archives/edgar/data/1583107/0001104659-26-109979.txt
    "TBPH": ('2026-09-23', 17),
    # Completed fixed cash; SEC issuer completion releases and 8-K terms.
    # https://www.sec.gov/Archives/edgar/data/1448056/000119312523273042/d469974dex991.htm
    "NEWR": ("2023-11-08", 87.0),
    # https://www.sec.gov/Archives/edgar/data/896841/000183988223030181/ex99-1.htm
    "AVID": ("2023-11-07", 27.05),
    # https://www.sec.gov/Archives/edgar/data/1760717/000110465923110660/tm2328754d2_8k.htm
    "SCPL": ("2023-10-23", 22.95),
    # Completed September 21 2023 before open, fixed cash.
    # https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2023-531
    "RADI": ("2023-09-21", 15.00),
    # SEC completed August 18 2023, fixed common-share cash.
    # https://www.sec.gov/Archives/edgar/data/1790982/000114036123040367/brhc20057664_8k.htm
    "ARNC": ("2023-08-18", 30.00),
    # Completed fixed common-share cash consideration; primary source:
    # https://www.sec.gov/Archives/edgar/data/708818/0001193125-23-274104.txt
    "NXGN": ("2023-11-09", 23.95),
    # Completed fixed common-share cash consideration; primary source:
    # https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2023-595
    "HCCI": ("2023-10-17", 45.5),
    # Completed fixed common-share cash consideration; primary source:
    # https://www.sec.gov/Archives/edgar/data/789019/000119312523255762/d537928d8k.htm
    "ATVI": ("2023-10-13", 95),
    # Completed fixed common-share cash consideration; primary source:
    # https://www.sec.gov/Archives/edgar/data/318154/000119312523252361/d534754dex991.htm
    "HZNP": ("2023-10-06", 116.5),
    # Nasdaq confirms March 2 completion; unpriced nontransferable CVR excluded.
    # https://www.nasdaqtrader.com/TraderNews.aspx?id=eca2023-126
    "ALBO": ("2023-03-02", 42.00),
    # SEC completion, fixed cash; June 1 trading suspension and closing announcement.
    # https://www.sec.gov/Archives/edgar/data/1273931/0001193125-23-158474.txt
    "MGI": ("2023-06-01", 11.00),
    # SEC completion August 23 2023, fixed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1543916/000114036123040969/brhc20057813_8k.htm
    "FORG": ("2023-08-23", 23.25),
    # SEC completion August 11 2023. Nontransferable, unpriced CVR excluded.
    # https://www.sec.gov/Archives/edgar/data/1435049/000119312523210803/d103891d8k.htm
    "KDNY": ("2023-08-11", 40.00),
    # SEC completed April 27 2023, fixed common-share consideration.
    # https://www.sec.gov/Archives/edgar/data/1180145/0001104659-23-051430.txt
    "CSII": ("2023-04-27", 20.00),
    # SEC completed June 14 2023, fixed tender/merger consideration.
    # https://www.sec.gov/Archives/edgar/data/1324272/0001193125-23-166585.txt
    "RUTH": ("2023-06-14", 21.50),
    # SEC completion fixed cash: https://www.sec.gov/Archives/edgar/data/1160951/0001140361-23-014664.txt
    "DCT": ("2023-03-30", 19.00),
    # SEC completion fixed cash: https://www.sec.gov/Archives/edgar/data/1599489/0001104659-23-122267.txt
    "VRTV": ("2023-11-30", 170.00),
    # SEC completed fixed consideration: https://www.sec.gov/Archives/edgar/data/1338065/0001193125-23-167475.txt
    "DCP": ("2023-06-15", 41.75),
    # SEC completed fixed consideration: https://www.sec.gov/Archives/edgar/data/1651052/0001104659-23-097110.txt
    "FOCS": ("2023-08-31", 53),
    # SEC completed fixed consideration: https://www.sec.gov/Archives/edgar/data/1577916/0001193125-25-294735.txt
    "PINC": ("2025-11-25", 28.25),
    # Completed July 28 2023; fixed cash, SEC https://www.sec.gov/Archives/edgar/data/40888/0001193125-23-196927.txt
    "AJRD": ("2023-07-28", 58.00),
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
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/946647/0001193125-25-043541.txt
    'PFC': {'effective_date': '2025-03-03', 'successor_ticker': 'WSBC', 'shares_per_share': 0.8, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/946647/0001193125-25-043541.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1393612/0001193125-25-122107.txt
    'DFS': {'effective_date': '2025-05-19', 'successor_ticker': 'COF', 'shares_per_share': 1.0192, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1393612/0001193125-25-122107.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1723089/0001193125-25-159855.txt
    'CHX': {'effective_date': '2025-07-16', 'successor_ticker': 'SLB', 'shares_per_share': 0.735, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1723089/0001193125-25-159855.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/846901/0001193125-24-140117.txt
    'LBAI': {'effective_date': '2024-05-16', 'successor_ticker': 'PFS', 'shares_per_share': 0.8319, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/846901/0001193125-24-140117.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1439095/0001193125-25-269775.txt
    'MRC': {'effective_date': '2025-11-06', 'successor_ticker': 'DNOW', 'shares_per_share': 0.9489, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1439095/0001193125-25-269775.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1382821/0000950142-25-001793.txt
    'RDFN': {'effective_date': '2025-07-01', 'successor_ticker': 'RKT', 'shares_per_share': 0.7926, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1382821/0000950142-25-001793.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1532961/0001628280-25-037472.txt
    'NVEE': {'effective_date': '2025-08-04', 'successor_ticker': 'TIC', 'shares_per_share': 1.1523, 'cash_per_share': 10.0, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1532961/0001628280-25-037472.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1038357/0001193125-24-130052.txt
    'PXD': {'effective_date': '2024-05-03', 'successor_ticker': 'XOM', 'shares_per_share': 2.3234, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1038357/0001193125-24-130052.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1592000/0001213900-25-008864.txt
    'ENLC': {'effective_date': '2025-01-31', 'successor_ticker': 'OKE', 'shares_per_share': 0.1412, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1592000/0001213900-25-008864.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1509589/0001104659-26-008521.txt
    'CIVI': {'effective_date': '2026-01-30', 'successor_ticker': 'SM', 'shares_per_share': 1.45, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1509589/0001104659-26-008521.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/920112/0001193125-25-018916.txt
    'HTLF': {'effective_date': '2025-02-03', 'successor_ticker': 'UMBF', 'shares_per_share': 0.55, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/920112/0001193125-25-018916.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1378992/0001104659-25-042492.txt
    'BERY': {'effective_date': '2025-04-30', 'successor_ticker': 'AMCR', 'shares_per_share': 7.25, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1378992/0001104659-25-042492.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1501570/0001104659-25-100622.txt
    'VBTX': {'effective_date': '2025-10-20', 'successor_ticker': 'HBAN', 'shares_per_share': 1.95, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1501570/0001104659-25-100622.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/824410/0001104659-25-030581.txt
    'SASR': {'effective_date': '2025-04-01', 'successor_ticker': 'AUB', 'shares_per_share': 0.9, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/824410/0001104659-25-030581.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1013462/0001140361-25-026141.txt
    'ANSS': {'effective_date': '2025-07-17', 'successor_ticker': 'SNPS', 'shares_per_share': 0.3399, 'cash_per_share': 199.91, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1013462/0001140361-25-026141.txt'},
    # SEC completed fixed terms: https://www.sec.gov/Archives/edgar/data/1854401/0001193125-25-193504.txt
    'BRDG': {'effective_date': '2025-09-02', 'successor_ticker': 'APO', 'shares_per_share': 0.07081, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1854401/0001193125-25-193504.txt'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1308606/000119312524013577/d722798d8k.htm
    'SRC': {'effective_date': '2024-01-23', 'successor_ticker': 'O', 'shares_per_share': 0.762, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},

    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1616533/000162828024042831/peng-20241015.htm
    'SGH': {'effective_date': '2024-10-15', 'successor_ticker': 'PENG', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market'},

    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1322439/000162828024015450/egle-20240409.htm
    'EGLE': {'effective_date': '2024-04-09', 'successor_ticker': 'SBLK', 'shares_per_share': 2.6211, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},

    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1959472/000114036124000247/ny20017682x2_8k.htm
    'RPT': {'effective_date': '2024-01-02', 'successor_ticker': 'KIM', 'shares_per_share': 0.6049, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},

    # Completed common-share conversion: https://www.columbiabankingsystem.com/news-market-data/press-releases/press-release/2023/Columbia-Banking-System-and-Umpqua-Holdings-Corporation-Complete-Merger/default.aspx
    'UMPQ': {'effective_date': '2023-03-01', 'successor_ticker': 'COLB', 'shares_per_share': 0.5958, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},

    # Same common shares, explicit issuer filing: https://www.sec.gov/Archives/edgar/data/1725057/0000950170-24-009619.txt
    'CDAY': {'effective_date': '2024-02-01', 'successor_ticker': 'DAY', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market'},
    # Same common shares, explicit issuer filing: https://www.sec.gov/Archives/edgar/data/1481582/0001193125-26-051335.txt
    'RYI': {'effective_date': '2026-02-24', 'successor_ticker': 'RYZ', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market'},
    # Same common shares, explicit issuer filing: https://www.sec.gov/Archives/edgar/data/895447/0001193125-26-266625.txt
    'SCVL': {'effective_date': '2026-06-12', 'successor_ticker': 'SHOE', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market'},
    # Same common shares, explicit issuer filing: https://www.sec.gov/Archives/edgar/data/1591588/0001193125-25-307852.txt
    'AMRK': {'effective_date': '2025-12-02', 'successor_ticker': 'GOLD', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market'},
    # Same common shares, explicit issuer filing: https://www.sec.gov/Archives/edgar/data/821130/0001104659-25-073368.txt
    'USM': {'effective_date': '2025-08-12', 'successor_ticker': 'AD', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/77159/0001104659-23-072968.txt
    'ROCC': {'effective_date': '2023-06-20', 'successor_ticker': 'BTE', 'shares_per_share': 7.49, 'cash_per_share': 13.31, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1037676/0001104659-25-003782.txt
    'ARCH': {'effective_date': '2025-01-14', 'successor_ticker': 'CNR', 'shares_per_share': 1.326, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1037676/0001104659-25-003782.txt
    'CEIX': {'effective_date': '2025-01-15', 'successor_ticker': 'CNR', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/947559/0000947559-25-000035.txt
    'FBMS': {'effective_date': '2025-04-01', 'successor_ticker': 'RNST', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1517006/0001193125-25-007425.txt
    'GATO': {'effective_date': '2025-01-16', 'successor_ticker': 'AG', 'shares_per_share': 2.55, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/1528129/0001193125-25-319188.txt
    'VTLE': {'effective_date': '2025-12-15', 'successor_ticker': 'CRGY', 'shares_per_share': 1.9062, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},
    # Completed common-share conversion: https://www.sec.gov/Archives/edgar/data/28412/0001193125-26-032627.txt
    'CMA': {'effective_date': '2026-02-01', 'successor_ticker': 'FITB', 'shares_per_share': 1.8663, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market'},
    # Completed November 7 2023; common-share consideration $30 + 0.03002 SJM.
    # https://www.sec.gov/Archives/edgar/data/1644406/0001193125-23-272309.txt
    "TWNK": {"effective_date": "2023-11-07", "successor_ticker": "SJM", "shares_per_share": 0.03002, "cash_per_share": 30.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # Completed September 1 2023 before open; common shares convert to 0.75 GMED.
    # https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2023-493
    "NUVA": {"effective_date": "2023-09-01", "successor_ticker": "GMED", "shares_per_share": 0.75, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # Completed common-share conversion or unchanged common-stock symbol; primary source:
    # https://www.sec.gov/Archives/edgar/data/77877/000110465923088136/tm2321729d8_8k.htm
    "PDCE": {"effective_date": "2023-08-07", "successor_ticker": "CVX", "shares_per_share": 0.4638, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # Completed common-share conversion or unchanged common-stock symbol; primary source:
    # https://www.sec.gov/Archives/edgar/data/912603/0001157523-23-001375.txt
    "SCHN": {"effective_date": "2023-09-01", "successor_ticker": "RDUS", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # Completed common-share conversion or unchanged common-stock symbol; primary source:
    # https://investors.fiserv.com/news-releases/news-release-details/fiserv-completes-listing-transfer-new-york-stock-exchange
    "FISV": {"effective_date": "2023-06-07", "successor_ticker": "FI", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # Completed common-share conversion or unchanged common-stock symbol; primary source:
    # https://www.sec.gov/Archives/edgar/data/1655888/000119312523182372/d471939dex991.htm
    "ORCC": {"effective_date": "2023-07-06", "successor_ticker": "OBDC", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # Completed common-share conversion or unchanged common-stock symbol; primary source:
    # https://news.revvity.com/press-announcements/press-releases/press-release-details/2023/Revvity-Announces-Financial-Results-for-the-First-Quarter-of-2023/default.aspx
    "PKI": {"effective_date": "2023-05-16", "successor_ticker": "RVTY", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed September 1 2023: each NexTier common share receives 0.7520 PTEN shares.
    # https://www.sec.gov/Archives/edgar/data/1688476/0001688476-23-000147.txt
    "NEX": {"effective_date": "2023-09-01", "successor_ticker": "PTEN", "shares_per_share": 0.7520, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # Completed June 1 2023, common shares: $9 cash plus 0.1301 HNI.
    # https://www.sec.gov/Archives/edgar/data/55772/0001140361-23-027820.txt
    "KBAL": {"effective_date": "2023-06-01", "successor_ticker": "HNI", "shares_per_share": 0.1301, "cash_per_share": 9.0, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    # Completed July 20 2023, common shares convert to 0.895 Extra Space shares.
    # https://www.sec.gov/Archives/edgar/data/944314/0001193125-23-190113.txt
    "LSI": {"effective_date": "2023-07-20", "successor_ticker": "EXR", "shares_per_share": 0.895, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # SEC completed May 24 2023; each Evoqua share converts to 0.48 Xylem shares.
    # https://www.sec.gov/Archives/edgar/data/1604643/0001193125-23-152552.txt
    "AQUA": {"effective_date": "2023-05-24", "successor_ticker": "XYL", "shares_per_share": 0.48, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # SEC completed March 20 2023 terms: https://www.sec.gov/Archives/edgar/data/1745041/0001104659-23-034674.txt
    "IAA": {"effective_date": "2023-03-20", "successor_ticker": "RBA", "shares_per_share": 0.5252, "cash_per_share": 12.80, "reason": "STOCK_CASH_MERGER", "execution": "successor-market-plus-cash"},
    # SEC completed exchange ratio: https://www.sec.gov/Archives/edgar/data/928022/0001193125-24-083393.txt
    "CPE": {"effective_date": "2024-04-01", "successor_ticker": "APA", "shares_per_share": 1.0425, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # SEC completed exchange ratio: https://www.sec.gov/Archives/edgar/data/1136352/0001193125-23-270382.txt
    "CEQP": {"effective_date": "2023-11-03", "successor_ticker": "ET", "shares_per_share": 2.07, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # Unchanged common shares; SEC https://www.sec.gov/Archives/edgar/data/730464/0001104659-26-011611.txt
    "ATGE": {"effective_date": "2026-02-24", "successor_ticker": "CVSA", "shares_per_share": 1.0, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/1108134/0001104659-25-086043.txt
    "BHLB": {"effective_date": "2025-09-01", "successor_ticker": "BBT", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/1049782/0001104659-25-086054.txt
    "BRKL": {"effective_date": "2025-09-01", "successor_ticker": "BBT", "shares_per_share": 0.42, "cash_per_share": 0.0, "reason": "STOCK_MERGER", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/910073/0001193125-24-237666.txt
    "NYCB": {"effective_date": "2024-10-28", "successor_ticker": "FLG", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/1108426/0001108426-24-000082.txt
    "PNM": {"effective_date": "2024-08-05", "successor_ticker": "TXNM", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/1140859/0001104659-23-096698.txt
    "ABC": {"effective_date": "2023-08-30", "successor_ticker": "COR", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/1564902/0000950170-24-014585.txt
    "SEAS": {"effective_date": "2024-02-13", "successor_ticker": "PRKS", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/884219/0000950170-25-000594.txt
    "VVI": {"effective_date": "2025-01-02", "successor_ticker": "PRSU", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
    # SEC completed terms / same security name change: https://www.sec.gov/Archives/edgar/data/860546/0000860546-23-000039.txt
    "OFC": {"effective_date": "2023-09-15", "successor_ticker": "CDP", "shares_per_share": 1, "cash_per_share": 0.0, "reason": "SYMBOL_CHANGE", "execution": "successor-market"},
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
