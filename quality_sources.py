"""Bounded, redacted provider access to original SEC filing files, not restated fundamentals."""
import gzip
import hashlib
import json
import os
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlparse
import requests


class DataUnavailable(RuntimeError):pass


class Provider:
    def __init__(self,key=None):self.key=key or os.environ.get('POLYGON_API_KEY');self.session=requests.Session()
    def get(self,path,params=None,xml=False):
        if not self.key:raise DataUnavailable('MISSING_EXISTING_API_KEY')
        if not path.startswith('/'):raise DataUnavailable('INVALID_PROVIDER_PATH')
        try:r=self.session.get('https://api.polygon.io'+path,params=dict(params or {},apiKey=self.key),timeout=(5,20))
        except requests.RequestException as e:raise DataUnavailable('NETWORK_'+type(e).__name__) from None
        if r.status_code!=200:raise DataUnavailable('HTTP_'+str(r.status_code))
        if len(r.content)>20_000_000:raise DataUnavailable('OVERSIZE_FILING')
        if xml:
            if 'xml' not in r.headers.get('content-type','').lower():raise DataUnavailable('NOT_XML')
            return r.content
        try:return r.json()
        except ValueError:raise DataUnavailable('NOT_JSON') from None


def iso_date(value):
    s=str(value)
    if len(s)==8 and s.isdigit():return s[:4]+'-'+s[4:6]+'-'+s[6:]
    return s[:10]


def current_filing(provider,ticker,observed_at):
    choices=[]
    for form in ('10-Q','10-K'):
        payload=provider.get('/v1/reference/sec/filings',{'entities.company_data.ticker':ticker,'type':form,'sort':'filing_date','order':'desc','limit':1})
        choices.extend(payload.get('results',[]))
    if not choices:raise DataUnavailable('NO_ORIGINAL_FILINGS')
    filing=max(choices,key=lambda f:(iso_date(f['filing_date']),str(f['accession_number'])))
    if iso_date(filing['filing_date'])>observed_at[:10]:raise DataUnavailable('FUTURE_FILING')
    if filing['type'] not in ('10-K','10-Q'):raise DataUnavailable('UNSUPPORTED_FORM')
    url=filing.get('xbrl_instance_url')
    if not url:raise DataUnavailable('NO_XBRL_INSTANCE')
    parsed=urlparse(url)
    if parsed.hostname not in ('api.massive.com','api.polygon.io') or parsed.query:raise DataUnavailable('UNTRUSTED_INSTANCE_URL')
    if not parsed.path.startswith('/v1/reference/sec/filings/'+filing['id']+'/files/'):raise DataUnavailable('MISMATCHED_INSTANCE')
    entity=next((e['company_data'] for e in filing['entities'] if e.get('relation')=='filer' and ticker in e.get('company_data',{}).get('tickers',[e.get('company_data',{}).get('ticker')])),None)
    if not entity:raise DataUnavailable('TICKER_FILTER_MISMATCH')
    amendments=provider.get('/stocks/filings/vX/index',{'cik':entity['cik'],'form_type.any_of':'10-K/A,10-Q/A','filing_date.gte':iso_date(filing['filing_date']),'limit':1})
    if amendments.get('results'):raise DataUnavailable('AMENDMENT_REQUIRES_REVIEW')
    filing['amendments_checked_at']=observed_at
    raw=provider.get(parsed.path,xml=True)
    return filing,raw


def save_original(root,filing,raw,observed_at):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);accession=filing['accession_number']
    if any(c not in '0123456789-' for c in accession):raise DataUnavailable('INVALID_ACCESSION')
    digest=hashlib.sha256(raw).hexdigest();stem=accession+'-'+digest[:16]
    prior=list(root.glob(accession+'-*.json'))
    if prior and any(json.loads(p.read_text())['sha256']!=digest for p in prior):raise DataUnavailable('ORIGINAL_ACCESSION_CHANGED')
    if not (root/(stem+'.xml.gz')).exists():
        with gzip.open(root/(stem+'.xml.gz'),'wb') as f:f.write(raw)
    receipt=dict(observed_at=observed_at,filing=filing,sha256=digest,xml_asset=stem+'.xml.gz',source='original SEC XBRL via existing Massive filing-file endpoint')
    if not (root/(stem+'.json')).exists():(root/(stem+'.json')).write_text(json.dumps(receipt,indent=2))
    return receipt


if __name__=='__main__':
    root=Path('quality_originals_output');root.mkdir(exist_ok=True);rows=[];provider=Provider()
    for ticker in ('AAPL','MSFT'):
        now=datetime.now(timezone.utc).isoformat()
        try:
            filing,raw=current_filing(provider,ticker,now);receipt=save_original(root,filing,raw,now)
            rows.append(dict(ticker=ticker,status='AVAILABLE',observed_at=now,bytes=len(raw),accession=filing['accession_number'],filing_date=iso_date(filing['filing_date']),period_end=iso_date(filing['period_of_report_date']),sha256=receipt['sha256']))
        except DataUnavailable as e:rows.append(dict(ticker=ticker,status='BLOCKED',reason=str(e),observed_at=now))
    (root/'probe.json').write_text(json.dumps(dict(sources=rows,history_certified=False,broker_orders_enabled=False),indent=2));print(json.dumps(rows,indent=2))
