"""Verified issuer copies of indexed originals; never a company eligibility exemption."""
import gzip,hashlib,json,re
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
import requests
from pypdf import PdfReader
from quality_sources import DataUnavailable
from momentum_core_data import atomic_json

REGISTRY=Path('data/filing_mirrors.json')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def normalized(s):return re.sub(r'\s+','',s).lower()

def inspect_pdf(raw,entry):
    if not raw.startswith(b'%PDF-'):raise DataUnavailable('MIRROR_NOT_PDF')
    reader=PdfReader(BytesIO(raw));text='\n'.join(p.extract_text() or '' for p in reader.pages)
    title=str((reader.metadata or {}).get('/Title',''))
    if entry['accession_number'] not in title:raise DataUnavailable('MIRROR_ACCESSION_MISMATCH')
    if len(reader.pages)!=entry['pages'] or len(text)<50000:raise DataUnavailable('INCOMPLETE_FILING_MIRROR')
    if any(normalized(m) not in normalized(text) for m in entry['markers']):raise DataUnavailable('MIRROR_IDENTITY_OR_EXHIBIT_MISMATCH')
    return text,dict(pages=len(reader.pages),title=title,text_sha256=sha(text.encode()),bytes=len(raw),sha256=sha(raw),characters=len(text))

def download(entry):
    p=urlparse(entry['url'])
    if p.hostname!='s202.q4cdn.com' or not p.path.startswith('/'+entry['issuer_tenant']+'/'):raise DataUnavailable('UNTRUSTED_ISSUER_MIRROR')
    r=requests.get(entry['url'],timeout=(5,25))
    if r.status_code!=200:raise DataUnavailable('ISSUER_MIRROR_HTTP_'+str(r.status_code))
    if len(r.content)>20_000_000:raise DataUnavailable('OVERSIZE_ISSUER_MIRROR')
    return r.content

def probe():
    for entry in json.loads(REGISTRY.read_text()):
        raw=download(entry);text,meta=inspect_pdf(raw,entry)
        origin=requests.get(entry['issuer_page'],timeout=(5,20))
        print('BEST_V2_ISSUER_MIRROR_PROBE',json.dumps(dict(cik=entry['cik'],accession=entry['accession_number'],
            issuer_page_http=origin.status_code,issuer_tenant_in_page=entry['issuer_tenant'] in origin.text,**meta)),flush=True)

def original(row,filing,root,cutoff):
    # Reuse any authenticated prior SEC cache with exact URL/hash evidence.
    url=filing['filing_url'];key=sha(url.encode())
    for path in Path(root).rglob(key+'.json'):
        meta=json.loads(path.read_text());asset=path.parent/meta.get('asset','')
        if meta.get('url')!=url or asset.name!=meta.get('asset') or not asset.is_file():continue
        raw=gzip.decompress(asset.read_bytes())
        if sha(raw)!=meta.get('sha256'):raise DataUnavailable('CHANGED_CACHED_SEC_ORIGINAL')
        return raw.decode('utf-8',errors='replace'),dict(meta,source='CACHED_ORIGINAL_SEC')
    entry=next((e for e in json.loads(REGISTRY.read_text()) if e['cik']==row['cik'] and e['accession_number']==filing['accession_number']),None)
    if not entry:raise DataUnavailable('NO_VERIFIED_ISSUER_MIRROR')
    if entry['filing_date']!=filing['filing_date'] or entry['form_type']!=filing['form_type'] or entry['filing_date']>cutoff:raise DataUnavailable('MIRROR_FILING_DATE_OR_FORM_MISMATCH')
    expected=entry.get('sha256')
    if not expected or not re.fullmatch('[0-9a-f]{64}',expected):raise DataUnavailable('UNPINNED_ISSUER_MIRROR')
    cache=Path(root)/'best-v2-mirrors';cache.mkdir(parents=True,exist_ok=True);asset=cache/(expected+'.pdf')
    raw=asset.read_bytes() if asset.exists() else download(entry)
    if sha(raw)!=expected:raise DataUnavailable('CHANGED_ISSUER_MIRROR')
    text,meta=inspect_pdf(raw,entry)
    if not asset.exists():asset.write_bytes(raw)
    receipt=dict(meta,cik=row['cik'],accession=entry['accession_number'],filing_date=entry['filing_date'],form_type=entry['form_type'],
        source='ISSUER_COMPLETE_FILING_PDF',source_url=entry['url'],issuer_page=entry['issuer_page'],original_sec_url=url,
        observed_at=datetime.now(timezone.utc).isoformat(),asset=asset.name)
    atomic_json(cache/(expected+'.json'),receipt)
    return text,receipt

if __name__=='__main__':probe()
