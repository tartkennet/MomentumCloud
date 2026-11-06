"""Bounded source capability discovery; no selection, account or orders."""
import json
from datetime import datetime,timezone
from best_data import BestProvider
from quality_sources import DataUnavailable

def main():
    client=BestProvider()
    for ticker in ('ITGR','HZO','HNGE','AAPL'):
        out={'ticker':ticker,'observed_at':datetime.now(timezone.utc).isoformat()}
        for label,path,params in [('reference','/v3/reference/tickers/'+ticker,{}),('filings','/v1/reference/sec/filings',{'entities.company_data.ticker':ticker,'filing_date.gte':'2025-10-01','sort':'filing_date','order':'desc','limit':3})]:
            try:
                d=client.get(path,params)
                # No request URLs, credentials, or raw signed provider links.
                rows=d.get('results',[])
                if label=='reference':out[label]={k:rows.get(k) for k in ('ticker','cik','description','sic_code','sic_description')}
                else:out[label]={'keys':list(rows[0]) if rows else [],'rows':[{k:r.get(k) for k in ('id','accession_number','type','filing_date','acceptance_datetime','description','items','entities')} for r in rows],'paginated':bool(d.get('next_url'))}
            except DataUnavailable as e:out[label]={'blocked':str(e)}
        print('BEST_V2_SOURCE_PROBE',json.dumps(out),flush=True)
if __name__=='__main__':main()
