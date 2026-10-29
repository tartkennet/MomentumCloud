"""Research-only mixed consideration, spin-off and confirmed halt accounting.

Frozen Core/paper code is not modified. A halt mark is a valuation, NEVER an
executable quote. Only the explicitly documented PLYA session is permitted.
"""
import copy
from momentum_core import CONFIG, DataBlocked, Ledger, number

STOCK_COMPLETIONS = {
    'AEL': {'effective_date': '2024-05-03', 'completion_date': '2024-05-02',
            'successor_ticker': 'BAM', 'shares_per_share': .45464, 'cash_per_share': 38.85,
            'reason': 'STOCK_CASH_MERGER',
            'source_url': 'https://www.sec.gov/Archives/edgar/data/1039828/000110465924056427/tm2413201d1_8k.htm'},
    'RNA': {'effective_date': '2026-02-26', 'successor_ticker': 'RNAM',
            'shares_per_share': 1., 'reason': 'TICKER_CHANGE',
            'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-89'},
}
CASH_COMPLETIONS = {
    'PLYA': {'effective_date': '2025-06-17', 'cash_per_share': 13.5,
             'source_url': 'https://www.sec.gov/Archives/edgar/data/1692412/000164117225015857/xslSCHEDULE_13D_X01/primary_doc.xml'},
    'RNAM': {'effective_date': '2026-02-27', 'cash_per_share': 72.,
             'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-89'},
}
DISTRIBUTIONS = [{'ex_date': '2026-02-27', 'parent': 'RNAM', 'recipient': 'RNA',
                  'ratio': .1, 'legal_distribution_date': '2026-02-26',
                  'source_url': 'https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-89'}]
HALTS = {'2025-06-16': {'ticker': 'PLYA', 'last_session': '2025-06-13', 'offer_value': 13.5,
         'source_url': 'https://www.sec.gov/Archives/edgar/data/1468174/000110465925058026/tm2517598d1_ex99a5g.htm'}}


def complete_data(data, mark_policy='last_quote'):
    if mark_policy not in ('last_quote', 'offer_value'):
        raise ValueError('Unknown confirmed-halt valuation policy')
    data.source.cash_actions = dict(data.source.cash_actions, **copy.deepcopy(CASH_COMPLETIONS))
    data.cash_actions = copy.deepcopy(data.source.cash_actions)
    data.source.stock_actions = dict(data.source.stock_actions, **copy.deepcopy(STOCK_COMPLETIONS))
    data.distributions = copy.deepcopy(DISTRIBUTIONS)
    data.halt_marks = {}
    for day, event in HALTS.items():
        if day in data.days:
            last = data.bars(event['last_session']).get(event['ticker'])
            if not last or number(last[1]) is None:
                raise DataBlocked('Missing observed pre-suspension PLYA close')
            data.halt_marks[day] = dict(event, value=last[1] if mark_policy == 'last_quote' else event['offer_value'],
                                        policy=mark_policy, observed_market_quote=False)
    return data


class ResearchLedger(Ledger):
    def execute_open(self, data, day, config=CONFIG):
        signal = self.pending['signal_date'] if self.pending else None
        first = len(self.trades)
        super().execute_open(data, day, config)
        for trade in self.trades[first:]:
            if trade['side'] == 'BUY_CANCELLED_NO_OPEN':
                trade['signal_date'] = signal

    def events_before_open(self, data, day):
        # Quantities immediately before the event, after that day's splits.
        quantities = dict(self.shares)
        for e in data.splits:
            if e['execution_date'] == day and e['ticker'] in quantities:
                quantities[e['ticker']] *= e['split_to'] / e['split_from']
        super().events_before_open(data, day)
        for ticker, e in data.stock_actions.items():
            q = quantities.get(ticker, 0)
            if e['effective_date'] == day and q and e.get('cash_per_share'):
                self._cash_claim(day, ticker, q * e['cash_per_share'], e.get('pay_date'), 'STOCK_MERGER_CASH')
                self.trades.append({'date': day, 'ticker': ticker, 'side': 'STOCK_MERGER_CASH_CLAIM',
                                    'quantity': q, 'price': e['cash_per_share'], 'fee': 0.})
        # Nasdaq's ex/due-bill date determines the economic recipient. The
        # previous RNAM close is cum-distribution; RNA first trades on ex-date.
        for e in getattr(data, 'distributions', []):
            q = quantities.get(e['parent'], 0) * e['ratio']
            if e['ex_date'] == day and q:
                self.shares[e['recipient']] = self.shares.get(e['recipient'], 0) + q
                self.trades.append({'date': day, 'ticker': e['recipient'], 'side': 'STOCK_DISTRIBUTION',
                                    'quantity': q, 'price': 0., 'fee': 0., 'parent': e['parent']})

    def close_value(self, data, day):
        mark = getattr(data, 'halt_marks', {}).get(day)
        if not mark or mark['ticker'] not in self.shares:
            return super().close_value(data, day)
        bars = data.bars(day)
        stock = 0.
        for ticker, q in self.shares.items():
            if ticker == mark['ticker']:
                if bars.get(ticker) and number(bars[ticker][1]) is not None:
                    raise DataBlocked('Unexpected quote on the confirmed PLYA suspension date')
                stock += q * mark['value']
            else:
                stock += q * self._price(bars, ticker, 1, day)
        claims = sum(r['amount'] for r in self.receivables)
        return self.cash + stock + claims, stock, claims
