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

if __name__=='__main__':
    import hashlib,requests
    c=BestProvider();acc='0001104659-26-120692';name='tm2628622d1_8ka.htm'
    paths=[('provider','https://api.polygon.io/v1/reference/sec/filings/'+acc+'/files/'+name),('sec_html','https://www.sec.gov/Archives/edgar/data/876883/000110465926120692/'+name),('public_original_copy','https://cdn.yahoofinance.com/prod/sec-filings/0000876883/000110465926120692/'+name)]
    for label,url in paths:
        try:
            r=requests.get(url,params={'apiKey':c.key} if label=='provider' else {},headers={'User-Agent':'MomentumCloud research github.com/tartkennet/MomentumCloud'},timeout=(5,20))
            print('BEST_REQUIRED_AMENDMENT_ORIGINAL',json.dumps(dict(source=label,http=r.status_code,bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest(),company='Stagwell' in r.text,form='8-K/A' in r.text,cik='876883' in r.text)),flush=True)
        except requests.RequestException as e:print('BEST_REQUIRED_AMENDMENT_ORIGINAL',json.dumps(dict(source=label,error=type(e).__name__)),flush=True)

if __name__=='__main__':
    from best_v2_sources import pages
    records=pages(BestProvider(),'/stocks/filings/vX/index',{'cik':'0001978954','filing_date.gte':'2025-10-03','filing_date.lte':'2026-11-07','limit':1000,'sort':'filing_date.desc'})
    print('BEST_REQUIRED_FOREIGN_INDEX',json.dumps([r for r in records if r.get('form_type') in ('6-K','6-K/A','425','SC TO-T','SC 14D9','DEFM14A')]),flush=True)

if __name__=='__main__':
    from concurrent.futures import ThreadPoolExecutor
    filing='0001193125-26-443746';cik='0001978954';base='https://cdn.yahoofinance.com/prod/sec-filings/'+cik+'/'+filing.replace('-','')+'/'
    probes=[('provider_real_name','https://api.polygon.io/v1/reference/sec/filings/'+filing+'/files/6k_tbbb_3q26_earnings_re.htm'),('copy_html',base+'6k_tbbb_3q26_earnings_re.htm'),('copy_submission',base+filing+'.txt'),('issuer_index','https://www.investorstiendas3b.com/financials/sec-filings/default.aspx')]
    def check(pair):
        label,url=pair
        try:
            r=requests.get(url,params={'apiKey':c.key} if label.startswith('provider') else {},timeout=(5,15))
            out=dict(source=label,http=r.status_code,bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest())
            if label=='issuer_index':
                import re
                out['scripts']=re.findall(r'<script[^>]+src=[\"\x27]([^\"\x27]+)',r.text)
                out['feed_calls']=re.findall(r'.{0,120}(?:edgar|Edgar|secFilings|SEC\.svc|SecFiling).{0,350}',r.text)[:15]
            return out
        except requests.RequestException as exc:return dict(source=label,error=type(exc).__name__)
    for result in ThreadPoolExecutor(max_workers=4).map(check,probes):print('BEST_TBBB_ORIGINAL_ACCESS',json.dumps(result),flush=True)

if __name__=='__main__':
    import re
    from best_v2_mirrors import Text
    candidates=json.loads(open('data/foreign_original_candidates.json').read())
    for entry in candidates:
        for name in entry['files']:
            url='https://cdn.yahoofinance.com/prod/sec-filings/'+entry['cik']+'/'+entry['accession_number'].replace('-','')+'/'+name
            try:
                r=requests.get(url,timeout=(5,15));parser=Text();parser.feed(r.text);text=' '.join(parser.parts)
                print('BEST_FOREIGN_COPY_FINGERPRINT',json.dumps(dict(accession=entry['accession_number'],name=name,http=r.status_code,bytes=len(r.content),sha256=hashlib.sha256(r.content).hexdigest(),characters=len(text),company='bbb foods' in text.lower(),form='6-k' in text.lower(),signature='signatures' in text.lower(),items=sorted(set(re.findall(r'item\s+(\d\.\d\d)',text.lower()))))),flush=True)
            except requests.RequestException as exc:print('BEST_FOREIGN_COPY_FINGERPRINT',json.dumps(dict(accession=entry['accession_number'],name=name,error=type(exc).__name__)),flush=True)
