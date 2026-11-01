"""Resumable SEC-only gap review; never changes economic code or old panels.

The SEC submissions feed is discovery only. Availability and identity come
from the original SGML header; facts come from its unchanged XBRL attachment.
"""
import argparse,copy,gzip,hashlib,json,re,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import requests
from historical_quality_facts import available_at,parse_historical
from historical_quality_audit import audit_fundamental
from quality_strategy import division
from quality_sources import DataUnavailable
from momentum_core_data import atomic_json


def sha(raw):return hashlib.sha256(raw).hexdigest()


class SEC:
    def __init__(self,root,offline=False):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.offline=offline
        self.session=requests.Session()
        self.session.headers['User-Agent']='MomentumCloud research (github.com/tartkennet/MomentumCloud)'
    def get(self,url):
        if not re.fullmatch(r'https://(?:www|data)\.sec\.gov/[A-Za-z0-9_./-]+',url):raise DataUnavailable('UNTRUSTED_SEC_URL')
        key=sha(url.encode());asset=self.root/(key+'.gz');receipt=self.root/(key+'.json')
        if receipt.exists():
            meta=json.loads(receipt.read_text());raw=gzip.decompress(asset.read_bytes())
            assert meta['url']==url and sha(raw)==meta['sha256'];return raw,meta
        if self.offline:raise DataUnavailable('UNCACHED_SEC_ORIGINAL')
        time.sleep(.15)
        try:r=self.session.get(url,timeout=(5,12))
        except requests.RequestException as e:raise DataUnavailable('SEC_NETWORK_'+type(e).__name__) from None
        if r.status_code!=200:raise DataUnavailable('SEC_HTTP_'+str(r.status_code))
        if len(r.content)>180_000_000:raise DataUnavailable('SEC_OVERSIZE')
        raw=r.content;meta=dict(url=url,sha256=sha(raw),observed_at=datetime.now(timezone.utc).isoformat(),asset=asset.name)
        asset.write_bytes(gzip.compress(raw,mtime=0));atomic_json(receipt,meta);return raw,meta


def header(raw,accession,cik):
    text=raw.split(b'</SEC-HEADER>',1)[0].decode('utf-8')
    def field(pattern):
        found=re.findall(pattern,text,re.M)
        if len(set(found))!=1:raise DataUnavailable('SEC_HEADER_IDENTITY:'+pattern)
        return found[0]
    actual=field(r'^ACCESSION NUMBER:\s*([0-9-]+)\s*$')
    if actual!=accession:raise DataUnavailable('SEC_WRONG_ACCESSION')
    entities=[]
    for block in re.split(r'^FILER:\s*$',text,flags=re.M)[1:]:
        ci=re.search(r'CENTRAL INDEX KEY:\s*(\d+)',block)
        sic=re.search(r'STANDARD INDUSTRIAL CLASSIFICATION:[^\n]*\[(\d{4})\]',block)
        if ci and int(ci[1])==int(cik) and sic:entities.append(sic[1])
    if len(set(entities))!=1:raise DataUnavailable('SEC_FILER_SIC_UNRESOLVED')
    return dict(id=accession,accession_number=accession,
        type=field(r'^CONFORMED SUBMISSION TYPE:\s*([^\s]+)\s*$'),
        filing_date=field(r'^FILED AS OF DATE:\s*(\d{8})\s*$'),
        period_of_report_date=field(r'^CONFORMED PERIOD OF REPORT:\s*(\d{8})\s*$'),
        acceptance_datetime=field(r'^<ACCEPTANCE-DATETIME>(\d{14})\s*$'),sic=entities[0])


def instance(raw):
    found=[]
    for block in raw.split(b'<DOCUMENT>')[1:]:
        filename=re.search(rb'<FILENAME>([^\r\n]+)',block)
        if not filename or not filename[1].lower().endswith(b'.xml'):continue
        match=re.search(rb'<XML>\s*(<\?xml.*?</xbrl>)\s*</XML>',block,re.S|re.I)
        if match:found.append((filename[1].decode(),match[1]))
    if len(found)!=1:raise DataUnavailable('SEC_AMBIGUOUS_XBRL_ATTACHMENT')
    return found[0]


def submissions(client,cik,day):
    raw,meta=client.get('https://data.sec.gov/submissions/CIK'+str(cik).zfill(10)+'.json')
    data=json.loads(raw);groups=[data['filings']['recent']]
    for item in data['filings'].get('files',[]):
        if item['filingFrom']<=day and (item['filingTo']>=day or not any(
            form in ('10-K','10-Q','10-K/A','10-Q/A') and filed<=day
            for group in groups for form,filed in zip(group['form'],group['filingDate']))):
            b,_=client.get('https://data.sec.gov/submissions/'+item['name']);groups.append(json.loads(b))
    rows=[]
    for group in groups:
        for i,form in enumerate(group['form']):
            if form not in ('10-K','10-Q','10-K/A','10-Q/A') or group['filingDate'][i]>day:continue
            rows.append({k:v[i] for k,v in group.items() if isinstance(v,list) and len(v)==len(group['form'])})
    return sorted(rows,key=lambda r:(r['filingDate'],r['accessionNumber']),reverse=True),meta


def review(row,day,client):
    out=copy.deepcopy(row);out['original_gap']=row.get('reason');cutoff=day+'T08:17:00+00:00'
    evidence=[]
    try:
        choices,discovery=submissions(client,row['cik'],day);out['discovery']=discovery
        chosen=None;amendments=[]
        for candidate in choices:
            if chosen and candidate['filingDate']<chosen[0]['filingDate']:break
            accession=candidate['accessionNumber']
            url='https://www.sec.gov/Archives/edgar/data/'+str(int(row['cik']))+'/'+accession.replace('-','')+'/'+accession+'.txt'
            raw,meta=client.get(url);f=header(raw,accession,row['cik']);f['source_url']=url
            evidence.append(dict(receipt=meta,header=f))
            if available_at(f)>datetime.fromisoformat(cutoff):continue
            if f['type'].endswith('/A'):amendments.append(f);continue
            chosen=(candidate,raw,meta,f)
            # Older originals cannot supersede this eligible original. Newer
            # amendments above were checked against their own acceptance times.
            break
        if not chosen:raise DataUnavailable('SEC_NO_AS_OF_PERMITTED_ORIGINAL')
        candidate,raw,meta,f=chosen
        out['sec_header']=f
        if any(a['filing_date']>=f['filing_date'] for a in amendments):raise DataUnavailable('AS_OF_AMENDMENT_REQUIRES_REVIEW')
        if f['type'] not in ('10-K','10-Q'):raise DataUnavailable('SEC_UNSUPPORTED_FORM')
        out.update(sic=f['sic'],division=division(f['sic']),classification_vintage='ORIGINAL_SEC_HEADER')
        if not division(f['sic']):out.update(resolved=True,data_status='OUT_OF_SCOPE_INDUSTRY',reason=None);return out
        name,xml=instance(raw)
        receipt=dict(observed_at=meta['observed_at'],filing=f,sha256=sha(xml),source='original SEC complete submission attachment',xml_filename=name,sgml_sha256=meta['sha256'])
        out['sec_receipt']=receipt
        facts=parse_historical(xml,receipt,row['cik'],cutoff)
        audit=audit_fundamental(xml,receipt,facts,row['cik'],cutoff)
        out.update(resolved=True,data_status='VERIFIED',fundamental=facts,audit=audit,reason=None)
    except (DataUnavailable,AssertionError,ValueError,KeyError) as e:
        out.update(resolved=False,data_status='DATA_GAP',reason=str(e) if isinstance(e,DataUnavailable) else type(e).__name__)
    finally:out['sec_evidence']=evidence
    return out


def run(panels,history,output,day=None,max_rows=200,retry_transient=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True);client=SEC(output/'sec-originals')
    prior=json.loads(Path(history).read_text());summary=[]
    for source in sorted(Path(panels).glob('*.panel.json')):
        date=source.name[:10]
        if day and date!=day:continue
        panel=json.loads(source.read_text());dest=output/(date+'.supplement.json')
        done=json.loads(dest.read_text()) if dest.exists() else dict(date=date,source_panel_sha256=sha(source.read_bytes()),rows=[])
        assert done['source_panel_sha256']==sha(source.read_bytes())
        existing={r['ticker']:r for r in done['rows']}
        if retry_transient:
            existing={t:r for t,r in existing.items() if not str(r.get('reason','')).startswith(('SEC_NETWORK_','SEC_HTTP_429','SEC_HTTP_5','SEC_OVERSIZE'))}
        capacity=next(r['block']['panel'] for r in prior['cases'][:4] if r.get('block',{}).get('panel',{}).get('date')==date)
        missing={r['ticker'] for r in capacity['gaps']};todo=[r for r in panel['rows'] if r['ticker'] in missing and r['ticker'] not in existing][:max_rows]
        for row in todo:
            updated=review(row,date,client);existing[row['ticker']]=updated;done['rows']=list(existing.values());atomic_json(dest,done)
            print('SEC_GAP',date,row['ticker'],updated['resolved'],updated.get('reason'),flush=True)
        resolved=sum(r['resolved'] for r in existing.values());coverage=capacity['coverage']+resolved/capacity['capacity']
        summary.append(dict(date=date,original_coverage=capacity['coverage'],supplemented=resolved,coverage=round(coverage,4),minimum_coverage=.9,gate_pass=coverage>=.9,
            reviewed=len(existing),expected_gaps=len(missing),reason_counts=dict(Counter(r.get('reason') or 'RESOLVED' for r in existing.values())),
            remaining=[dict(ticker=r['ticker'],original_reason=r['original_gap'],reason=r.get('reason')) for r in existing.values() if not r['resolved']]))
    report=dict(status='NO_GO_INSUFFICIENT_EVIDENCE',generated_at=datetime.now(timezone.utc).isoformat(),economic_model_changed=False,earlier_results_changed=False,
        historical_backtest_certified=False,financial_go=False,live_approved=False,broker_orders_enabled=False,source_coverage=summary)
    atomic_json(output/'source-review.json',report);return report


def apply_verified(panels,supplements,destination):
    """Build a separate panel set by reproducing every resolution offline."""
    import shutil
    panels=Path(panels);supplements=Path(supplements);destination=Path(destination)
    assert panels.resolve()!=destination.resolve(),'ORIGINAL_PANELS_ARE_IMMUTABLE'
    assert not destination.exists(),'DESTINATION_ALREADY_EXISTS'
    for saved in supplements.glob('*.supplement.json'):
        rows=json.loads(saved.read_text())['rows']
        assert not any(str(r.get('reason','')).startswith(('SEC_HTTP_','SEC_NETWORK_','SEC_OVERSIZE','UNCACHED_SEC_')) for r in rows),'INCOMPLETE_SEC_TRANSPORT'
    shutil.copytree(panels,destination)
    client=SEC(supplements/'sec-originals',offline=True);changes=[]
    for source in sorted(panels.glob('*.panel.json')):
        saved=json.loads((supplements/(source.name[:10]+'.supplement.json')).read_text())
        assert saved['source_panel_sha256']==sha(source.read_bytes())
        panel=json.loads(source.read_text());mapping={r['ticker']:r for r in panel['rows']}
        assert len({r['ticker'] for r in saved['rows']})==len(saved['rows'])
        for row in saved['rows']:
            original=mapping[row['ticker']]
            assert not original['resolved'],'CANNOT_REPLACE_VERIFIED_ORIGINAL'
            if not row['resolved']:continue
            reproduced=review(original,panel['date'],client)
            assert reproduced==row,'SUPPLEMENT_FAILED_OFFLINE_REPRODUCTION'
            mapping[row['ticker']]=reproduced
            changes.append(dict(date=panel['date'],ticker=row['ticker'],status=row['data_status']))
        panel['rows']=[mapping[r['ticker']] for r in panel['rows']]
        atomic_json(destination/source.name,panel)
    atomic_json(destination/'supplement-application.json',dict(status='PASS',offline=True,changes=changes))
    return changes


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--panels',required=True);p.add_argument('--history',default='public/data/quality-history.json');p.add_argument('--output',required=True);p.add_argument('--day');p.add_argument('--max-rows',type=int,default=200);p.add_argument('--retry-transient',action='store_true');p.add_argument('--apply-to');a=p.parse_args()
    if a.apply_to:apply_verified(a.panels,a.output,a.apply_to)
    else:run(a.panels,a.history,a.output,a.day,a.max_rows,a.retry_transient)
