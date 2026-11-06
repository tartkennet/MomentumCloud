"""Read-only production checks. Never creates orders or changes account capital."""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE='https://momentum-cloud.vercel.app'

def get(path):
    try:
        with urllib.request.urlopen(BASE+path,timeout=30) as r:return r.status,r.read()
    except urllib.error.HTTPError as e:return e.code,e.read()

def main():
    output=Path('best_production_check');output.mkdir(exist_ok=True)
    status,home=get('/')
    assert status==200 and b'/best-app.js' in home, 'PRODUCTION_ROOT_NOT_BEST'
    checks={'root':dict(http=status,model='Momentum 10 BEST')}
    for endpoint in ('health','dashboard','h3','portfolio','quality','avanza10','best'):
        status,body=get('/api/'+endpoint);data=json.loads(body)
        assert status in (200,503),(endpoint,status)
        assert isinstance(data,dict),endpoint
        checks[endpoint]=dict(http=status,reported_status=data.get('status'),errors=data.get('errors'))
        if endpoint=='best':
            for attempt in range(6):
                if status==200 and data.get('promotion_ready'):break
                time.sleep(10);status,body=get('/api/best');data=json.loads(body)
            assert status==200 and data.get('promotion_ready'), 'PRODUCTION_BEST_NOT_READY'
            assert data['paper']['automation_verified'] and not data['live_approved'] and not data['broker_orders_enabled']
            members=data['signal']['selection']['rows'];assert len(members)==10
            assert len({r['cik'] for r in members})==10 and all(r['instrument_type']=='CS' and r['ticker']!='SPY' for r in members)
            checks['best'].update(http=status,targets=[r['ticker'] for r in members],initial_sek=data['paper']['initial_sek'],paper_started=data['paper']['paper_started'])
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for width in (1440,390,320):
            page=browser.new_page(viewport=dict(width=width,height=900));errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(BASE+'/',wait_until='networkidle')
            page.locator('#overview-targets .ticker-pill').first.wait_for()
            for tab in ('overview','portfolio','trades','statistics','settings'):
                page.locator('nav [data-tab='+tab+']').click();page.locator('#'+tab).wait_for(state='visible')
                assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'),(width,tab)
            page.locator('#capital').fill('1');page.locator('#capital-form button').click()
            page.locator('nav [data-tab=portfolio]').click()
            names=page.locator('#targets h3').all_text_contents();assert names==checks['best']['targets']
            assert 'KAPITALUNDERSKOTT' in page.locator('#funding').inner_text()
            page.locator('nav [data-tab=settings]').click();page.locator('#capital').fill('1000000');page.locator('#capital-form button').click()
            page.locator('nav [data-tab=portfolio]').click();assert page.locator('#targets h3').all_text_contents()==names
            assert not errors,errors
            page.locator('nav [data-tab=overview]').click();page.screenshot(path=str(output/('production-'+str(width)+'.png')))
            checks[str(width)]=dict(tabs=5,errors=0,capital_invariance=True,overflow=False)
            page.close()
        browser.close()
    (output/'checks.json').write_text(json.dumps(checks,indent=2))
    print('BEST_PRODUCTION_CHECK',json.dumps(checks),flush=True)

if __name__=='__main__':main()
