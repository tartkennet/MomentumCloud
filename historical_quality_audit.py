"""Independent checks: no strategy or production parser import."""
import hashlib
import math
from datetime import date,datetime,timezone
from historical_quality_facts import available_at
from xml.etree import ElementTree as E


def near(a,b):
    if not math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-8):raise AssertionError('Independent numeric mismatch')


def audit_fundamental(raw,receipt,f,cik,decision_at):
    assert hashlib.sha256(raw).hexdigest()==f['sha256']==receipt['sha256']
    assert datetime.fromisoformat(receipt['observed_at'])<=datetime.now(timezone.utc)
    assert available_at(receipt['filing'])<=datetime.fromisoformat(decision_at)
    assert 0<=(date.fromisoformat(decision_at[:10])-date.fromisoformat(f['filed'])).days<=140
    tree=E.fromstring(raw);ns='{http://www.xbrl.org/2003/instance}'
    contexts={}
    for c in tree.findall(ns+'context'):
        if c.find('.//'+ns+'segment') is not None or c.find(ns+'scenario') is not None:continue
        identifier=c.find('.//'+ns+'identifier');start=c.find('.//'+ns+'startDate');end=c.find('.//'+ns+'endDate')
        if identifier is None or start is None or end is None:continue
        if int(identifier.text)!=int(cik):continue
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
    near(m['net_margin'],c['net_income']/c['revenue'])
    near(m['margin_change'],c['net_income']/c['revenue']-p['net_income']/p['revenue'])
    expected=[c['revenue']>p['revenue'],p['eps']>0 and c['eps']>p['eps'],c['net_income']>0 and m['margin_change']>=0,
              c['net_income']>0 and p['net_income']>0,c['operating_cash_flow']>0 and c['operating_cash_flow']>=c['net_income'] and p['operating_cash_flow']>0]
    assert list(f['checks'].values())==expected and f['qualified']==all(expected)
    return dict(status='PASS',facts_checked=8,source_hash=f['sha256'],independent_code=True,independent_vendor=False)

