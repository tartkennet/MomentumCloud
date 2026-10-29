const test=require('node:test'),assert=require('node:assert/strict');
const {validate}=require('../api/portfolio'),ui=require('../public/investment');
const actual=require('../public/data/h3-display.json');
const handler=require('../api/portfolio');
test('SEK delivery preserves identity and never accepts a fabricated anchor-free NAV',()=>{
 validate(structuredClone(actual));
 const wrong=structuredClone(actual);wrong.metrics={nav_sek:100000,spy_nav_sek:100000};wrong.anchor=null;
 assert.throws(()=>validate(wrong));
 const live=structuredClone(actual);live.broker_orders_enabled=true;assert.throws(()=>validate(live));
});
test('empty and single-session charts never interpolate fake history',()=>{
 assert.doesNotMatch(ui.chart([],390),/class="value-chart"/);
 assert.doesNotMatch(ui.chart([{nav_sek:100000,spy_sek:100000,date:'2026-10-29'}],390),/class="value-chart"/);
 assert.equal(ui.pct(null),'—');assert.equal(ui.esc('<img>'),'&lt;img&gt;');
});
test('chart uses real coordinates and refuses missing currency intervals',()=>{
 const rows=[{nav_sek:100000,spy_sek:100000,date:'2026-10-29'},{nav_sek:101000,spy_sek:99000,date:'2026-10-30'}];
 assert.match(ui.chart(rows,390),/viewBox="0 0 390 285"/);assert.doesNotMatch(ui.chart(rows,390),/NaN|Infinity/);
 rows[1].nav_sek=null;assert.doesNotMatch(ui.chart(rows,390),/<svg/);
 assert.equal(ui.statistics(rows).sharpe,null);assert.equal(ui.statistics(rows).dd,null);
});
test('portfolio API delivers an actual waiting state and fails closed on missing delivery',async t=>{
 const data=structuredClone(actual);data.generated_at=new Date().toISOString();
 const h3=structuredClone(require('../public/data/h3.json'));h3.operations.next_expected_attempt_at=new Date(Date.now()+3600000).toISOString();
 t.mock.method(global,'fetch',async url=>({ok:true,json:async()=>url.includes('h3-display.json')?structuredClone(data):structuredClone(h3)}));
 const response=()=>({setHeader(){},status(code){this.code=code;return this},json(body){this.body=body;return this}});
 let res=response();await handler({},res);assert.equal(res.code,200);assert.equal(res.body.metrics,null);assert.equal(res.body.delivery.synchronized,true);
 global.fetch=async()=>{throw Error('unavailable')};res=response();await handler({},res);
 assert.equal(res.code,503);assert.equal(res.body.status,'DELIVERY_BLOCKED');assert.equal(res.body.pending_intentions,null);assert.equal(res.body.broker_orders_enabled,false);
});
