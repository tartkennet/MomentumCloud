"""Exercise the unified user journal and preserved mobile/dark UI without credentials."""
import json,sys,threading,shutil
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
from datetime import datetime
sys.path.insert(0,str(Path('tests').resolve()))
from test_best_v2 import formation
from best_v2_user import initialize,export
import best_v2_execution as execution
from playwright.sync_api import sync_playwright

def main():
    _,r,_=formation();source=json.loads(Path('data/best-v2-user-start.json').read_text())
    for row,h in zip(r['signal']['selection']['rows'],source['holdings']):row.update(ticker=h['ticker'],price_usd=h['mark_usd'])
    r['signal']['selection']['month']='2026-11';r['signal']['quotes']={h['ticker']:h['mark_usd'] for h in source['holdings']}
    r['fx']={'usdsek':source['fx_rate_sek_per_usd']};now=datetime.fromisoformat('2026-11-09T22:00:00+00:00')
    state=initialize(source,r,now);execution.register(state,type('Data',(),{'sessions':['2026-11-09']})(),now)
    r=export(state,r,now);r.update(delivery={'verified':True},operations={'delayed':False})
    r['paper'].update(automation_verified=True,effective_status='MONITORING',delivery_blockers=[])
    server=ThreadingHTTPServer(('127.0.0.1',8767),partial(SimpleHTTPRequestHandler,directory='public'));threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as pw:
            b=pw.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium'),headless=True)
            for width in (1440,390,320):
                page=b.new_page(viewport={'width':width,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.add_init_script("localStorage.setItem('momentum-theme','dark')")
                page.route('**/api/best-v2',lambda route:route.fulfill(content_type='application/json',body=json.dumps(r)))
                page.goto('http://127.0.0.1:8767/index.html',wait_until='networkidle')
                assert page.locator('#hero-value').inner_text().replace('\xa0',' ').startswith('25')
                assert page.locator('#positions .paper-holding').count()==10
                assert page.locator('#transactions').inner_text().count('Rekonstruerat startköp')==10
                assert page.locator('[data-paper-reconstruction]').count()==0
                assert page.evaluate("document.documentElement.dataset.theme==='dark'")
                for tab in ('overview','portfolio','trades','statistics','settings'):
                    page.locator('nav [data-tab='+tab+']').click();page.locator('#'+tab).wait_for(state='visible')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,tab)
                r['delivery']['verified']=False;r['paper'].update(automation_verified=False,effective_status='BLOCKED',delivery_blockers=['USER_ACCOUNT_COLLECTION_FAILED'])
                page.reload(wait_until='networkidle');page.locator('nav [data-tab=portfolio]').click()
                assert page.locator('#positions .paper-holding').count()==10
                assert 'HANDEL PAUSAD' in page.locator('#delivery').inner_text();assert not errors,errors
                r['delivery']['verified']=True;r['paper'].update(automation_verified=True,effective_status='MONITORING',delivery_blockers=[])
                page.close()
            b.close()
        print('USER_PAPER_BROWSER_PASS: one account, ten initialization trades, five tabs, dark theme, blocked refresh retains holdings; 1440/390/320')
    finally:server.shutdown()
if __name__=='__main__':main()
