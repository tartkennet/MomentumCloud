"""Primary SEC classification evidence; no guessed SIC and no future vintage."""
import json
import threading
from datetime import datetime,timezone
from quality_forward import NY,digest
from quality_sources import DataUnavailable,iso_date
from supplement_quality_sources import SEC,header
from best_strategy import division


_SEC_ACCESS=threading.Lock()

def sec_classification(row,day,root,client=None):
    with _SEC_ACCESS:return _sec_classification(row,day,root,client)

def _sec_classification(row,day,root,client=None):
    client=client or SEC(root)
    raw,receipt=client.get('https://data.sec.gov/submissions/CIK'+row['cik']+'.json')
    payload=json.loads(raw)
    if str(payload.get('cik','')).zfill(10)!=row['cik']:raise DataUnavailable('SEC_REFERENCE_IDENTITY_MISMATCH')
    stamp=datetime.fromisoformat(receipt['observed_at']).astimezone(NY).date().isoformat()
    sic=str(payload.get('sic') or '').zfill(4)
    if stamp<=day:
        try:division(sic)
        except (TypeError,ValueError):pass
        else:return dict(sic=sic,cik=row['cik'],filed=stamp,observed_at=receipt['observed_at'],
            source='SEC_REFERENCE_OBSERVED_BY_SIGNAL_DATE',source_sha256=receipt['sha256'],source_url=receipt['url'])
    groups=[payload['filings']['recent']]
    def annuals(groups):
        result=[]
        for group in groups:
            for i,form in enumerate(group.get('form',[])):
                if form not in ('20-F','20-F/A','10-K','10-Q','40-F','40-F/A') or group['filingDate'][i]>day:continue
                result.append(dict(form=form,filed=group['filingDate'][i],accession=group['accessionNumber'][i]))
        return sorted(result,key=lambda r:(r['filed'],r['accession']),reverse=True)
    if not annuals(groups):
        for part in payload['filings'].get('files',[]):
            if part.get('filingFrom','9999')>day:continue
            history,_=client.get('https://data.sec.gov/submissions/'+part['name']);groups.append(json.loads(history))
            if annuals(groups):break
    for filing in annuals(groups)[:3]:
        accession=filing['accession']
        url='https://www.sec.gov/Archives/edgar/data/'+str(int(row['cik']))+'/'+accession.replace('-','')+'/'+accession+'.txt'
        original,meta=client.get(url);filing_header=header(original,accession,row['cik'])
        filed=iso_date(filing_header['filing_date'])
        if filed>day:continue
        sic=filing_header['sic'];division(sic)
        return dict(sic=sic,cik=row['cik'],filed=filed,accession=accession,observed_at=meta['observed_at'],
            source='ORIGINAL_SEC_FILER_HEADER',source_sha256=meta['sha256'],source_url=url)
    raise DataUnavailable('SEC_ASOF_CLASSIFICATION_UNAVAILABLE')
