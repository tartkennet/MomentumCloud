"""Independent checks: no strategy or production parser import."""
import hashlib
import math
from datetime import date,datetime
from xml.etree import ElementTree as E


def near(a,b):
    if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8):raise AssertionError('Independent numeric mismatch')


def audit_fundamental(raw,receipt,f,cik,decision_at):
    assert hashlib.sha256(raw).hexdigest()==f['sha256']==receipt['sha256']
    assert datetime.fromisoformat(receipt['observed_at'])<=datetime.fromisoformat(decision_at)
    assert 0<=(date.fromisoformat(decision_at[:10])-date.fromisoformat(f['filed'])).days<=140
    tree=E.fromstring(raw);ns='{http://www.xbrl.org/2003/instance}'
    contexts={}
    for c in tree.findall(ns+'context'):
        if c.find('.//'+ns+'segment') is not None or c.find(ns+'scenario') is not None:continue
        identifier=c.find('.//'+ns+'identifier');start=c.find('.//'+ns+'startDate');end=c.find('.//'+ns+'endDate')
        if identifier is None or start is None or end is None:continue
        assert int(identifier.text)==int(cik)
        contexts[c.attrib['id']]=(start.text,end.text)
    original={}
    for name,tag in f['concepts'].items():
        values={}
        for n in tree:
            if n.tag.rsplit('}',1)[-1]!=tag or '/us-gaap/' not in n.tag:continue
            period=contexts.get(n.get('contextRef'))
            if period not in (tuple(f['period']),tuple(f['prior_period'])):continue
            unit=next((u for u in tree.findall(ns+'unit') if u.get('id')==n.get('unitRef')),None)
            assert unit is not None
            measures=[x.text.rsplit(':',1)[-1] for x in unit.iter(ns+'measure')]
            assert measures==(['USD','shares'] if name=='eps' else ['USD'])
            if n.text is None:continue
            value=float(n.text)
            if period in values:near(values[period],value)
            values[period]=value
        assert set(values)=={tuple(f['period']),tuple(f['prior_period'])}
        original[name]=values
        near(values[tuple(f['period'])],f['current'][name]);near(values[tuple(f['prior_period'])],f['prior'][name])
    c=f['current'];p=f['prior'];m=f['metrics']
    near(m['revenue_growth'],(c['revenue']-p['revenue'])/p['revenue'])
    if p['eps']>0:near(m['eps_growth'],(c['eps']-p['eps'])/p['eps'])
    else:assert m['eps_growth'] is None
    near(m['operating_margin'],c['operating_income']/c['revenue'])
    near(m['margin_change'],c['operating_income']/c['revenue']-p['operating_income']/p['revenue'])
    expected=[c['revenue']>p['revenue'],p['eps']>0 and c['eps']>p['eps'],c['operating_income']>0 and m['margin_change']>=0,
              c['net_income']>0 and p['net_income']>0,c['operating_cash_flow']>0 and c['operating_cash_flow']>=c['net_income'] and p['operating_cash_flow']>0]
    assert list(f['checks'].values())==expected and f['qualified']==all(expected)
    return dict(status='PASS',facts_checked=10,source_hash=f['sha256'],independent_code=True,independent_vendor=False)


def audit_plan(targets,plan,shares,cash,nav,prices):
    assert len(targets)==10 and len({r['cik'] for r in targets})==10
    expected_sales={t:math.floor(q) for t,q in shares.items() if t not in {r['ticker'] for r in targets} and q>=1}
    sales={o['ticker']:o['quantity'] for o in plan['orders'] if o['side']=='SELL'};assert sales==expected_sales
    def charge(n):return max(1,n*.0025)+n*.004 if n else 0.
    reserve=sum(q*prices[t]*.98-charge(q*prices[t]*.98) for t,q in sales.items());near(reserve,plan['sale_reserve_usd'])
    spent=0.;buys={}
    for o in plan['orders']:
        assert isinstance(o['quantity'],int) and o['quantity']>=1 and o['ticker']!='SPY'
        if o['side']=='BUY':
            assert o['ticker'] not in shares or shares[o['ticker']]<1
            row=next(r for r in targets if r['ticker']==o['ticker']);near(o['limit'],row['price_usd']*1.02)
            n=o['quantity']*o['limit'];spent+=n+charge(n);buys[o['ticker']]=o['quantity']
    near(spent,plan['reserved_cash_usd']);assert spent<=cash+reserve+1e-8
    assert all(shares.get(r['ticker'],0)>=1 or buys.get(r['ticker'],0)>=1 for r in targets)
    for t,q in plan['retained'].items():assert q==shares[t] and t not in sales and t not in buys
    return dict(status='PASS',orders=len(plan['orders']),funded=True,whole_shares=True,no_future_open_sizing=True)


def audit_selection(rows,targets,nav):
    def sector(s):
        k=int(s)//100
        for lo,hi,name in [(1,9,'Agriculture'),(10,14,'Mining'),(15,17,'Construction'),(20,39,'Manufacturing'),(40,48,'Transport/communications'),(50,51,'Wholesale'),(52,59,'Retail'),(70,89,'Services')]:
            if lo<=k<=hi:return name
        return None
    eligible=[r for r in rows if r['fundamental']['qualified'] and sector(r['sic'])]
    scores={}
    for r in eligible:
        score=0.
        for field in ('revenue_growth','eps_growth','margin_change'):
            values=[x['fundamental']['metrics'][field] for x in eligible];v=r['fundamental']['metrics'][field]
            score+=(len([a for a in values if a<v])+.5*len([a for a in values if a==v]))/len(values)/3
        scores[r['ticker']]=score
    expected=[];used=set();cost=0.
    for r in sorted(eligible,key=lambda x:(-scores[x['ticker']],x['ticker'])):
        ind=str(r['sic'])[:2];sec=sector(r['sic']);p=r['price_usd']*1.02;minimum=p+max(1,p*.0025)+p*.004
        if r['cik'] in used or sum(str(a['sic'])[:2]==ind for a in expected)>=2 or sum(sector(a['sic'])==sec for a in expected)>=4:continue
        if p>nav*.2 or cost+minimum+(9-len(expected))*(10.2+1+10.2*.004)>nav:continue
        expected.append(r);used.add(r['cik']);cost+=minimum
        if len(expected)==10:break
    if len(expected)!=10:expected=[]
    assert [r['ticker'] for r in expected]==[r['ticker'] for r in targets]
    for r in targets:near(r['quality_score'],scores[r['ticker']])
    return dict(status='PASS',eligible=len(eligible),targets=len(targets),independent_code=True)
