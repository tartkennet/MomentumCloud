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


def target_event(text):
    t=re.sub(r'\s+',' ',re.sub('<[^>]+>',' ',text.lower()))
    if not event_text(t):return False
    return any(re.search(p,t) for p in (
        r'(?:our|the company.s) (?:outstanding )?(?:common stock|shares).{0,180}(?:converted|cancelled|canceled|right to receive).{0,100}(?:cash|\$)',
        r'(?:our|the company.s) (?:stockholders|shareholders).{0,120}(?:receive|entitled).{0,80}(?:cash|\$)',
        r'(?:we|the company) (?:will be|to be) acquired.{0,200}(?:cash|per share)',
        r'each (?:outstanding )?share of (?:our|the company.s) common stock.{0,200}(?:cash|\$)'))


def pages(client,path,params):
    rows=[];seen=set();base=path
    while True:
        body=client.get(path,params)
        if body.get('status') not in (None,'OK'):raise DataUnavailable('EVENT_PROVIDER_NOT_OK')
        rows.extend(body.get('results',[]));nxt=body.get('next_url')
        if not nxt:break
        p=urlparse(nxt)
        if p.hostname not in ('api.massive.com','api.polygon.io') or p.path!=base:raise DataUnavailable('UNTRUSTED_FILINGS_PAGE')
        params={k:v[0] for k,v in parse_qs(p.query).items() if k!='apiKey'};path=p.path
        key=digest(params)
        if key in seen:raise DataUnavailable('REPEATED_FILINGS_PAGE')
        seen.add(key)
    return rows


def material_original(row,filing,date):
    if '_cache' not in row:raise DataUnavailable('EVENT_TEXT_COVERAGE_GAP')
    from best_v2_mirrors import original
    try:return original(row,filing,row['_cache'],date)
    except DataUnavailable as exc:
        if str(exc)!='NO_VERIFIED_ISSUER_MIRROR':raise
    from supplement_quality_sources import SEC
    raw,meta=SEC(Path(row['_cache'])/'best-v2-sec').get(filing['filing_url'])
    return raw.decode('utf-8',errors='replace'),meta


def review_events(client,row,date):
    start=(datetime.fromisoformat(date)-timedelta(days=400)).date().isoformat()
    index=pages(client,'/stocks/filings/vX/index',dict(cik=row['cik'],**{'filing_date.gte':start,'filing_date.lte':date},limit=1000,sort='filing_date.desc'))
    if not index:raise DataUnavailable('EMPTY_COMPLETE_EVENT_INDEX')
    for x in index:
        if str(x.get('cik','')).zfill(10)!=row['cik'] or not start<=iso_date(x['filing_date'])<=date:raise DataUnavailable('EVENT_INDEX_IDENTITY_OR_DATE')
    required=[x for x in index if x['form_type'] in ('8-K','8-K/A')]
    other=[x for x in index if x['form_type'] in ('6-K','6-K/A','425','SC TO-T','SC 14D9','DEFM14A')]
    texts=pages(client,'/stocks/filings/8-K/vX/text',dict(cik=row['cik'],**{'filing_date.gte':start,'filing_date.lte':date,'form_type.any_of':'8-K,8-K/A'},limit=100,sort='filing_date.desc'))
    mapped={x['accession_number']:x for x in texts}
    missing=[x for x in required if x['accession_number'] not in mapped]
    if missing:
        print('BEST_V2_MISSING_MATERIAL_TEXT',json.dumps(dict(ticker=row['ticker'],missing=[{k:x.get(k) for k in ('accession_number','form_type','filing_date','filing_url')} for x in missing])),flush=True)
    documents=[];warnings=[]
    def keep(accession,text,url,filed,source_receipt=None):
        if not text or len(text)<30:raise DataUnavailable('EMPTY_EVENT_TEXT')
        if filed>date:raise DataUnavailable('FUTURE_EVENT_TEXT')
        flagged=target_event(text)
        documents.append(dict(accession=accession,filing_date=filed,source_url=url,
            text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),event_language=flagged,source_receipt=source_receipt))
        if flagged:warnings.append(accession)
    for x in required:
        if x['accession_number'] not in mapped:
            text,meta=material_original(row,x,date)
            keep(x['accession_number'],text,meta.get('source_url',meta.get('url')),iso_date(x['filing_date']),meta)
            continue
        t=mapped[x['accession_number']]
        if str(t.get('cik','')).zfill(10)!=row['cik'] or iso_date(t['filing_date'])!=iso_date(x['filing_date']):raise DataUnavailable('EVENT_TEXT_IDENTITY_OR_DATE')
        keep(x['accession_number'],t['items_text'],x['filing_url'],iso_date(x['filing_date']))
    # Non-8-K forms require original text, never silent omission of foreign issuers.
    for x in other:
        text,meta=material_original(row,x,date)
        keep(x['accession_number'],text,meta.get('source_url',meta.get('url')),iso_date(x['filing_date']),meta)
    # Read latest annual and interim originals as long-lived pending deal checks.
    financial=pages(client,'/v1/reference/sec/filings',{'entities.company_data.cik':row['cik'],'filing_date.lte':date.replace('-',''),'sort':'filing_date','order':'desc','limit':100})
    matches=[x for x in financial if any(e.get('relation')=='filer' and str(e.get('company_data',{}).get('cik','')).zfill(10)==row['cik'] for e in x.get('entities',[])) and iso_date(x['filing_date'])<=date]
    annual=[x for x in matches if x['type'] in ('10-K','20-F','40-F')]
    interim=[x for x in matches if x['type']=='10-Q']
    if not annual:raise DataUnavailable('NO_ANNUAL_EVENT_BASELINE')
    chosen=[max(annual,key=lambda x:(iso_date(x['filing_date']),x['accession_number']))]
    if interim:chosen.append(max(interim,key=lambda x:(iso_date(x['filing_date']),x['accession_number'])))
    print('BEST_V2_MATCHED_FILINGS',json.dumps(dict(ticker=row['ticker'],cik=row['cik'],unrelated_records=len(financial)-len(matches),selected=[dict(accession=x['accession_number'],form=x['type'],filed=iso_date(x['filing_date'])) for x in chosen])),flush=True)
    for x in chosen:
        if not any(e.get('relation')=='filer' and str(e.get('company_data',{}).get('cik','')).zfill(10)==row['cik'] for e in x.get('entities',[])):raise DataUnavailable('FINANCIAL_EVENT_IDENTITY_MISMATCH')
        raw=raw_document(client,x['main_file_url']);text=re.sub('<[^>]+>',' ',raw.decode('utf-8',errors='replace'))
        keep(x['accession_number'],text,x['source_url'],iso_date(x['filing_date']))
    # Positive/ambiguous deal language is an explicit event exclusion requiring review,
    # never an optimistic CLEAR. Event termination requires original analyst review.
    return dict(status='EXCLUDED_PENDING_PRICE_BINDING_EVENT' if warnings else 'CLEAR',index_sha256=digest(index),
        indexed_forms=len(index),indexed_8k=len(required),reviewed_documents=len(documents),documents=documents,
        warning_accessions=warnings,scope='All provider-indexed SEC material forms and annual/interim originals; provider updates daily')


def reference(row,day,root,client,decision_at):
    decision=datetime.fromisoformat(decision_at);date=decision.astimezone(NY).date().isoformat()
    path=Path(root)/'best-v2-reference'/date/(row['ticker']+'.json')
    if path.exists():receipt=read_json(path)
    else:
        profile=client.get('/v3/reference/tickers/'+row['ticker'],{'date':date})['results']
        if profile.get('ticker')!=row['ticker'] or str(profile.get('cik','')).zfill(10)!=row['cik'] or profile.get('type')!='CS':raise DataUnavailable('V2_REFERENCE_IDENTITY_MISMATCH')
        receipt=dict(ticker=row['ticker'],cik=row['cik'],price_date=day,decision_date=date,
            observed_at=datetime.now(timezone.utc).isoformat(),profile={k:profile.get(k) for k in ('ticker','cik','type','description','sic_code','sic_description','name')},**classify(profile))
        # Save business proof even if event access is blocked; not a clearance.
        receipt['event_status']='DATA_BLOCKED';atomic_json(path,receipt)
    if receipt['cik']!=row['cik'] or receipt['decision_date']!=date:raise DataUnavailable('V2_RECEIPT_IDENTITY_MISMATCH')
    if receipt.get('event_status')=='DATA_BLOCKED':
        events=review_events(client,dict(row,_cache=str(root)),date)
        receipt.update(events=events,event_status=events['status'],observed_at=datetime.now(timezone.utc).isoformat());atomic_json(path,receipt)
    return dict(row,**{k:receipt[k] for k in ('sector','factor','healthcare_exposure')},event_status=receipt['event_status'],reference_sha256=digest(receipt))
