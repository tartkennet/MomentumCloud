"""Native-currency dividend bookkeeping for the separate v2 study only."""
from datetime import date
from xml.etree import ElementTree

from momentum_core import DataBlocked

TD_REPAIR={'ticker':'TD','ex_dividend_date':'2026-01-09','cash_amount':1.08,'currency':'CAD',
    'pay_date':'2026-02-02','contractual_pay_date':'2026-01-31',
    'source_url':'https://stories.td.com/ca/en/news/2025-12-04-td-bank-group-declares-dividends',
    'business_day_source':'https://www.td.com/ca/en/about-td/for-investors/investor-relations/share-information/dividends'}


def supplement_native_dividend(data):
    matched=[e for e in data.source.dividends if e['ticker']=='TD' and e['ex_dividend_date']=='2026-01-09']
    if len(matched)!=1:raise DataBlocked('Ambiguous TD dividend repair')
    previous=dict(matched[0]);replacement=dict(previous,**TD_REPAIR)
    data.source.dividends=[replacement if e is matched[0] else e for e in data.source.dividends]
    data.dividends_by_day={}
    for e in data.source.dividends:data.dividends_by_day.setdefault(e['ex_dividend_date'],[]).append(e)
    return {'original':previous,'verified_replacement':replacement}


class ReferenceFX:
    def __init__(self,path):
        self.rows={}
        for node in ElementTree.parse(path).iter():
            if 'time' in node.attrib:
                row={c.attrib['currency']:float(c.attrib['rate']) for c in node if 'currency' in c.attrib}
                if 'USD' in row:self.rows[node.attrib['time']]={'EUR':1.,**row}
        self.memo={}

    def usd(self,day,currency):
        if currency=='USD':return 1.
        key=(day,currency)
        if key not in self.memo:
            prior=max((d for d in self.rows if d<day),default=None)
            if not prior or (date.fromisoformat(day)-date.fromisoformat(prior)).days>7 or currency not in self.rows[prior]:
                raise DataBlocked('Missing prior-date native dividend FX '+currency+' '+day)
            self.memo[key]=self.rows[prior]['USD']/self.rows[prior][currency]
        return self.memo[key]


def native_dividends(ledger,data,day,callback):
    """Keep native face receivable, daily USD mark, and pay-date conversion fee."""
    events=data.dividends
    foreign=[e for e in events if e.get('currency','').upper()!='USD']
    quantities=dict(ledger.shares)
    for e in data.splits:
        if e['ticker'] in quantities:quantities[e['ticker']]*=e['split_to']/e['split_from']
    due=[]
    for claim in ledger.receivables:
        if 'native_amount' in claim:
            claim['amount']=claim['native_amount']*data.native_usd(day,claim['currency'])
            if claim.get('pay_date') and claim['pay_date']<=day:due.append(dict(claim))
    data.dividends=[e for e in events if e not in foreign]
    try:callback()
    finally:data.dividends=events
    for e in foreign:
        t=e['ticker'];q=quantities.get(t,0)
        if e['ex_dividend_date']!=day:continue
        if not q:continue
        currency=e.get('currency','').upper();pay=e.get('pay_date')
        if not pay or pay<day or float(e['cash_amount'])<0:raise DataBlocked('Unresolved native dividend '+t+' '+str(e))
        face=q*float(e['cash_amount']);amount=face*data.native_usd(day,currency)
        claim=dict(ticker=t,amount=amount,pay_date=pay,reason='NATIVE_DIVIDEND',currency=currency,native_amount=face)
        if pay<=day:ledger.cash+=amount;due.append(claim)
        else:ledger.receivables.append(claim)
    for claim in due:
        charge=claim['amount']*.0025
        ledger.cash-=charge;ledger.fees+=charge
        ledger.fx_payments.append(dict(date=day,ticker=claim['ticker'],currency=claim['currency'],
            native_amount=claim['native_amount'],gross_usd=claim['amount'],fee_usd=charge,
            scheduled_pay_date=claim['pay_date'],rate=data.native_usd(day,claim['currency'])))
