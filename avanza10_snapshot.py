"""Monthly Quality rank and daily marks for the separate Avanza paper planner."""
import math
from datetime import datetime

from quality_forward import NY
from quality_strategy import rank

VERSION = 'avanza10-paper-v1'


def build_snapshot(report, previous=None):
    month = datetime.fromisoformat(report['generated_at']).astimezone(NY).strftime('%Y-%m')
    selection = previous.get('selection') if previous else None
    quote_day = report.get('price_as_of')
    status = report.get('collection_status')
    collected = status in ('PAPER_READY_AWAITING_SESSION', 'RISK_OFF', 'SELECTION_BLOCKED', 'DATA_BLOCKED')
    source_ok = collected and report['status'] != 'COLLECTION_FAILED' and not report.get('errors')
    audited = ((report.get('audits') or {}).get('selection') or {}).get('status') == 'PASS'
    ranked = report.get('candidates', [])
    fx = (report.get('fx') or {}).get('usdsek')
    if (source_ok and quote_day and audited and (report.get('coverage') or 0) >= .90
            and fx and report.get('risk_on') is True and (not selection or selection['month'] < month)):
        eligible = [r for r in ranked if r.get('data_status') == 'VERIFIED']
        selection = dict(month=month, as_of=quote_day, usdsek=fx, observed_at=report['generated_at'], rows=[
            {k: r[k] for k in ('ticker', 'name', 'sic', 'division', 'cik', 'price_usd', 'quality_score')}
            for r in rank(eligible)
        ])
    quotes = {}
    if source_ok:
        locked = {r['ticker']: r['cik'] for r in selection['rows']} if selection else {}
        quotes = {r['ticker']: r['price_usd'] for r in ranked
                  if r['cik'] == locked.get(r['ticker'], r['cik']) and r.get('price_as_of') == quote_day
                  and math.isfinite(r['price_usd']) and r['price_usd'] > 0}
    return dict(version=VERSION, mode='PAPER_ONLY', selection=selection, quotes=quotes,
                quotes_as_of=quote_day, market_verified=bool(source_ok and quote_day),
                selection_verified=bool(source_ok and audited and (report.get('coverage') or 0) >= .90))
