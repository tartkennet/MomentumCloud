"""Read-only public SEC transport evidence; never runs or changes a paper account."""
import hashlib,json,time
from pathlib import Path
import requests
from best_v2_sources import canonical_sec_submission

row={'cik':'0001625101'}
filing=dict(cik=row['cik'],accession_number='0001437749-26-006269',filing_url='https://www.sec.gov/Archives/edgar/data/1625101/0001437749-26-006269.txt')
urls=[filing['filing_url'],canonical_sec_submission(row,filing),'https://data.sec.gov/submissions/CIK0001625101.json']
session=requests.Session();session.headers['User-Agent']='MomentumCloud research (github.com/tartkennet/MomentumCloud)'
results=[]
for url in urls:
    time.sleep(1)
    try:
        r=session.get(url,timeout=(5,20));body=r.content
        result=dict(url=url,http=r.status_code,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),
                    sec_access_denied='undeclared automated tool' in r.text.lower() or 'access denied' in r.text.lower(),
                    accession_present=filing['accession_number'].encode() in body,
                    retry_after=r.headers.get('Retry-After'),content_type=r.headers.get('Content-Type'))
    except requests.RequestException as exc:result=dict(url=url,error=type(exc).__name__)
    results.append(result);print('BEST_V2_SEC_TRANSPORT',json.dumps(result),flush=True)
Path('sec-transport.json').write_text(json.dumps(results,indent=2))
