"""Verified issuer copies of indexed originals; never a company eligibility exemption."""
import gzip,hashlib,json,re
from datetime import datetime,timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
import requests
from html.parser import HTMLParser
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

class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def inspect(raw,entry):
    if entry.get('format')!='html':return inspect_pdf(raw,entry)
    parser=Text();parser.feed(raw.decode('utf-8'));text=' '.join(parser.parts)
    if len(text)<entry['min_characters'] or any(normalized(m) not in normalized(text) for m in entry['markers']):raise DataUnavailable('ORIGINAL_HTML_IDENTITY_OR_COMPLETENESS')
    items=sorted(set(re.findall(r'item\s+(\d\.\d\d)',text.lower())))
    if items!=entry['required_items']:raise DataUnavailable('ORIGINAL_HTML_MATERIAL_ITEMS_MISMATCH')
    return text,dict(format='html',material_items=items,text_sha256=sha(text.encode()),bytes=len(raw),sha256=sha(raw),characters=len(text))

def download(entry):
    p=urlparse(entry['url'])
    valid=(p.hostname=='s202.q4cdn.com' and p.path.startswith('/'+entry.get('issuer_tenant','MISSING')+'/')) or (p.hostname=='cdn.yahoofinance.com' and p.path.startswith('/prod/sec-filings/'+entry['cik']+'/'+entry['accession_number'].replace('-','')+'/'))
    if not valid or p.query:raise DataUnavailable('UNTRUSTED_ISSUER_MIRROR')
    r=requests.get(entry['url'],timeout=(5,25))
    if r.status_code!=200:raise DataUnavailable('ISSUER_MIRROR_HTTP_'+str(r.status_code))
    if len(r.content)>20_000_000:raise DataUnavailable('OVERSIZE_ISSUER_MIRROR')
    return r.content

def probe():
    for entry in json.loads(REGISTRY.read_text()):
        raw=download(entry);text,meta=inspect(raw,entry)
        origin=requests.get(entry.get('issuer_page',entry['canonical_sec_document']),timeout=(5,20)) if 'canonical_sec_document' in entry else requests.get(entry['issuer_page'],timeout=(5,20))
        print('BEST_V2_ISSUER_MIRROR_PROBE',json.dumps(dict(cik=entry['cik'],accession=entry['accession_number'],
            issuer_page_http=origin.status_code,issuer_tenant_in_page=entry.get('issuer_tenant','NOT_APPLICABLE') in origin.text,**meta)),flush=True)

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
    cache=Path(root)/'best-v2-mirrors';cache.mkdir(parents=True,exist_ok=True);asset=cache/(expected+('.html' if entry.get('format')=='html' else '.pdf'))
    raw=asset.read_bytes() if asset.exists() else download(entry)
    if sha(raw)!=expected:raise DataUnavailable('CHANGED_ISSUER_MIRROR')
    text,meta=inspect(raw,entry)
    if not asset.exists():asset.write_bytes(raw)
    receipt=dict(meta,cik=row['cik'],accession=entry['accession_number'],filing_date=entry['filing_date'],form_type=entry['form_type'],
        source='PINNED_ORIGINAL_HTML_COPY' if entry.get('format')=='html' else 'ISSUER_COMPLETE_FILING_PDF',source_url=entry['url'],issuer_page=entry.get('issuer_page'),canonical_sec_document=entry.get('canonical_sec_document'),original_sec_url=url,
        observed_at=datetime.now(timezone.utc).isoformat(),asset=asset.name)
    atomic_json(cache/(expected+'.json'),receipt)
    return text,receipt

if __name__=='__main__':probe()
