"""Verified corporate-action settlements for validation runs only.


Cash values are completed transaction consideration. No price is invented for
halted, unpriced or otherwise non-executable securities. The additions below
are sourced from issuer announcements or SEC completion filings; WBA excludes
its non-transferable, unpriced contingent DAP right and INFN uses the documented
non-electing cash consideration.
"""


CASH_SETTLEMENTS = {
    'DESP': ('2025-05-15', 19.5), # https://www.sec.gov/Archives/edgar/data/1703141/000094787125000525/ss4830126_ex9901.htm
    # Completed July25; trading suspended AS OF CLOSE July25. Operational first nontrading session July26. https://www.prnewswire.com/news-releases/hollysys-announces-completion-of-merger-transaction-with-ascendent-capital-partners-302206694.html
    'HOLI': ('2024-07-26', 26.5),
    # Closed before open December12; administrative suspension December13. https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2024-602
    'AY': ('2024-12-12', 22.0),
    # Nasdaq confirms September 12 completed BEFORE OPEN; September 13 administrative suspension is not the action date. https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2024-417
    'WKME': ('2024-09-12', 14.0),
    # Completed common-share consideration; prior-open halt verified. https://www.sec.gov/Archives/edgar/data/1356570/0002077096-25-000155.txt
    'WNS': ('2025-10-17', 76.5),
    # Completed common-share consideration; prior-open halt verified. https://www.sec.gov/Archives/edgar/data/1484565/0001193125-26-228016.txt
    'SLNO': ('2026-05-18', 53.0),
    # Completed common-share consideration; prior-open halt verified. https://www.sec.gov/Archives/edgar/data/1163302/0001104659-25-060674.txt
    'X': ('2025-06-18', 55.0),
    # Completed common-share consideration; prior-open halt verified. https://www.sec.gov/Archives/edgar/data/1773427/0001104659-25-064445.txt
    'SWTX': ('2025-07-01', 47.0),
    # Completed common-share consideration; prior-open halt verified. https://www.sec.gov/Archives/edgar/data/1531048/0001193125-25-029190.txt
    'NARI': ('2025-02-19', 80.0),
    # Verified completed terms: https://www.sec.gov/Archives/edgar/data/1651311/0001193125-25-335951.txt
    # Non-tendered common shares cancelled in back-end merger; not tender acceptance December 12.
    'MRUS': ('2025-12-30', 97),
    # Verified completed terms: https://www.sec.gov/Archives/edgar/data/893691/0001193125-24-139523.txt
    # NYSE withdrawal before May 15 open.
    'DOOR': ('2024-05-15', 133),
    # Verified completed terms: https://www.sec.gov/Archives/edgar/data/1654151/0001193125-24-158772.txt
    # Nasdaq suspension before June 11 opening.
    'DCPH': ('2024-06-11', 25.6),
    # Verified completed terms: https://www.sec.gov/Archives/edgar/data/1492422/0001193125-26-222923.txt
    # Non-transferable unpriced CVR excluded; not valued at maximum $4.
    'APLS': ('2026-05-14', 41),
    # Verified completed terms: https://www.sec.gov/Archives/edgar/data/1699838/0001104659-26-029071.txt
    # Nasdaq suspended before opening on Closing Date.
    'CFLT': ('2026-03-17', 31),
    # Verified completed terms: https://www.sec.gov/Archives/edgar/data/1897982/0001140361-25-008260.txt
    # 
    'AZPN': ('2025-03-12', 265),
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1856430/0001104659-24-071779.txt
    'SNPO': ('2024-06-14', 10.75),
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1805387/0001193125-24-190764.txt
    'CERE': ('2024-08-01', 45.0),
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1721947/0001104659-26-009193.txt
    'JAMF': ('2026-01-30', 13.05),
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1769617/0001104659-25-105592.txt
    # Final proration: all non-election shares receive $12 cash.
    'HONE': ('2025-11-01', 12.0),
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
    'JNVR': {'effective_date': '2025-05-05', 'legal_effective_date': '2025-05-05', 'successor_ticker': 'DFDV', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.nasdaq.com/press-release/defi-development-corp-announces-ticker-symbol-change-dfdv-2025-05-02', 'note': 'Issuer confirms market-open change, unchanged CUSIP and no corporate-structure change. Later splits remain separate paired-basis adjustments.'},
    'EYEN': {'effective_date': '2025-07-03', 'legal_effective_date': '2025-07-01', 'successor_ticker': 'HYPD', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1682639/0001104659-25-065294.txt', 'note': 'Legal name change July 1; actual market ticker change July 3. Same common rights; February reverse split is separate from this 1:1 change.'},
    'CSWI': {'effective_date': '2025-06-09', 'legal_effective_date': '2025-06-09', 'successor_ticker': 'CSW', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://cswindustrials.gcs-web.com/news-releases/news-release-details/csw-industrials-announces-commencement-trading-new-york-stock', 'note': 'Issuer confirms commencement at June 9 NYSE opening; same common shares transfer from Nasdaq.'},
    'PX': {'effective_date': '2026-02-11', 'legal_effective_date': '2026-02-11', 'successor_ticker': 'RPC', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1841968/000119312526010556/d28146d8k.htm', 'note': 'SEC certificate and later amended Form 4 confirm effective February 11. CUSIP unchanged. RPC is Ridgepost CIK1841968, not RPC Inc. CIK742278 (ticker RES).'},
    'VERB': {'effective_date': '2025-09-02', 'legal_effective_date': '2025-09-02', 'successor_ticker': 'TONX', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1566610/0001493152-25-012461.txt', 'note': 'SEC certificate is effective September 2 at9 a.m.; later issuer exhibit confirms trading as TONX from that day. Entry on the old symbol still needs actual successor execution, never a synthetic original quote.'},
    'PSTG': {'effective_date': '2026-04-17', 'legal_effective_date': '2026-04-17', 'successor_ticker': 'P', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.everpuredata.com/uk/company/newsroom/press-releases/everpure-to-change-ticker-symbol.html', 'note': 'Ticker change April17 is distinct from March5 name rebrand (when PSTG stayed unchanged). Common CUSIP74624M102 unchanged; single-letter ticker needs dated identity.'},
    'DOOO': {'effective_date': '2025-12-08', 'legal_effective_date': '2025-12-08', 'successor_ticker': 'DOO', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1748797/000119312526125055/d76000dex991.htm', 'note': 'Completed Nasdaq symbol change documented in annual information form. Use US Nasdaq USD successor; Canadian TSX DOO is not an interchangeable USD observation.'},
    'SILV': {'effective_date': '2025-02-14', 'legal_effective_date': '2025-02-14', 'successor_ticker': 'CDE', 'shares_per_share': 1.6022, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1659520/000095014225000380/eh250591256_ex9901.htm', 'note': 'Completed before February14 open. Preserve common-share 1.6022 exchange, not rounded option-contract 1.60 delivery.'},
    'SCS': {'effective_date': '2025-12-10', 'legal_effective_date': '2025-12-10', 'successor_ticker': 'HNI', 'shares_per_share': 0.2192, 'cash_per_share': 7.2, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1050825/0001193125-25-315864.txt', 'note': 'Completed before December10 opening. SEC explicitly confirms non-electing common holders receive mixed consideration0.2192 plus$7.20; does not assume the optional all-cash election.'},
    # Recovered 22-case primary-source batch, 2026-10-12. Validation only.
    'SNV': {'effective_date': '2026-01-02', 'legal_effective_date': '2026-01-01', 'successor_ticker': 'PNFP', 'shares_per_share': 0.5237, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/18349/0001140361-26-000049.txt', 'note': 'Operational first session January 2; successor is new Georgia issuer CIK 2082866, not legacy PNFP CIK 1115055. Dated identity and paired prices still required.'},
    'SMLR': {'effective_date': '2026-01-16', 'legal_effective_date': '2026-01-16', 'successor_ticker': 'ASST', 'shares_per_share': 21.05, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1554859/0001104659-26-004581.txt', 'note': 'Nasdaq confirms completed before January 16 open and last trade January 15; administrative suspension January 20 is not conversion date. Preserve legal 21.05 ratio despite later successor splits.'},
    'LSXMA': {'effective_date': '2024-09-10', 'legal_effective_date': '2024-09-09', 'successor_ticker': 'SIRI', 'shares_per_share': 0.8375, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1560385/0001104659-24-098251.txt', 'note': 'Completed September 9 at 4:05 p.m.; first successor session September 10. New Sirius issuer differs from legacy SIRI; requires dated successor identity.'},
    'LSXMK': {'effective_date': '2024-09-10', 'legal_effective_date': '2024-09-09', 'successor_ticker': 'SIRI', 'shares_per_share': 0.8375, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1560385/0001104659-24-098251.txt', 'note': 'Completed September 9 at 4:05 p.m.; first successor session September 10. Same completed common exchange as LSXMA, not legacy SIRI 0.1 exchange.'},
    'LBRDA': {'effective_date': '2026-08-20', 'legal_effective_date': '2026-08-19', 'successor_ticker': 'CHTR', 'shares_per_share': 0.236, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1611983/0001140361-26-033932.txt', 'note': 'SEC completed effective August 19 at 11:56 p.m.; first following session August 20. Fractional-share cash is not a fixed extra consideration.'},
    'LBRDK': {'effective_date': '2026-08-20', 'legal_effective_date': '2026-08-19', 'successor_ticker': 'CHTR', 'shares_per_share': 0.236, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1611983/0001140361-26-033932.txt', 'note': 'Same completed common exchange as LBRDA; legal late-night closing preserved separately.'},
    'HEP': {'effective_date': '2023-12-01', 'legal_effective_date': '2023-12-01', 'successor_ticker': 'DINO', 'shares_per_share': 0.315, 'cash_per_share': 4, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1283140/0001193125-23-287465.txt', 'note': 'SEC confirms fixed 0.3150 shares plus $4 cash and suspension before December 1 opening.'},
    'AZEK': {'effective_date': '2025-07-01', 'legal_effective_date': '2025-07-01', 'successor_ticker': 'JHX', 'shares_per_share': 1.034, 'cash_per_share': 26.45, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1782754/0001193125-25-154115.txt', 'note': 'SEC completed fixed 1.0340 JHX ordinary shares plus $26.45 and removal prior July 1 open; no conversion to announcement headline price.'},
    'WWE': {'effective_date': '2023-09-12', 'legal_effective_date': '2023-09-12', 'successor_ticker': 'TKO', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1091907/0001193125-23-233499.txt', 'note': 'SEC completed one TKO Class A share per WWE common share; TKO trades from September 12 opening.'},
    'CMPO': {'effective_date': '2026-01-23', 'legal_effective_date': '2026-01-23', 'successor_ticker': 'GPGI', 'shares_per_share': 1, 'cash_per_share': 0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1823144/000162828026017266/cmpo-20251231.htm', 'note': 'Same common stock continues at January 23 open. The earlier RHLD spin-off is separate and cannot be treated as this symbol change.'},
    'SIX': {'effective_date': '2024-07-02', 'legal_effective_date': '2024-07-01', 'successor_ticker': 'FUN', 'shares_per_share': 0.58, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/701374/0001193125-24-173426.txt', 'note': 'SEC confirms 0.5800 new HoldCo common shares and first successor session July 2. $1.53 special dividend is separately documented and omitted under the fixed price-only scope, not assigned zero value.'},
    'VSTO': {'effective_date': '2024-11-27', 'legal_effective_date': '2024-11-27', 'successor_ticker': 'GEAR', 'shares_per_share': 1, 'cash_per_share': 25.75, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1616318/0001616318-24-000122.txt', 'note': 'Completed fixed one Revelyst share plus $25.75; issuer confirms GEAR starts November 27. Later GEAR acquisition is a separate event.'},
    # Same common CUSIP; ticker begins June4. https://www.sec.gov/Archives/edgar/data/1800227/0001104659-26-070364.txt
    'IAC': {'effective_date': '2026-06-04', 'successor_ticker': 'PPLI', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1800227/0001104659-26-070364.txt'},
    # Legal January1; SEC explicitly suspension before January2 open. https://www.sec.gov/Archives/edgar/data/1564618/0000950103-25-000002.txt
    'IBTX': {'effective_date': '2025-01-02', 'successor_ticker': 'SSB', 'shares_per_share': 0.6, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1564618/0000950103-25-000002.txt'},
    # SEC suspension prior August1 opening; completed fixed common ratio. https://www.sec.gov/Archives/edgar/data/1053584/0001104659-24-084676.txt
    'MCBC': {'effective_date': '2024-08-01', 'successor_ticker': 'WTFC', 'shares_per_share': 0.137, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1053584/0001104659-24-084676.txt'},
    # SEC old common cancelled at12:01a.m.; successor SEC2074176/000119312525183036 confirms VNOM starts same opening. https://www.sec.gov/Archives/edgar/data/1949543/0001193125-25-183045.txt
    'STR': {'effective_date': '2025-08-19', 'successor_ticker': 'VNOM', 'shares_per_share': 0.4855, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1949543/0001193125-25-183045.txt'},
    # Closed Feb13; Nasdaq ECA2026-83 confirms last trading Feb13, suspension Feb17. Operational next trading session. https://www.sec.gov/Archives/edgar/data/1412665/0001412665-26-000015.txt
    'MOFG': {'effective_date': '2026-02-17', 'successor_ticker': 'NIC', 'shares_per_share': 0.3175, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1412665/0001412665-26-000015.txt'},
    # Closed Apr17; Nasdaq ECA2026-239 confirms last trading Apr17, suspension Apr20. Operational next trading session. https://www.sec.gov/Archives/edgar/data/1053352/0001193125-26-167257.txt
    'HTBK': {'effective_date': '2026-04-20', 'successor_ticker': 'CVBF', 'shares_per_share': 0.65, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1053352/0001193125-26-167257.txt'},

    'MMC': {'effective_date': '2026-01-14', 'successor_ticker': 'MRSH', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.marsh.com/en/corp/about/news/marsh-mclennan-to-change-nyse-symbol-to-mrsh.html'},
    'NEP': {'effective_date': '2025-02-03', 'successor_ticker': 'XIFR', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.investor.nexteraenergypartners.com/~/media/Files/N/NEP-IR/news-and-events/News%20Release/2025-0123%20NEP%20name%20change%20PR%20vfinal.pdf'},
    'UCBI': {'effective_date': '2024-08-06', 'successor_ticker': 'UCB', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/857855/000085785524000051/ucbi-20240726.htm'},
    'CNHI': {'effective_date': '2024-05-20', 'successor_ticker': 'CNH', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://investors.cnh.com/news/news-details/2024/CNH-is-changing-its-NYSE-ticker-symbol-to-CNH-on-May-20-05-01-2024/default.aspx'},
    'FIHL': {'effective_date': '2026-05-12', 'successor_ticker': 'PLGO', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1636639/000162828026034096/pressrelease-plgocommencem.htm'},
    'CVGW': {'effective_date': '2026-05-28', 'successor_ticker': 'AVO', 'shares_per_share': 0.979, 'cash_per_share': 14.85, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-355'},
    # Exchange confirms completed merger before open and common-share consideration.
    'CYBR': {'effective_date': '2026-02-11', 'successor_ticker': 'PANW', 'shares_per_share': 2.2005, 'cash_per_share': 45.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-84'},
    # Exchange confirms completed merger before open and common-share consideration.
    'AMWD': {'effective_date': '2026-05-28', 'successor_ticker': 'MBC', 'shares_per_share': 5.15, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-358'},
    # 
    'SJW': {'effective_date': '2025-05-06', 'successor_ticker': 'HTO', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.globenewswire.com/news-release/2025/05/06/3075097/0/en/sjw-group-rebrands-as-h2o-america.html'},
    # https://www.sec.gov/Archives/edgar/data/1095073/000109507323000039/eg-20230630.htm
    'RE': {'effective_date': '2023-07-10', 'successor_ticker': 'EG', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.everestglobal.com/us-en/news-media/press-releases/2023/everest-re-group-to-hold-second-quarter-2023-earnings-conference-call'},
    # 
    'BSIG': {'effective_date': '2025-01-02', 'successor_ticker': 'AAMI', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1748824/000174882425000016/aami-20241231.htm'},
    # https://infomemo.theocc.com/infomemos?number=55593
    'MRO': {'effective_date': '2024-11-22', 'successor_ticker': 'COP', 'shares_per_share': 0.255, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/101778/0001104659-24-122113.txt'},
    # Verified original common-share consideration; original/successor paired basis still required.
    'PCH': {'effective_date': '2026-02-02', 'successor_ticker': 'RYN', 'shares_per_share': 1.8185, 'cash_per_share': 0.61, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1338749/0001193125-26-032108.txt'},
    # Verified original common-share consideration; original/successor paired basis still required.
    'ALCC': {'effective_date': '2024-05-10', 'successor_ticker': 'OKLO', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1849056/000110465924060634/tm2414092d1_8k.htm'},
    # Same company common shares; completed corporate name/ticker rebranding.
    # https://www.sec.gov/Archives/edgar/data/1840572/000162828024051278/bowl-20241212.htm
    'BOWL': {'effective_date': '2024-12-12', 'successor_ticker': 'LUCK', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1840572/000162828024051278/bowl-20241212.htm'},
    # Same Class A company shares, name/ticker change; date explicit in 10-Q.
    # https://www.sec.gov/Archives/edgar/data/1781755/000178175524000030/brp-20240331.htm
    'BRP': {'effective_date': '2024-05-20', 'successor_ticker': 'BWIN', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1781755/000178175524000030/brp-20240331.htm'},
    # Common shares remain listed; CUSIP unchanged.
    # https://investors.gapinc.com/press-releases/news-details/2024/Gap-Inc.-To-Change-Ticker-Symbol-to-GAP-on-August-22-To-Report-Second-Quarter-Fiscal-2024-Results-on-August-29/default.aspx
    'GPS': {'effective_date': '2024-08-22', 'successor_ticker': 'GAP', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://investors.gapinc.com/press-releases/news-details/2024/Gap-Inc.-To-Change-Ticker-Symbol-to-GAP-on-August-22-To-Report-Second-Quarter-Fiscal-2024-Results-on-August-29/default.aspx'},
    # NYSE Class A same CUSIP; not ASX January 22.
    # https://investors.block.xyz/investor-news/news-details/2025/Block-Announces-Ticker-Symbol-Change-to-XYZ-To-Report-Fourth-Quarter-Results/default.aspx
    'SQ': {'effective_date': '2025-01-21', 'successor_ticker': 'XYZ', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://investors.block.xyz/investor-news/news-details/2025/Block-Announces-Ticker-Symbol-Change-to-XYZ-To-Report-Fourth-Quarter-Results/default.aspx'},
    # Legal merger August 31; Nasdaq suspension before September 2 opening; common shares .9150, cash fractions unpriced.
    # https://www.columbiabankingsystem.com/news-market-data/press-releases/press-release/2025/Columbia-Banking-System-Completes-Acquisition-of-Pacific-Premier-Bancorp-and-Unifies-Columbia-Brand/default.aspx
    'PPBI': {'effective_date': '2025-09-02', 'successor_ticker': 'COLB', 'shares_per_share': 0.915, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.columbiabankingsystem.com/news-market-data/press-releases/press-release/2025/Columbia-Banking-System-Completes-Acquisition-of-Pacific-Premier-Bancorp-and-Unifies-Columbia-Brand/default.aspx'},
    # Same acquirer common shares; company name/ticker change, not Marel offer ratio.
    # https://ir.jbtmarel.com/sec-filings/all-sec-filings/content/0001193125-25-002636/d919143d8k.htm
    'JBT': {'effective_date': '2025-01-03', 'successor_ticker': 'JBTM', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://ir.jbtmarel.com/sec-filings/all-sec-filings/content/0001193125-25-002636/d919143d8k.htm'},
    # https://www.sec.gov/Archives/edgar/data/1813814/0001193125-26-009854.txt
    # Common share CUSIP unchanged; market open January 13 explicitly.
    'MNMD': {'effective_date': '2026-01-13', 'successor_ticker': 'DFTX', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1813814/0001193125-26-009854.txt'},
    # https://www.sec.gov/Archives/edgar/data/57515/0000057515-25-000013.txt
    # CUSIP 513847103 unchanged; common stock rights unchanged.
    'LANC': {'effective_date': '2025-07-01', 'successor_ticker': 'MZTI', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/57515/0000057515-25-000013.txt'},
    # https://www.sec.gov/Archives/edgar/data/895126/0001104659-24-104976.txt
    # Acquirer Chesapeake own existing common shares; NOT Southwestern exchange ratio. Trading EXE October 2 explicitly.
    'CHK': {'effective_date': '2024-10-02', 'successor_ticker': 'EXE', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/895126/0001104659-24-104976.txt'},
    # https://www.sec.gov/Archives/edgar/data/1130713/0001140361-23-051490.txt
    # Name change effective November 6; stockholder rights unchanged; BYON filing header.
    'OSTK': {'effective_date': '2023-11-06', 'successor_ticker': 'BYON', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1130713/0001140361-23-051490.txt'},
    # Verified completed common-security terms: https://www.sec.gov/Archives/edgar/data/1865187/0001193125-25-240243.txt
    # Documented non-election default is .625 WES, not elective cash or mixed terms.
    'ARIS': {'effective_date': '2025-10-15', 'successor_ticker': 'WES', 'shares_per_share': 0.625, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1865187/0001193125-25-240243.txt'},
    # Verified completed common-security terms: https://www.sec.gov/Archives/edgar/data/1618563/0001104659-26-085888.txt
    # Common shares only; suspended before NYSE opening.
    'NSA': {'effective_date': '2026-07-22', 'successor_ticker': 'PSA', 'shares_per_share': 0.14, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1618563/0001104659-26-085888.txt'},
    # Verified completed common-security terms: https://www.sec.gov/Archives/edgar/data/1364885/0001104659-25-119096.txt
    # Common stock conversion; excludes Airbus asset-sale proceeds.
    'SPR': {'effective_date': '2025-12-08', 'successor_ticker': 'BA', 'shares_per_share': 0.1955, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1364885/0001104659-25-119096.txt'},
    # Verified completed common-security terms: https://www.sec.gov/Archives/edgar/data/4447/0000950142-25-001950.txt
    # NYSE suspended before July 18 opening.
    'HES': {'effective_date': '2025-07-18', 'successor_ticker': 'CVX', 'shares_per_share': 1.025, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/4447/0000950142-25-001950.txt'},
    # Verified completed common-security terms: https://www.sec.gov/Archives/edgar/data/933136/0000950142-25-002623.txt
    # Nasdaq suspended before October 1 opening.
    'COOP': {'effective_date': '2025-10-01', 'successor_ticker': 'RKT', 'shares_per_share': 11, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/933136/0000950142-25-002623.txt'},
    # Verified completed common-security terms: https://www.sec.gov/Archives/edgar/data/10254/0001193125-23-270505.txt
    # NYSE ceased before November 1 opening.
    'ESTE': {'effective_date': '2023-11-01', 'successor_ticker': 'PR', 'shares_per_share': 1.446, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/10254/0001193125-23-270505.txt'},
    # Verified completed common-security terms: https://www.sec.gov/Archives/edgar/data/1110805/0001193125-24-130840.txt
    # Common units only, not preferred units.
    'NS': {'effective_date': '2024-05-03', 'successor_ticker': 'SUN', 'shares_per_share': 0.4, 'cash_per_share': 0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1110805/0001193125-24-130840.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1742924/0001140361-24-000581.txt
    'LTHM': {'effective_date': '2024-01-04', 'successor_ticker': 'ALTM', 'shares_per_share': 2.406, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1742924/0001140361-24-000581.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1339605/0001193125-25-133372.txt
    'HEES': {'effective_date': '2025-06-02', 'successor_ticker': 'HRI', 'shares_per_share': 0.1287, 'cash_per_share': 78.75, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1339605/0001193125-25-133372.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/858470/0001104659-26-057278.txt
    'CTRA': {'effective_date': '2026-05-07', 'successor_ticker': 'DVN', 'shares_per_share': 0.7, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/858470/0001104659-26-057278.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1126975/0001213900-23-079220.txt
    'MMP': {'effective_date': '2023-09-25', 'successor_ticker': 'OKE', 'shares_per_share': 0.667, 'cash_per_share': 25.0, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1126975/0001213900-23-079220.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/945764/0000945764-23-000140.txt
    'DEN': {'effective_date': '2023-11-02', 'successor_ticker': 'XOM', 'shares_per_share': 0.84, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/945764/0000945764-23-000140.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/949039/0001193125-24-212705.txt
    'DO': {'effective_date': '2024-09-04', 'successor_ticker': 'NE', 'shares_per_share': 0.2316, 'cash_per_share': 5.65, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/949039/0001193125-24-212705.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/51644/0001193125-25-300704.txt
    # Legal date 2025-11-26; first retired session 2025-11-28.
    'IPG': {'effective_date': '2025-11-28', 'successor_ticker': 'OMC', 'shares_per_share': 0.344, 'cash_per_share': 0.0, 'reason': 'STOCK_MERGER', 'execution': 'successor-market', 'source_url': 'https://www.sec.gov/Archives/edgar/data/51644/0001193125-25-300704.txt'},
    # Verified completed action: https://www.sec.gov/Archives/edgar/data/1743907/0001140361-26-021071.txt
    'SNCY': {'effective_date': '2026-05-13', 'successor_ticker': 'ALGT', 'shares_per_share': 0.1557, 'cash_per_share': 4.1, 'reason': 'STOCK_CASH_MERGER', 'execution': 'successor-market-plus-cash', 'source_url': 'https://www.sec.gov/Archives/edgar/data/1743907/0001140361-26-021071.txt'},
    # Verified completed action: https://infomemo.theocc.com/infomemos?number=52179
    'SIVB': {'effective_date': '2023-03-28', 'successor_ticker': 'SIVBQ', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://infomemo.theocc.com/infomemos?number=52179'},
    # Verified completed action: https://infomemo.theocc.com/infomemos?number=52352
    'FRC': {'effective_date': '2023-05-03', 'successor_ticker': 'FRCB', 'shares_per_share': 1.0, 'cash_per_share': 0.0, 'reason': 'SYMBOL_CHANGE', 'execution': 'successor-market', 'source_url': 'https://infomemo.theocc.com/infomemos?number=52352'},
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


# Primary sources: audit_evidence/action_batch_20261012_symbols.json.
# Validation-only terms; paired prices and dated issuer checks remain required.
STOCK_SETTLEMENTS.update({'BK': {'effective_date': '2026-05-21',
        'successor_ticker': 'BNY',
        'shares_per_share': 1.0,
        'cash_per_share': 0.0,
        'reason': 'SYMBOL_CHANGE',
        'execution': 'successor-market'},
 'EQR': {'effective_date': '2026-08-18',
         'successor_ticker': 'VMRK',
         'shares_per_share': 1.0,
         'cash_per_share': 0.0,
         'reason': 'SYMBOL_CHANGE',
         'execution': 'successor-market'},
 'LC': {'effective_date': '2026-06-22',
        'successor_ticker': 'HAPN',
        'shares_per_share': 1.0,
        'cash_per_share': 0.0,
        'reason': 'SYMBOL_CHANGE',
        'execution': 'successor-market'},
 'MEG': {'effective_date': '2026-05-04',
         'successor_ticker': 'ONT',
         'shares_per_share': 1.0,
         'cash_per_share': 0.0,
         'reason': 'SYMBOL_CHANGE',
         'execution': 'successor-market'},
 'VSCO': {'effective_date': '2026-06-02',
          'successor_ticker': 'VSXY',
          'shares_per_share': 1.0,
          'cash_per_share': 0.0,
          'reason': 'SYMBOL_CHANGE',
          'execution': 'successor-market'},
 'SATS': {'effective_date': '2026-06-24',
          'successor_ticker': 'ECHO',
          'shares_per_share': 1.0,
          'cash_per_share': 0.0,
          'reason': 'SYMBOL_CHANGE',
          'execution': 'successor-market'},
 'KAR': {'effective_date': '2025-12-26',
         'successor_ticker': 'OPLN',
         'shares_per_share': 1.0,
         'cash_per_share': 0.0,
         'reason': 'SYMBOL_CHANGE',
         'execution': 'successor-market'},
 'CWEN.A': {'effective_date': '2026-05-01',
            'successor_ticker': 'CWEN',
            'shares_per_share': 1.0,
            'cash_per_share': 0.0,
            'reason': 'CLASS_CONVERSION',
            'execution': 'successor-market'},
 'FDP': {'effective_date': '2026-06-29',
         'successor_ticker': 'DMC',
         'shares_per_share': 1.0,
         'cash_per_share': 0.0,
         'reason': 'SYMBOL_CHANGE',
         'execution': 'successor-market'},
 'HLX': {'effective_date': '2026-09-02',
         'successor_ticker': 'HOS',
         'shares_per_share': 1.0,
         'cash_per_share': 0.0,
         'reason': 'STOCK_MERGER',
         'execution': 'successor-market'},
 'TNP': {'effective_date': '2024-07-01',
         'successor_ticker': 'TEN',
         'shares_per_share': 1.0,
         'cash_per_share': 0.0,
         'reason': 'SYMBOL_CHANGE',
         'execution': 'successor-market'}})

# Primary sources and non-election details: audit_evidence/action_batch_20261012_terms.json.
STOCK_SETTLEMENTS.update({'ENFN': {'effective_date': '2025-04-21',
          'successor_ticker': 'CWAN',
          'shares_per_share': 0.4676,
          'cash_per_share': 0,
          'reason': 'STOCK_MERGER',
          'execution': 'successor-market'},
 'PARA': {'effective_date': '2025-08-07',
          'successor_ticker': 'PSKY',
          'shares_per_share': 1,
          'cash_per_share': 0,
          'reason': 'STOCK_MERGER',
          'execution': 'successor-market'},
 'ERF': {'effective_date': '2024-05-31',
         'successor_ticker': 'CHRD',
         'shares_per_share': 0.10125,
         'cash_per_share': 1.84,
         'reason': 'STOCK_CASH_MERGER',
         'execution': 'successor-market-plus-cash'},
 'CADE': {'effective_date': '2026-02-02',
          'successor_ticker': 'HBAN',
          'shares_per_share': 2.475,
          'cash_per_share': 0,
          'reason': 'STOCK_MERGER',
          'execution': 'successor-market'},
 'REVG': {'effective_date': '2026-02-02',
          'successor_ticker': 'TEX',
          'shares_per_share': 0.9809,
          'cash_per_share': 8.71,
          'reason': 'STOCK_CASH_MERGER',
          'execution': 'successor-market-plus-cash'},
 'PRMW': {'effective_date': '2024-11-11',
          'successor_ticker': 'PRMB',
          'shares_per_share': 1,
          'cash_per_share': 0,
          'reason': 'STOCK_MERGER',
          'execution': 'successor-market'},
 'SBOW': {'effective_date': '2024-07-30',
          'successor_ticker': 'CRGY',
          'shares_per_share': 3.125,
          'cash_per_share': 0,
          'reason': 'STOCK_MERGER',
          'execution': 'successor-market'}})
CASH_SETTLEMENTS.update({'VMW': ('2023-11-22', 142.5)})

# Source-reviewed dated and final terms; validation only, no execution approval.
# audit_evidence/action_batch_20261012_dated.json and action_batch_20261012_final_terms.json
STOCK_SETTLEMENTS.update({
    "DOC": {
        "effective_date": "2024-03-01",
        "successor_ticker": "PEAK",
        "shares_per_share": 0.674,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market",
        "reintroduced_date": "2024-03-04"
    },
    "PEAK": {
        "effective_date": "2024-03-04",
        "successor_ticker": "DOC",
        "shares_per_share": 1,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "FI": {
        "effective_date": "2025-11-11",
        "successor_ticker": "FISV",
        "shares_per_share": 1,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "GOLD": {
        "effective_date": "2025-05-09",
        "successor_ticker": "B",
        "shares_per_share": 1,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "AVB": {
        "effective_date": "2026-08-17",
        "successor_ticker": "EQR",
        "shares_per_share": 2.793,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "ISSC": {
        "effective_date": "2026-08-18",
        "successor_ticker": "IA",
        "shares_per_share": 1,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "LNW": {
        "effective_date": "2025-11-13",
        "successor_ticker": "LNWO",
        "shares_per_share": 1,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "TRTN": {
        "effective_date": "2023-09-28",
        "successor_ticker": "BIPC",
        "shares_per_share": 0.758545,
        "cash_per_share": 54.61096,
        "reason": "STOCK_CASH_MERGER",
        "execution": "successor-market-plus-cash"
    },
    "BLD": {
        "effective_date": "2026-07-01",
        "successor_ticker": "QXO",
        "shares_per_share": 20.2,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "CEPT": {
        "effective_date": "2026-07-02",
        "successor_ticker": "SECZ",
        "shares_per_share": 1,
        "cash_per_share": 0,
        "reason": "STOCK_MERGER",
        "execution": "successor-market"
    },
    "IGT": {
        "effective_date": "2025-07-02",
        "successor_ticker": "BRSL",
        "shares_per_share": 1,
        "cash_per_share": 0,
        "reason": "SYMBOL_CHANGE",
        "execution": "successor-market"
    },
    "MAG": {
        "effective_date": "2025-09-04",
        "successor_ticker": "PAAS",
        "shares_per_share": 0.58844257,
        "cash_per_share": 4.52847757,
        "reason": "STOCK_CASH_MERGER",
        "execution": "successor-market-plus-cash"
    }
})
STOCK_SETTLEMENTS["FISV"]["reintroduced_date"] = "2025-11-11"
CASH_SETTLEMENTS.update({"MTAL": ("2025-10-24", 12.25), "B": ("2025-01-27", 47.5)})




def install_verified_exit_data(engine):
    for ticker, (effective_date, cash_per_share) in CASH_SETTLEMENTS.items():
        engine.CASH_CORPORATE_ACTIONS[ticker] = {
            "effective_date": effective_date,
            "cash_per_share": cash_per_share,
            "reason": "CASH_MERGER",
            "execution": "cash-settlement",
        }
    engine.CASH_CORPORATE_ACTIONS["B"]["reintroduced_date"] = "2025-05-09"
    engine.STOCK_CORPORATE_ACTIONS.update(STOCK_SETTLEMENTS)




import backtest_momentum_v3 as _engine
install_verified_exit_data(_engine)
