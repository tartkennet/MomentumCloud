"""Read full SEC filings for the remaining audit cases; no settlement inference."""
import concurrent.futures
import html
import json
from pathlib import Path
import re
import time

import requests

root = Path('evidence/full_remaining_filings')
root.mkdir(parents=True, exist_ok=True)
left = {x['ticker'] for x in json.loads(Path('audit_evidence/universe_remaining_ledger.json').read_text())
        if not x['reviewed_action_record_available']}
filings = json.loads(Path('evidence/filings.json').read_text())
records = {}
for pair in filings.values():
    if pair['ticker'] not in left:
        continue
    for record in pair.get('primary_filings', {}).get('results', []):
        accession = record['accession_number']
        records.setdefault(accession, {'record': record, 'tickers': set()})['tickers'].add(pair['ticker'])


def fetch(item):
    accession, data = item
    path = root / (accession + '.json')
    if path.exists():
        return json.loads(path.read_text())
    record = data['record']
    cik = str(int(record['cik']))
    url = f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}.txt'
    error = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 MomentumCloud historical audit'}, timeout=25)
            response.raise_for_status()
            docs = re.findall(r'<DOCUMENT>(.*?)</DOCUMENT>', response.text, re.S | re.I)
            first = next((d for d in docs if re.search(r'<TYPE>8-K(?:\s|$)', d)), None)
            if first is None:
                raise ValueError('No primary 8-K document')
            first = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', first, flags=re.S | re.I)
            text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', first))).strip()
            value = dict(accession=accession, cik=cik, filing_date=record['filing_date'],
                         tickers=sorted(data['tickers']), source_url=url, text=text, status='READABLE')
            temporary = path.with_suffix('.tmp')
            temporary.write_text(json.dumps(value))
            temporary.replace(path)
            return value
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)
            if attempt < 2:
                time.sleep(1 + attempt)
    return dict(accession=accession, tickers=sorted(data['tickers']), status='ERROR', error=error)


completed = []
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for result in pool.map(fetch, records.items()):
        completed.append({k: v for k, v in result.items() if k != 'text'})
        if len(completed) % 25 == 0:
            print('Read', len(completed), 'of', len(records), flush=True)
        Path('audit_evidence/full_remaining_filings_manifest.json').write_text(json.dumps(completed, indent=2))
print('COMPLETE', len(completed), 'errors', sum(x['status'] == 'ERROR' for x in completed), flush=True)
