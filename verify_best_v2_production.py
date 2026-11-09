"""Read-only production checks. Never creates orders or changes account capital."""
import json
import re,math
import shutil
import time
import urllib.request
import urllib.error
import http.client
from pathlib import Path

BASE='https://momentum-cloud.vercel.app'

def get(path):
    for attempt in range(1,4):
        started=time.monotonic()
        try:
            with urllib.request.urlopen(BASE+path,timeout=30) as r:
                body=r.read();status=r.status
            print('BEST_V2_PRODUCTION_HTTP',json.dumps(dict(path=path,http=status,bytes=len(body),attempt=attempt,seconds=round(time.monotonic()-started,3))),flush=True)
            return status,body
        except urllib.error.HTTPError as e:return e.code,e.read()
        except (urllib.error.URLError,TimeoutError,http.client.IncompleteRead) as exc:
            print('BEST_V2_PRODUCTION_READ_RETRY',json.dumps(dict(path=path,attempt=attempt,error=type(exc).__name__)),flush=True)
            if attempt==3:raise
            time.sleep(2)

def main():
    output=Path('best_v2_production_check');output.mkdir(exist_ok=True)
    status,home=get('/')
    assert status==200 and b'/best-v2-app.js' in home, 'PRODUCTION_V2_VIEW_NOT_BEST'
    checks={'root':dict(http=status,model='Momentum 10 BEST v2')}
    for endpoint in ('health','dashboard','h3','portfolio','quality','avanza10','best','best-v2'):
        status,body=get('/api/'+endpoint);data=json.loads(body)
        assert status in (200,503),(endpoint,status)
        assert isinstance(data,dict),endpoint
        checks[endpoint]=dict(http=status,reported_status=data.get('status'),errors=data.get('errors'))
        if endpoint=='best-v2':
            for attempt in range(6):
                if status==200 and data.get('promotion_ready'):break
                time.sleep(10);status,body=get('/api/best-v2');data=json.loads(body)
            assert status==200 and data.get('promotion_ready'), 'PRODUCTION_BEST_NOT_READY'
            assert data['paper']['automation_verified'] and not data['live_approved'] and not data['broker_orders_enabled']
            if data['paper'].get('execution_policy'):
                assert data['technical_ready'] is True and data['trading_outcome']['status']
                if not data['paper']['paper_started']:assert data['trading_success'] is False and not data['paper']['trades']
            if data.get('account_id'):
                assert data['account_id']=='best-v2-user-simulation-2026-11-09'
                assert data['paper']['historical_start_count']==10 and data['paper']['initialization_kind']=='SIMULATED_HISTORICAL_INITIALIZATION'
                assert sum(bool(t.get('initialization_kind')) for t in data['paper']['trades'])==10
                assert all(t['execution_at'] is None and t['actual_execution'] is False for t in data['paper']['trades'] if t.get('initialization_kind'))
                if data['paper']['prospective_trade_count']==0:assert not data['trading_success']
            members=data['signal']['selection']['rows'];assert len(members)==10
            assert len({r['cik'] for r in members})==10 and all(r['instrument_type']=='CS' and r['ticker']!='SPY' for r in members)
            checks['best-v2'].update(account_id=data.get('account_id'),positions=len(data['paper']['positions']),historical_initializations=sum(bool(t.get('initialization_kind')) for t in data['paper']['trades']),http=status,targets=[r['ticker'] for r in members],initial_sek=data['paper']['initial_sek'],paper_started=data['paper']['paper_started'],execution_policy=data['paper'].get('execution_policy'))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser_path=shutil.which('google-chrome') or shutil.which('chromium')
        if not browser_path:raise RuntimeError('EXISTING_CI_BROWSER_NOT_AVAILABLE')
        browser=p.chromium.launch(executable_path=browser_path,headless=True)
        for width in (1440,390,320):
            page=browser.new_page(viewport=dict(width=width,height=900));errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(BASE+'/',wait_until='networkidle')
            page.locator('#overview-targets .ticker-pill').first.wait_for()
            if checks['best-v2'].get('account_id'):
                assert page.locator('[data-paper-reconstruction]').count()==0
                assert page.locator('#positions .paper-holding').count()==checks['best-v2']['positions']
                if data['paper']['nav_sek'] is not None:assert ''.join(re.findall(r'\d',page.locator('#hero-value').inner_text()))==str(math.floor(data['paper']['nav_sek']+.5))
                else:assert data['paper']['valuation_pending']
                assert 'Historiskt rekonstruerad' in page.locator('#account-caption').inner_text()
                assert page.locator('#transactions').inner_text().count('Rekonstruerat startköp')==10
            if checks['best-v2'].get('execution_policy'):
                page.locator('#execution-status').wait_for()
                assert 'fördröjda' in page.locator('#execution-status').inner_text()
            for tab in ('overview','portfolio','trades','statistics','settings'):
                page.locator('nav [data-tab='+tab+']').click();page.locator('#'+tab).wait_for(state='visible')
                assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),(width,tab)
            page.locator('#capital').fill('1');page.locator('#capital-form button').click()
            page.locator('nav [data-tab=portfolio]').click()
            names=page.locator('#targets h3').all_text_contents();assert names==checks['best-v2']['targets']
            assert 'KAPITALUNDERSKOTT' in page.locator('#funding').inner_text()
            page.locator('nav [data-tab=settings]').click();page.locator('#capital').fill('1000000');page.locator('#capital-form button').click()
            page.locator('nav [data-tab=portfolio]').click();assert page.locator('#targets h3').all_text_contents()==names
            assert not errors,errors
            page.locator('nav [data-tab=overview]').click();page.screenshot(path=str(output/('production-'+str(width)+'.png')))
            checks[str(width)]=dict(tabs=5,errors=0,capital_invariance=True,overflow=False)
            page.close()
        browser.close()
    (output/'checks.json').write_text(json.dumps(checks,indent=2))
    print('BEST_V2_PRODUCTION_CHECK',json.dumps(checks),flush=True)

if __name__=='__main__':main()
