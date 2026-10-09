"""Verify archived audit outputs without network calls or model reruns."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def verify(root):
    manifest = json.loads((root / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError('Evidence hash mismatch: ' + name)
    model_dir = root / 'Momentum_verified_gap_model'
    pos = pd.read_csv(model_dir / 'momentum_selection_only_positions.csv')
    results = pd.read_csv(model_dir / 'momentum_selection_only_results.csv')
    record = json.loads((model_dir / 'momentum_selection_only_model_result.json').read_text())
    prices = pd.read_csv(root / 'selection_price_audit.csv')
    identities = pd.read_csv(root / 'selection_issuer_identity_audit.csv', dtype={'CIK': str})
    nav = pd.read_csv(root / 'independent_daily_nav.csv')
    if len(pos) != 645 or len(results) != 43 or len(prices) != 1935 or len(nav) != 943:
        raise ValueError('Unexpected archived coverage')
    if pos.duplicated(['SignalDate', 'Ticker']).any():
        raise ValueError('Duplicate positions')
    if not (pos.groupby('SignalDate').size() == 15).all():
        raise ValueError('Unexpected basket weights')
    if not prices['pass'].all() or not identities.Matched.all() or identities.CIK.isna().any():
        raise ValueError('Failed price or identity checks')
    if len(identities) != 645 or identities.duplicated(['SignalDate', 'Ticker']).any():
        raise ValueError('Identity coverage mismatch')
    fields = {'signal': 'SignalPrice_USD', 'entry': 'EntryPrice_USD', 'exit': 'ExitPrice_USD'}
    keyed = pos.set_index(['SignalDate', 'Ticker'])
    for row in prices.itertuples():
        model_price = float(keyed.loc[(row.signal, row.ticker), fields[row.field]])
        if not np.isfinite(model_price) or model_price <= 0:
            raise ValueError('Invalid position price')
        if not np.isclose(model_price, row.model_price, rtol=1e-10, atol=1e-10):
            raise ValueError('Archived model price mismatch')
        if not np.isclose(model_price, row.reference_price, rtol=1e-6, atol=1e-8):
            raise ValueError('Individual reference price mismatch')
    gross = (pos.ExitPrice_USD / pos.EntryPrice_USD - 1) * 100
    if not np.allclose(gross, pos.GrossReturn_pct, rtol=1e-10, atol=1e-10):
        raise ValueError('Position return mismatch')
    monthly = pos.assign(verified_gross=gross).groupby('SignalDate').verified_gross.mean()
    net_return = float(((1 + (monthly - .30) / 100).prod() - 1) * 100)
    gross_return = float(((1 + monthly / 100).prod() - 1) * 100)
    spy_return = float(((1 + (results.SPYReturn_pct - .30) / 100).prod() - 1) * 100)
    values = np.r_[100., nav.nav.to_numpy(dtype=float)]
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError('Invalid daily NAV')
    drawdown = float((values / np.maximum.accumulate(values) - 1).min() * 100)
    if not np.isclose(net_return, record['metrics']['TotalReturn_pct'], atol=1e-9):
        raise ValueError('Independent basket aggregation mismatch')
    if not np.isclose(drawdown, record['metrics']['DailyMaxDrawdown_pct'], atol=1e-9):
        raise ValueError('Independent drawdown mismatch')
    if not np.isclose((values[-1] / 100 - 1) * 100, net_return, atol=1e-9):
        raise ValueError('Daily NAV terminal mismatch')
    return dict(status='PASS_ARCHIVED_SELECTION_ONLY', positions=len(pos),
                tickers=int(pos.Ticker.nunique()), periods=len(results),
                price_checks=len(prices), identity_checks=len(identities),
                nav_points=len(nav), net_return_pct=net_return,
                gross_return_pct=gross_return, spy_matched_cost_pct=spy_return,
                daily_drawdown_pct=drawdown, full_universe_complete=False,
                limitation='Reverifies archived observations; does not rerun selection or prove ranking benefit.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.root), indent=2))
