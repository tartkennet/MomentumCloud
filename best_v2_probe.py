"""Bounded source capability discovery; no selection, account or orders."""
import json
from datetime import datetime,timezone
from best_data import BestProvider
from quality_sources import DataUnavailable

def main():
    client=BestProvider()
    for ticker in ('ITGR','HZO','HNGE','AAPL'):
        out={'ticker':ticker,'observed_at':datetime.now(timezone.utc).isoformat()}
        for label,path,params in [('reference','/v3/reference/tickers/'+ticker,{}),('eight_k','/v1/reference/sec/filings',{'entities.company_data.ticker':ticker,'type':'8-K','filing_date.gte':'2025-10-01','limit':2}),('all_form_index','/stocks/filings/vX/index',{'ticker':ticker,'form_type':'8-K','filing_date.gte':'2025-10-01','limit':2}),('filings','/v1/reference/sec/filings',{'entities.company_data.ticker':ticker,'filing_date.gte':'2025-10-01','sort':'filing_date','order':'desc','limit':3})]:
            try:
                d=client.get(path,params)
                # No request URLs, credentials, or raw signed provider links.
                rows=d.get('results',[])
                if label=='reference':out[label]={k:rows.get(k) for k in ('ticker','cik','description','sic_code','sic_description')}
                else:out[label]={'keys':list(rows[0]) if rows else [],'rows':[{k:r.get(k) for k in ('id','accession_number','type','filing_date','acceptance_datetime','description','items','entities')} for r in rows],'paginated':bool(d.get('next_url'))}
            except DataUnavailable as e:out[label]={'blocked':str(e)}
        try:
            from urllib.parse import urlparse
            r=client.get('/v1/reference/sec/filings',{'entities.company_data.ticker':ticker,'limit':1,'sort':'filing_date','order':'desc'})['results'][0]
            u=urlparse(r['main_file_url']);out['original_path']=u.path
            response=client.session.get('https://api.polygon.io'+u.path,params={'apiKey':client.key},timeout=(5,20))
            text=response.text.lower();out['original_read']={'http':response.status_code,'bytes':len(response.content),'merger_term': 'merger agreement' in text,'cash_term':'per share in cash' in text}
        except Exception as e:out['original_read']={'blocked':type(e).__name__}
        try:
            r=client.get('/stocks/filings/vX/index',{'ticker':ticker,'form_type':'8-K','limit':1,'sort':'filing_date','order':'desc'})['results'][0]
            a=r['accession_number'];out['event_originals']={}
            for label,path in [('files','/v1/reference/sec/filings/'+a+'/files'),('text','/stocks/filings/8-K/vX/text?ticker='+ticker),('details','/v1/reference/sec/filings/'+a)]:
                try:
                    body=client.get('/stocks/filings/8-K/vX/text',{'ticker':ticker,'accession_number':a,'limit':2}) if label=='text' else client.get(path);out['event_originals'][label]={'keys':list(body),'excerpt':str(body.get('results',[{}])[0].get('items_text',''))[:1500] if label=='text' and body.get('results') else None,'result_keys':list(body['results'][0]) if isinstance(body.get('results'),list) and body['results'] else []}
                except DataUnavailable as e:out['event_originals'][label]={'blocked':str(e)}
        except Exception as e:out['event_originals']={'blocked':type(e).__name__}
        print('BEST_V2_SOURCE_PROBE',json.dumps(out),flush=True)
if __name__=='__main__':main()
