"""Dated economic business classification and fail-closed original-event review."""
import hashlib
import json
import re
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from zoneinfo import ZoneInfo
from quality_sources import DataUnavailable,iso_date
from quality_forward import digest
from momentum_core_data import atomic_json,read_json

NY=ZoneInfo('America/New_York')

def classify(profile):
    """Economic taxonomy from business evidence plus detailed SIC; not GICS."""
    text=(profile.get('description') or '').lower();sic=int(profile.get('sic_code') or 0)
    if len(text)<40:raise DataUnavailable('ECONOMIC_BUSINESS_DESCRIPTION_MISSING')
    health=r'healthcare|health care|medical|musculoskeletal|pharmaceut|biotech|therapeutic|diagnostic|life.scien|patient'
    if re.search(health,text) or 2830<=sic<=2839 or 3840<=sic<=3859 or 8000<=sic<=8099:sector='Healthcare'
    elif 1300<=sic<=1399 or 2900<=sic<=2999 or 5170<=sic<=5179:sector='Energy'
    elif sic==6798 or 6500<=sic<=6599:sector='Real Estate'
    elif 6000<=sic<=6499 or 6700<=sic<=6799:sector='Financials'
    elif 4900<=sic<=4999:sector='Utilities'
    elif 3570<=sic<=3579 or 3670<=sic<=3679 or 7370<=sic<=7379 or sic in (3661,3663,3825,5045):sector='Technology'
    elif 4800<=sic<=4899 or 7310<=sic<=7319 or 7810<=sic<=7849:sector='Communication Services'
    elif 1000<=sic<=1299 or 1400<=sic<=1499 or 2600<=sic<=2699 or 2800<=sic<=2829 or 2840<=sic<=2899 or 3300<=sic<=3399 or sic in (5110,5111,5160,5169):sector='Materials'
    elif 100<=sic<=999 or 2000<=sic<=2199 or 5400<=sic<=5499 or 5140<=sic<=5159:sector='Consumer Staples'
    elif 1500<=sic<=1799 or 3200<=sic<=3599 or 3720<=sic<=3729 or 3760<=sic<=3769 or 4000<=sic<=4799 or 5000<=sic<=5099 or 7300<=sic<=7369 or 8700<=sic<=8799:sector='Industrials'
    elif 2200<=sic<=2599 or 3000<=sic<=3199 or 3630<=sic<=3659 or 3700<=sic<=3719 or 3900<=sic<=3999 or 5200<=sic<=5999 or 7000<=sic<=7299 or 7900<=sic<=7999 or 8200<=sic<=8299:sector='Consumer Discretionary'
    else:raise DataUnavailable('ECONOMIC_SECTOR_UNRESOLVED')
    factor=('Growth/technology' if sector in ('Technology','Communication Services') else
            'Rate sensitive' if sector in ('Financials','Real Estate','Utilities') else sector)
    return dict(sector=sector,factor=factor,classification_method='BUSINESS_ACTIVITY_AND_DETAILED_SIC_V2',
        business_sha256=hashlib.sha256(text.encode()).hexdigest(),healthcare_exposure=sector=='Healthcare')


def raw_document(client,url):
    p=urlparse(url)
    if p.hostname not in ('api.massive.com','api.polygon.io') or p.query or not p.path.startswith('/v1/reference/sec/filings/'):
        raise DataUnavailable('UNTRUSTED_ORIGINAL_DOCUMENT_PATH')
    response=client.session.get('https://api.polygon.io'+p.path,params={'apiKey':client.key},timeout=(5,20))
    if response.status_code!=200:raise DataUnavailable('ORIGINAL_DOCUMENT_HTTP_'+str(response.status_code))
    if len(response.content)>20_000_000:raise DataUnavailable('OVERSIZE_ORIGINAL_DOCUMENT')
    return response.content


def event_text(text):
    """Conservative signal: ambiguous contracts require review, never auto-clear."""
    t=re.sub('<[^>]+>',' ',text.lower());t=re.sub(r'\s+',' ',t)
    bindings=[r'definitive (?:merger |acquisition )?agreement',r'agreement and plan of merger',r'all.cash (?:transaction|acquisition|merger)',r'cash tender offer',r'plan of liquidation',r'going.private transaction']
    return any(re.search(p,t) for p in bindings)


def filings(client,ticker,start,cutoff):
    rows=[];params={'entities.company_data.ticker':ticker,'filing_date.gte':start,'filing_date.lte':cutoff,
                   'sort':'filing_date','order':'desc','limit':100}
    path='/v1/reference/sec/filings';seen=set()
    while True:
        body=client.get(path,params);rows.extend(body.get('results',[]))
        nxt=body.get('next_url')
        if not nxt:break
        p=urlparse(nxt)
        if p.hostname not in ('api.massive.com','api.polygon.io') or p.path!='/v1/reference/sec/filings':raise DataUnavailable('UNTRUSTED_FILINGS_PAGE')
        params={k:v[0] for k,v in parse_qs(p.query).items() if k!='apiKey'};path=p.path
        key=digest(params)
        if key in seen:raise DataUnavailable('REPEATED_FILINGS_PAGE')
        seen.add(key)
    return rows


def reference(row,day,root,client,decision_at):
    """Never interprets a financially restricted SEC feed as full event coverage."""
    decision=datetime.fromisoformat(decision_at);date=decision.astimezone(NY).date().isoformat()
    path=Path(root)/'best-v2-reference'/date/(row['ticker']+'.json')
    if path.exists():receipt=read_json(path)
    else:
        profile=client.get('/v3/reference/tickers/'+row['ticker'],{'date':date})['results']
        if profile.get('ticker')!=row['ticker'] or str(profile.get('cik','')).zfill(10)!=row['cik'] or profile.get('type')!='CS':raise DataUnavailable('V2_REFERENCE_IDENTITY_MISMATCH')
        observed=datetime.now(timezone.utc).isoformat()
        start=(decision.astimezone(NY).date()-timedelta(days=400)).isoformat()
        entries=filings(client,row['ticker'],start,date)
        # A financials-only feed can omit publicly known 8-K announcements.
        # Require independently corroborated form coverage before CLEAR.
        annual=[r for r in entries if r.get('type') in ('10-K','20-F','40-F')]
        events=[r for r in entries if r.get('type') in ('8-K','6-K','425','SC TO-T','SC 14D9','DEFM14A')]
        receipt=dict(ticker=row['ticker'],cik=row['cik'],price_date=day,decision_date=date,observed_at=observed,
            profile={k:profile.get(k) for k in ('ticker','cik','type','description','sic_code','sic_description','name')},
            filings=[{k:r.get(k) for k in ('id','type','filing_date','acceptance_datetime','main_file_url','entities')} for r in entries],
            form_counts={t:sum(r.get('type')==t for r in entries) for t in sorted({r.get('type') for r in entries})},
            event_status='UNVERIFIED_EVENT_FEED_COVERAGE',sources_sha256=digest(entries))
        receipt.update(classify(profile));atomic_json(path,receipt)
        if not annual or not events:raise DataUnavailable('MISSING_NONFINANCIAL_EVENT_COVERAGE_'+row['ticker'])
        # Review originals; positive signals block until dated analyst/event review.
        documents=[]
        for entry in entries:
            if entry.get('type') not in ('10-K','10-Q','20-F','40-F','8-K','6-K','425','SC TO-T','SC 14D9','DEFM14A'):continue
            if not any(e.get('relation')=='filer' and str(e.get('company_data',{}).get('cik','')).zfill(10)==row['cik'] for e in entry.get('entities',[])):raise DataUnavailable('V2_FILING_IDENTITY_MISMATCH')
            raw=raw_document(client,entry['main_file_url'])
            flag=event_text(raw.decode('utf-8',errors='replace'))
            documents.append(dict(id=entry['id'],sha256=hashlib.sha256(raw).hexdigest(),event_language=flag))
        receipt.update(documents=documents,event_status='REVIEW_REQUIRED' if any(x['event_language'] for x in documents) else 'ORIGINALS_REVIEWED')
        # Index completeness is a separate requirement: never certify from presence alone.
        receipt['event_status']='UNVERIFIED_EVENT_FEED_COVERAGE'
        atomic_json(path,receipt)
    if receipt['cik']!=row['cik'] or receipt['decision_date']!=date:raise DataUnavailable('V2_RECEIPT_IDENTITY_MISMATCH')
    if datetime.fromisoformat(receipt['observed_at'])>datetime.now(timezone.utc):raise DataUnavailable('FUTURE_REFERENCE_RECEIPT')
    if receipt.get('event_status')!='CLEAR':raise DataUnavailable('MISSING_NONFINANCIAL_EVENT_COVERAGE_'+row['ticker'])
    return dict(row,**{k:receipt[k] for k in ('sector','factor','healthcare_exposure')},event_status='CLEAR',reference_sha256=digest(receipt))
