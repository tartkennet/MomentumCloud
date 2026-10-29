"""Verified event completions for research only; never alter frozen Core code.

These facts also existed in PR 13. Primary filings were rechecked when the
normalized candidate first exposed SOVO's missing post-merger quote. Actual
broker payment dates remain unknown; use all original payment sensitivities.
"""
import copy

EXTRA_CASH_ACTIONS = {
    'SOVO': {'effective_date': '2024-03-12', 'cash_per_share': 23.0,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/1856608/000110465924033282/tm248409d1_8k.htm'},
    'CBAY': {'effective_date': '2024-03-22', 'cash_per_share': 32.5,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/882095/000110465924037619/tm249475d1_8k.htm'},
    'NWLI': {'effective_date': '2024-07-09', 'cash_per_share': 500.0,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/1635984/000163598424000019/nwli-20240709.htm'},
    'NVEI': {'effective_date': '2024-11-15', 'cash_per_share': 34.0,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/1765159/000095010324016364/dp220747_ex9902.htm'},
    'AXNX': {'effective_date': '2024-11-15', 'cash_per_share': 71.0,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/1603756/000162828024048038/axnx-20241115.htm'},
    'HCP': {'effective_date': '2025-02-27', 'cash_per_share': 35.0,
            'source_url': 'https://www.sec.gov/Archives/edgar/data/1720671/000119312525037910/d898526d8k.htm'},
    'RGLS': {'effective_date': '2025-06-25', 'cash_per_share': 7.0, 'contingent_cash_per_share': 7.0,
             'source_url': 'https://www.novartis.com/news/media-releases/novartis-completes-acquisition-regulus-therapeutics'},
    'ESGR': {'effective_date': '2025-07-02', 'cash_per_share': 338.0,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/1363829/000110465925065337/tm2519642d2_ex99-1.htm'},
    'FYBR': {'effective_date': '2026-01-20', 'cash_per_share': 38.5,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/732712/000119312526016059/d198618d8k.htm'},
    'EXAS': {'effective_date': '2026-03-23', 'cash_per_share': 105.0,
             'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-178'},
    'AL': {'effective_date': '2026-04-08', 'cash_per_share': 65.0,
           'source_url': 'https://www.sec.gov/Archives/edgar/data/1487712/000119312526147571/d139383d8k.htm'},
    'GTLS': {'effective_date': '2026-07-16', 'cash_per_share': 210.0,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/1701605/000170160526000023/bkr-20260630.htm'},
}


def supplement(data):
    actions = copy.deepcopy(data.source.cash_actions)
    if actions.keys() & EXTRA_CASH_ACTIONS.keys():
        raise ValueError('Research event supplement conflicts with original Core facts')
    actions.update(copy.deepcopy(EXTRA_CASH_ACTIONS))
    data.source.cash_actions = actions
    data.cash_actions = copy.deepcopy(actions)
    return data
