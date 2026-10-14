"""Value observed stock distributions without changing formation histories.

This audit-only installer handles NCR's two market-priced stock components.
It preserves the fixed requested exit date. Fractional cash-in-lieu is not
invented; prices use the audit's existing continuous share-unit convention.
"""
from datetime import datetime, timezone
from audit_corporate_action_basis import adjustment_factor, convert_stock_row

NCR_ACTION = {
    'effective_date': '2023-10-17',
    'legal_effective_date': '2023-10-16T17:00:00-04:00',
    'successor_ticker': 'VYX', 'shares_per_share': 1.0,
    'cash_per_share': 0.0, 'reason': 'STOCK_DISTRIBUTION',
    'execution': 'multiple-successor-markets',
    'valuation_ticker': 'VYX+0.5*NATL',
    'original_cik': '70866',
    'valuation_legs': [{'ticker': 'VYX', 'shares_per_share': 1.0, 'cik': '70866'},
                       {'ticker': 'NATL', 'shares_per_share': 0.5, 'cik': '1974138'}],
    'source_url': 'https://www.sec.gov/Archives/edgar/data/70866/0001193125-23-257806.txt',
    'completion_source_url': 'https://investor.ncr.com/news-releases/news-release-details/ncr-voyix-corporation-announces-completion-spin-ncr-atleos',
    'ex_distribution_source_url': 'https://infomemo.theocc.com/infomemos?number=53285',
    'unpriced_fractional_cash': 'Not assigned a guessed value; continuous stock-price units only.',
}


def install_compatible_multileg_actions(engine, paired_factor, observed_histories):
    """Wrap the compatible resolver; missing either exact-day leg stays missing."""
    observed = {}
    for ticker, bases in observed_histories.items():
        for basis, payload in bases.items():
            for bar in payload.get('results', []):
                day = datetime.fromtimestamp(bar['t'] / 1000, timezone.utc).date().isoformat()
                observed[ticker, basis, day] = bar
    engine.STOCK_CORPORATE_ACTIONS['NCR'] = dict(NCR_ACTION)
    original_resolver, original_close = engine.resolve_exit_execution, engine.position_close_on_day

    def composite(cache, day, entry):
        effective = NCR_ACTION['effective_date']
        original_days = [d for d in cache if (entry is None or entry <= d)
                         and d < effective and engine.get_from_map(cache[d], 'NCR')]
        if not original_days:
            raise RuntimeError('No original pre-action basis: NCR ' + effective)
        factor = paired_factor(cache, 'NCR', max(original_days))
        total = {'open': 0.0, 'close': 0.0}
        for leg in NCR_ACTION['valuation_legs']:
            ticker = leg['ticker']
            raw, adjusted = observed.get((ticker, 'false', day)), observed.get((ticker, 'true', day))
            if raw is None or adjusted is None:
                return None
            successor_factor = adjustment_factor(float(adjusted['c']), float(raw['c']))
            row = convert_stock_row({'open': float(adjusted['o']), 'close': float(adjusted['c'])},
                                    leg['shares_per_share'], 0.0, factor, successor_factor)
            for field in total:
                total[field] += row[field]
        return total

    def resolve(cache, days, ticker, target, entry, latest):
        if ticker != 'NCR' or target < NCR_ACTION['effective_date'] or entry >= NCR_ACTION['effective_date']:
            return original_resolver(cache, days, ticker, target, entry, latest)
        if target > latest or target not in days:
            return None, None, None
        row = composite(cache, target, entry)
        if row is None:
            return None, None, None
        return target, row, {**NCR_ACTION, 'basis_validation': 'PAIRED_RAW_ADJUSTED_EACH_LEG'}

    def close(cache, ticker, day, entry=None):
        if ticker != 'NCR' or day < NCR_ACTION['effective_date'] or (entry is not None and entry >= NCR_ACTION['effective_date']):
            return original_close(cache, ticker, day, entry)
        row = composite(cache, day, entry)
        action = {**NCR_ACTION, 'basis_validation': 'PAIRED_RAW_ADJUSTED_EACH_LEG'}
        return (None if row is None else row['close']), action

    engine.resolve_exit_execution, engine.position_close_on_day = resolve, close
