"""Check whether the existing material-text service actually covers foreign forms."""
import json
from best_data import BestProvider
from quality_sources import DataUnavailable
def main():
    c=BestProvider()
    for form in ('6-K','6-K/A'):
        try:
            d=c.get('/stocks/filings/8-K/vX/text',{'cik':'0001957132','form_type':form,'filing_date.gte':'2025-10-01','filing_date.lte':'2026-11-06','limit':100,'sort':'filing_date.desc'})
            rows=d.get('results',[])
            out={'requested_form':form,'count':len(rows),'paginated':bool(d.get('next_url')),'rows':[{k:r.get(k) for k in ('cik','form_type','filing_date','accession_number','filing_url')}|{'text_bytes':len(r.get('items_text',''))} for r in rows]}
        except DataUnavailable as e:out={'requested_form':form,'blocked':str(e)}
        print('BEST_FOREIGN_TEXT_CAPABILITY',json.dumps(out),flush=True)
    for params in ({'entities.company_data.ticker':'SN'},{'entities.company_data.cik':'0001957132'},{'cik':'0001957132'}):
        try:
            d=c.get('/v1/reference/sec/filings',dict(params,limit=5,sort='filing_date',order='desc'))
            out={'query_fields':list(params),'rows':[{'id':r.get('id'),'form':r.get('type'),'date':r.get('filing_date'),'entities':r.get('entities')} for r in d.get('results',[])]}
        except DataUnavailable as e:out={'query_fields':list(params),'blocked':str(e)}
        print('BEST_FILING_IDENTITY_PROBE',json.dumps(out),flush=True)
if __name__=='__main__':main()
