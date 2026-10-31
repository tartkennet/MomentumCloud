import copy
import hashlib
import unittest
from quality_fundamentals import parse_original
from quality_sources import DataUnavailable
from quality_strategy import choose,plan_orders
from quality_audit import audit_fundamental,audit_plan


def fixture():
    head='<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2026" xmlns:dei="http://xbrl.sec.gov/dei/2026" xmlns:iso4217="http://www.xbrl.org/2003/iso4217">'
    text=head
    for key,year in [('C','2026'),('P','2025')]:text+=f'<context id="{key}"><entity><identifier scheme="http://www.sec.gov/CIK">123</identifier></entity><period><startDate>{year}-01-01</startDate><endDate>{year}-06-30</endDate></period></context>'
    text+='<unit id="usd"><measure>iso4217:USD</measure></unit><unit id="eps"><divide><unitNumerator><measure>iso4217:USD</measure></unitNumerator><unitDenominator><measure>shares</measure></unitDenominator></divide></unit>'
    text+='<dei:EntityCentralIndexKey>123</dei:EntityCentralIndexKey><dei:DocumentType>10-Q</dei:DocumentType><dei:DocumentPeriodEndDate>2026-06-30</dei:DocumentPeriodEndDate>'
    for tag,c,p in [('Revenues',120,100),('OperatingIncomeLoss',24,15),('NetIncomeLoss',20,12),('EarningsPerShareDiluted',2,1.2),('NetCashProvidedByUsedInOperatingActivities',25,16)]:
        for ctx,v in [('C',c),('P',p)]:text+=f'<us-gaap:{tag} contextRef="{ctx}" unitRef="{"eps" if tag=="EarningsPerShareDiluted" else "usd"}">{v}</us-gaap:{tag}>'
    raw=(text+'</xbrl>').encode();receipt=dict(observed_at='2026-07-31T12:00:00+00:00',sha256=hashlib.sha256(raw).hexdigest(),filing=dict(type='10-Q',period_of_report_date='20260630',filing_date='20260731',accession_number='0000000123-26-000001',source_url='https://www.sec.gov/Archives/example'))
    return raw,receipt


class QualityTests(unittest.TestCase):
    def test_original_ytd_comparatives_and_independent_numbers(self):
        raw,r=fixture();f=parse_original(raw,r,'123','2026-08-01T00:00:00+00:00')
        self.assertTrue(f['qualified']);self.assertAlmostEqual(f['metrics']['revenue_growth'],.2)
        self.assertEqual(audit_fundamental(raw,r,f,'123','2026-08-01T00:00:00+00:00')['facts_checked'],10)
        f['current']['revenue']+=1
        with self.assertRaises(AssertionError):audit_fundamental(raw,r,f,'123','2026-08-01T00:00:00+00:00')

    def test_future_observation_and_stale_reports_are_rejected(self):
        raw,r=fixture()
        for decision in ('2026-07-31T11:59:59+00:00','2027-03-01T00:00:00+00:00'):
            with self.assertRaises(DataUnavailable):parse_original(raw,r,'123',decision)

    def test_wrong_currency_hash_or_issuer_cannot_be_used(self):
        raw,r=fixture()
        with self.assertRaises(DataUnavailable):parse_original(raw,r,'456','2026-08-01T00:00:00+00:00')
        with self.assertRaises(DataUnavailable):parse_original(raw+b' ',r,'123','2026-08-01T00:00:00+00:00')
        changed=raw.replace(b'iso4217:USD',b'iso4217:EUR');r['sha256']=hashlib.sha256(changed).hexdigest()
        with self.assertRaises(DataUnavailable):parse_original(changed,r,'123','2026-08-01T00:00:00+00:00')

    def rows(self):
        return [dict(ticker=f'T{i}',cik=str(i),sic=sic,price_usd=20,fundamental=dict(qualified=True,metrics=dict(revenue_growth=.1+i*.01,eps_growth=.2+i*.01,margin_change=.01))) for i,sic in enumerate(['2011','2022','3511','3611','5011','5111','5811','5911','7311','8011','8711','3711'])]

    def test_business_rank_not_extreme_price_return_and_funded_whole_plan(self):
        rows=self.rows();chosen=choose(rows,2000);self.assertEqual(len(chosen),10)
        plan=plan_orders(chosen,{},2000,2000);self.assertEqual(audit_plan(chosen,plan,{},2000,2000,{})['status'],'PASS')
        self.assertTrue(all(float(o['quantity']).is_integer() for o in plan['orders']))
        rows[0]['relative_strength']=100000
        self.assertEqual([r['ticker'] for r in choose(rows,2000)],[r['ticker'] for r in chosen])

    def test_too_little_cash_and_retained_round_trip(self):
        chosen=choose(self.rows(),2000)
        with self.assertRaises(ValueError):plan_orders(chosen,{},2000,50)
        shares={r['ticker']:3 for r in chosen};p=plan_orders(chosen,shares,2000,100)
        self.assertEqual(p['orders'],[])


if __name__=='__main__':unittest.main()
