"""Bounded access check for required foreign issuer originals; never clears a company."""
import json
from urllib.parse import urlparse
from best_data import BestProvider
from quality_sources import DataUnavailable
from best_v2_sources import raw_document
def main():
    c=BestProvider()
    rows=c.get('/stocks/filings/vX/index',{'ticker':'SN','form_type':'6-K','limit':3,'sort':'filing_date.desc'}).get('results',[])
    for r in rows:
        u=urlparse(r['filing_url']);a=r['accession_number'];out={k:r.get(k) for k in ('ticker','cik','form_type','filing_date','accession_number')}
        out['source_url']=r['filing_url']
        path='/v1/reference/sec/filings/'+a+'/files/'+u.path.split('/')[-1]
        try:
            b=raw_document(c,'https://api.polygon.io'+path);out['authenticated_original']={'http':200,'bytes':len(b)}
        except DataUnavailable as e:out['authenticated_original']={'blocked':str(e)}
        try:
            d=c.get('/v1/reference/sec/filings/'+a+'/files').get('results')
            out['files_schema']={'kind':type(d).__name__,'keys':list(d)[:8] if isinstance(d,dict) else None,'count':len(d) if d is not None else None}
        except DataUnavailable as e:out['files_schema']={'blocked':str(e)}
        print('BEST_V2_FOREIGN_ORIGINAL_PROBE',json.dumps(out),flush=True)
if __name__=='__main__':main()
