"""Browser fixture verification without market secrets or simulated account history."""
import json,sys,threading,shutil
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from functools import partial
sys.path.insert(0,str(Path('tests').resolve()))
from test_best_v2 import formation
from best_v2_forward import initialize,decide
from avanza10_forward import summarize
from quality_account_audit import audit_account
import audit_best_v2
from playwright.sync_api import sync_playwright

def main():
    data,r,now=formation();s=initialize(r,now);decide(s,r,data,now)
    s['audits']={k:audit_account(s,k,k=='benchmark') for k in ('strategy','benchmark')}
    p=summarize(s,r['signal'],now);p.update(model='momentum10-best-v2',automation_verified=True,effective_status=p['status'],delivery_blockers=[],statistics_audit=audit_best_v2.account(s,p))
    r.update(paper=p,technical_readiness={'status':'PASS','funded':True,'signal':{'status':'PASS'}},delivery={'verified':True},operations={'delayed':False},errors=[])
    server=ThreadingHTTPServer(('127.0.0.1',8766),partial(SimpleHTTPRequestHandler,directory='public'))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    try:
        with sync_playwright() as pw:
            browser_path=shutil.which('google-chrome') or shutil.which('chromium')
            if not browser_path:raise RuntimeError('EXISTING_CI_BROWSER_NOT_AVAILABLE')
            b=pw.chromium.launch(executable_path=browser_path,headless=True)
            for width in (1440,390,320):
                page=b.new_page(viewport={'width':width,'height':900});errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.add_init_script("const RealDate=Date;const fixed=Date.parse('2026-11-06T10:01:00Z');window.Date=class extends RealDate{constructor(...args){super(...(args.length?args:[fixed]));}static now(){return fixed;}};")
                page.route('**/api/best-v2',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(r)))
                page.goto('http://127.0.0.1:8766/best-v2.html',wait_until='networkidle')
                page.locator('#overview-targets .ticker-pill').first.wait_for()
                for tab in ('overview','portfolio','trades','statistics','settings'):
                    page.locator('nav [data-tab='+tab+']').click();page.locator('#'+tab).wait_for(state='visible')
                    page.wait_for_timeout(200)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,tab)
                page.locator('#capital').fill('1');page.locator('#capital-form button').click()
                page.locator('nav [data-tab=portfolio]').click()
                names=page.locator('#targets h3').all_text_contents();assert len(names)==10
                assert 'KAPITALUNDERSKOTT' in page.locator('#funding').inner_text()
                page.locator('nav [data-tab=settings]').click();page.locator('#capital').fill('1000000');page.locator('#capital-form button').click()
                page.locator('nav [data-tab=portfolio]').click();assert page.locator('#targets h3').all_text_contents()==names
                page.reload(wait_until='networkidle');page.locator('#targets h3').first.wait_for(state='visible')
                assert page.locator('#capital').input_value()=='1000000'
                assert page.locator('#targets h3').all_text_contents()==names
                assert not errors,errors
                results.append(dict(width=width,tabs=5,overflow=False,capital_invariance=True,errors=0))
                page.close()
            b.close()
        print('BEST_V2_BROWSER_FIXTURE_PASS',json.dumps(results),flush=True)
    finally:server.shutdown()
if __name__=='__main__':main()
