"""Independently attribute the verified fixed selection's realised losses.

No security is removed, no rule is optimised, and no unavailable price is filled.
Dollar contributions follow the actual net-capital path, so their sum reconciles
to the compounded final return rather than summing unweighted stock percentages.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from reverify_selection_archive import verify


def main():
    root = Path(__file__).parent
    archive = root / 'evidence/selection'
    verification = verify(archive)
    model = archive / 'Momentum_verified_gap_model'
    positions = pd.read_csv(model / 'momentum_selection_only_positions.csv')
    months = pd.read_csv(model / 'momentum_selection_only_results.csv').sort_values('SignalDate')
    nav = pd.read_csv(archive / 'independent_daily_nav.csv')
    references = json.loads((archive / 'selection_reference_histories.json').read_text())
    initial = 10000.0
    capital = initial
    capital_by_signal, contributions, fees = {}, [], []
    for month in months.itertuples():
        basket = positions[positions.SignalDate == month.SignalDate]
        assert len(basket) == 15 and abs(float(month.Cost_pct) - .30) < 1e-12
        capital_by_signal[month.SignalDate] = capital
        gross = 0.0
        for position in basket.itertuples():
            allocation = capital / 15.0
            pnl = allocation * (position.ExitPrice_USD / position.EntryPrice_USD - 1.0)
            gross += pnl
            contributions.append({'SignalDate': position.SignalDate, 'Ticker': position.Ticker,
                                  'Rank': int(position.Rank), 'GrossReturn_pct': position.GrossReturn_pct,
                                  'StartAllocation_USD': allocation, 'GrossPnL_USD': pnl,
                                  'Contribution_pct_initial': pnl / initial * 100})
        cost = capital * float(month.Cost_pct) / 100.0
        fees.append({'SignalDate': month.SignalDate, 'Cost_USD': cost})
        capital += gross - cost
        assert np.isclose(capital / initial * 100, month.PortfolioIndex, atol=1e-8)
    contrib = pd.DataFrame(contributions)
    fee_table = pd.DataFrame(fees)
    assert np.isclose(contrib.GrossPnL_USD.sum() - fee_table.Cost_USD.sum(), capital - initial)
    values = np.r_[100.0, nav.nav.to_numpy(dtype=float)]
    dd = values / np.maximum.accumulate(values) - 1
    trough_i = int(np.argmin(dd))
    peak_i = int(np.argmax(values[:trough_i + 1]))
    assert peak_i > 0 and trough_i > 0
    peak, trough = nav.iloc[peak_i - 1], nav.iloc[trough_i - 1]
    window_months = months[(months.SignalDate >= peak.signal) & (months.SignalDate <= trough.signal)]
    window_contributions, window_fees = [], 0.0
    for month in window_months.itertuples():
        basket = positions[positions.SignalDate == month.SignalDate]
        # This observed maximum-drawdown window contains no corporate action.
        # Fail closed if a different archive would require a new valuation path.
        assert basket.CorporateAction.isna().all()
        start_capital = capital_by_signal[month.SignalDate]
        for position in basket.itertuples():
            begin = float(position.EntryPrice_USD)
            end = float(position.ExitPrice_USD)
            if month.SignalDate == peak.signal:
                begin = float(references[position.Ticker]['adjusted'][peak.day]['close'])
            if month.SignalDate == trough.signal:
                end = float(references[position.Ticker]['adjusted'][trough.day]['close'])
            shares = start_capital / 15.0 / position.EntryPrice_USD
            pnl = shares * (end - begin)
            window_contributions.append({'SignalDate': month.SignalDate, 'Ticker': position.Ticker,
                                         'FromValuePrice_USD': begin, 'ToValuePrice_USD': end,
                                         'GrossPnL_USD': pnl})
        if month.SignalDate > peak.signal:
            window_fees += start_capital * float(month.Cost_pct) / 100.0
    window = pd.DataFrame(window_contributions)
    expected_loss = (trough.nav - peak.nav) / 100 * initial
    assert np.isclose(window.GrossPnL_USD.sum() - window_fees, expected_loss, atol=1e-7)
    total_ticker = contrib.groupby('Ticker').GrossPnL_USD.sum().sort_values()
    window_ticker = window.groupby('Ticker').GrossPnL_USD.sum().sort_values()
    # These are descriptions of the observed portfolio, not filtered reruns.
    gross_compounded = float(((1 + months.GrossReturn_pct / 100).prod() - 1) * 100)
    stock_loss = -float(window.loc[window.GrossPnL_USD < 0, 'GrossPnL_USD'].sum())
    stock_gains = float(window.loc[window.GrossPnL_USD > 0, 'GrossPnL_USD'].sum())
    worst10 = window_ticker.head(10)
    concentration = -float(worst10.sum()) / stock_loss * 100
    outcome = {
        'status': 'PASS_INDEPENDENT_OBSERVED_LOSS_ATTRIBUTION',
        'archive_verification': verification,
        'positions': len(positions), 'months': len(months),
        'initial_capital_USD': initial, 'final_capital_USD': capital,
        'net_return_pct': (capital / initial - 1) * 100,
        'gross_compounded_return_pct': gross_compounded,
        'fixed_cost_impact_on_compounded_return_pp': gross_compounded - (capital / initial - 1) * 100,
        'gross_stock_pnl_on_net_capital_path_USD': float(contrib.GrossPnL_USD.sum()),
        'direct_fixed_fees_USD': float(fee_table.Cost_USD.sum()),
        'peak_to_trough': {
            'peak_date': peak.day, 'peak_nav': float(peak.nav),
            'trough_date': trough.day, 'trough_nav': float(trough.nav),
            'drawdown_pct': float(dd[trough_i] * 100), 'net_loss_USD': expected_loss,
            'gross_stock_loss_USD': stock_loss, 'gross_stock_gains_USD': stock_gains,
            'fixed_fees_after_peak_USD': window_fees,
            'ten_worst_tickers_gross_loss_USD': -float(worst10.sum()),
            'ten_worst_tickers_share_of_gross_losing_positions_pct': concentration,
            'corporate_actions_in_window': 0,
            'worst_ticker_contributions_USD': {str(k): float(v) for k, v in worst10.items()},
            'best_ticker_contributions_USD': {str(k): float(v) for k, v in window_ticker.tail(10).items()},
        },
        'worst_whole_test_ticker_contributions_USD': {str(k): float(v) for k, v in total_ticker.head(10).items()},
        'best_whole_test_ticker_contributions_USD': {str(k): float(v) for k, v in total_ticker.tail(10).items()},
        'mean_monthly_gross_pct': float(months.GrossReturn_pct.mean()),
        'geometric_monthly_gross_pct': float((1 + gross_compounded / 100) ** (1 / len(months)) * 100 - 100),
        'limitations': ['Selection only; eligible-universe ranking benefit remains unproven.',
                        'Fixed monthly charges are not measured live spread/impact costs.',
                        'Price-only scope excludes dividends and unpriced rights.',
                        'These dates and models have already been examined; no fresh holdout is claimed.'],
        'no_security_removed': True, 'no_parameter_optimisation': True,
    }
    out = root / 'audit_evidence'
    contrib.to_csv(out / 'selection_position_pnl_attribution_20261012.csv', index=False)
    fee_table.to_csv(out / 'selection_fixed_fee_attribution_20261012.csv', index=False)
    window.to_csv(out / 'selection_drawdown_pnl_attribution_20261012.csv', index=False)
    (out / 'selection_loss_attribution_20261012.json').write_text(json.dumps(outcome, indent=2, allow_nan=False) + '\n')
    print(json.dumps(outcome, indent=2))


if __name__ == '__main__':
    main()
