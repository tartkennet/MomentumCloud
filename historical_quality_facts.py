"""Separate historical adapter. Economic rules copied unchanged from the frozen parser.
Only acquisition-vs-publication clocks differ. The prospective parser is untouched.
"""
import hashlib
import io
import math
from datetime import date,datetime,timezone
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as E
from quality_sources import DataUnavailable,iso_date

def available_at(filing):
    value=str(filing.get('acceptance_datetime',''))
    if len(value)!=14 or not value.isdigit():raise DataUnavailable('MISSING_ACCEPTANCE_TIMESTAMP')
    accepted=datetime.strptime(value,'%Y%m%d%H%M%S').replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
    # Filing day can be later than after-hours acceptance. Use the LATER bound.
    filed=datetime.fromisoformat(iso_date(filing['filing_date'])).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
    return max(accepted,filed)


X='http://www.xbrl.org/2003/instance'
USD='http://www.xbrl.org/2003/iso4217'
TAGS={'revenue':('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'),
      'net_income':('NetIncomeLoss',),
      'eps':('EarningsPerShareDiluted',),'operating_cash_flow':('NetCashProvidedByUsedInOperatingActivities',)}


def parse_historical(raw,receipt,cik,decision_at):
    if hashlib.sha256(raw).hexdigest()!=receipt['sha256']:raise DataUnavailable('SOURCE_HASH_MISMATCH')
    # Acquisition is NOW; economic availability is the original SEC acceptance.
    # Never fabricate a past acquisition timestamp or use period-end as publication.
    actual=datetime.fromisoformat(receipt['observed_at'])
    if actual.tzinfo is None:raise DataUnavailable('MISSING_RETRIEVAL_TIMEZONE')
    published=available_at(receipt['filing'])
    if published>datetime.fromisoformat(decision_at):raise DataUnavailable('REPORT_NOT_YET_PUBLIC')
    decision=datetime.fromisoformat(decision_at)
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise DataUnavailable('UNSAFE_XML')
    namespaces={}
    for _,(prefix,uri) in E.iterparse(io.BytesIO(raw),events=('start-ns',)):
        if prefix in namespaces and namespaces[prefix]!=uri:raise DataUnavailable('AMBIGUOUS_NAMESPACE')
        namespaces[prefix]=uri
    tree=E.fromstring(raw);filing=receipt['filing'];end=iso_date(filing['period_of_report_date'])
    filed=iso_date(filing['filing_date'])
    if filed>decision_at[:10] or end>filed:raise DataUnavailable('INVALID_REPORT_DATES')
    if (decision.date()-date.fromisoformat(filed)).days>140:raise DataUnavailable('STALE_FILING')
    def dei(tag):
        values=set()
        for n in tree:
            if not n.tag.endswith('}'+tag) or '/dei/' not in n.tag:continue
            ctx=next((c for c in tree if c.tag=='{'+X+'}context' and c.get('id')==n.get('contextRef')),None)
            if ctx is not None:
                identifier=ctx.find('.//{'+X+'}identifier')
                if identifier is None or str(int(identifier.text))!=str(int(cik)):continue
            values.add(str(int(n.text)) if tag=='EntityCentralIndexKey' else n.text)
        if len(values)!=1:raise DataUnavailable('AMBIGUOUS_'+tag)
        return next(iter(values))
    if str(int(dei('EntityCentralIndexKey')))!=str(int(cik)):raise DataUnavailable('WRONG_CIK')
    if dei('DocumentPeriodEndDate')!=end or dei('DocumentType')!=filing['type']:raise DataUnavailable('WRONG_FILING_IDENTITY')
    if any(n.text=='true' for n in tree if n.tag.endswith('}AmendmentFlag')):raise DataUnavailable('AMENDMENT_REQUIRES_REVIEW')
    contexts={};units={}
    for node in tree:
        if node.tag=='{'+X+'}context':
            if any(n.tag in ('{'+X+'}segment','{'+X+'}scenario') or 'xbrldi' in n.tag for n in node.iter()):continue
            identifier=node.find('.//{'+X+'}identifier')
            if identifier is None or str(int(identifier.text))!=str(int(cik)):continue
            start=node.find('.//{'+X+'}startDate');finish=node.find('.//{'+X+'}endDate')
            if start is not None and finish is not None:contexts[node.attrib['id']]=(start.text,finish.text)
        if node.tag=='{'+X+'}unit':
            def measure(n):
                text=n.text or '';prefix,local=text.split(':',1) if ':' in text else ('',text)
                return namespaces.get(prefix),local
            measures=[measure(n) for n in node.iter() if n.tag=='{'+X+'}measure']
            if measures==[(USD,'USD')]:units[node.attrib['id']]='USD'
            elif measures==[(USD,'USD'),(X,'shares')]:units[node.attrib['id']]='USD/shares'
    extracted={};concepts={}
    for field,alternatives in TAGS.items():
        for tag in alternatives:
            values={}
            for n in tree:
                if not n.tag.endswith('}'+tag) or not n.tag[1:].startswith(('http://fasb.org/us-gaap/','https://fasb.org/us-gaap/')):continue
                period=contexts.get(n.attrib.get('contextRef'));unit=units.get(n.attrib.get('unitRef'))
                if not period or unit!=('USD/shares' if field=='eps' else 'USD') or n.text is None:continue
                try:value=float(n.text)
                except ValueError:continue
                if not math.isfinite(value):continue
                if period in values and not math.isclose(value,values[period],rel_tol=1e-10,abs_tol=1e-8):raise DataUnavailable('CONFLICTING_'+field)
                values[period]=value
            if values:extracted[field]=values;concepts[field]=tag;break
        if field not in extracted:raise DataUnavailable('MISSING_'+field)
    shared=set.intersection(*(set(v) for v in extracted.values()))
    current=[p for p in shared if p[1]==end and 70<=(date.fromisoformat(p[1])-date.fromisoformat(p[0])).days<=380]
    if not current:raise DataUnavailable('NO_COMPLETE_REPORT_PERIOD')
    period=max(current,key=lambda p:(date.fromisoformat(p[1])-date.fromisoformat(p[0])).days)
    duration=(date.fromisoformat(period[1])-date.fromisoformat(period[0])).days
    prior=[p for p in shared if 350<=(date.fromisoformat(end)-date.fromisoformat(p[1])).days<=380 and abs((date.fromisoformat(p[1])-date.fromisoformat(p[0])).days-duration)<=10]
    if len(prior)!=1:raise DataUnavailable('NO_UNAMBIGUOUS_PRIOR_COMPARATIVE')
    previous=prior[0];now={k:v[period] for k,v in extracted.items()};old={k:v[previous] for k,v in extracted.items()}
    if now['revenue']<=0 or old['revenue']<=0:raise DataUnavailable('NONPOSITIVE_REVENUE')
    metrics=dict(revenue_growth=now['revenue']/old['revenue']-1,
        eps_growth=now['eps']/old['eps']-1 if old['eps']>0 else None,
        net_margin=now['net_income']/now['revenue'],
        margin_change=now['net_income']/now['revenue']-old['net_income']/old['revenue'],
        cash_conversion=now['operating_cash_flow']/now['net_income'] if now['net_income']>0 else None)
    checks=dict(revenue_growth=metrics['revenue_growth']>0,earnings_growth=old['eps']>0 and now['eps']>old['eps'],
        profitability_improvement=now['net_income']>0 and metrics['margin_change']>=0,
        positive_profits=now['net_income']>0 and old['net_income']>0,
        cash_backing=now['operating_cash_flow']>0 and now['operating_cash_flow']>=now['net_income'] and old['operating_cash_flow']>0)
    return dict(cik=str(cik).zfill(10),accession=filing['accession_number'],filed=filed,report_end=end,period=list(period),
        prior_period=list(previous),period_basis='ANNUAL' if filing['type']=='10-K' else 'FISCAL_YTD',
        observed_at=receipt['observed_at'],available_at=published.isoformat(),sha256=receipt['sha256'],source_url=filing['source_url'],concepts=concepts,
        current=now,prior=old,metrics=metrics,checks=checks,qualified=all(checks.values()))
