const test=require('node:test'),assert=require('node:assert/strict');
const {validate}=require('../api/portfolio'),ui=require('../public/investment');
const actual=require('../public/data/h3-display.json');
const handler=require('../api/portfolio');
const {monitor}=require('../lib/h3-monitor');

test('future cron display never clears an overdue publication, including weekends and DST',()=>{
 const h3={operations:{next_expected_attempt_at:'2026-10-30T06:35:00Z',delay_grace_minutes:90}};
 let result=monitor(h3,Date.parse('2026-10-30T08:49:00Z'));
 assert.equal(result.delayed,true);assert.equal(result.expected_attempt_at,'2026-10-30T06:35:00Z');
 assert.equal(result.next_scheduled_attempt_at,'2026-10-30T09:35:00.000Z');
 result=monitor(h3,Date.parse('2026-10-31T09:35:00Z'));
 assert.equal(result.next_scheduled_attempt_at,'2026-11-03T00:35:00.000Z');
 assert.equal(result.delayed,true);
 assert.equal(monitor(h3,Date.parse('2026-10-30T08:05:00Z')).delayed,false);
});

test('overdue H3 keeps its deadline, suppresses intentions and never creates holdings or trades',async t=>{
 const data=structuredClone(actual),h3=structuredClone(require('../public/data/h3.json'));
 h3.generated_at='2026-10-30T06:21:08Z';h3.operations.next_expected_attempt_at='2026-10-30T06:35:00Z';
 h3.pending_intentions={signal_date:'2026-10-29',targets:[{ticker:'SPY',weight:1}]};
 t.mock.method(Date,'now',()=>Date.parse('2026-10-30T08:49:00Z'));
 t.mock.method(global,'fetch',async url=>({ok:true,json:async()=>structuredClone(url.includes('h3-display.json')?data:h3)}));
 const res={setHeader(){},status(code){this.code=code;return this},json(body){this.body=body;return this}};
 await handler({},res);
 assert.equal(res.body.delivery.collection_delayed,true);assert.equal(res.body.pending_intentions,null);
 assert.equal(res.body.h3.next_attempt,'2026-10-30T09:35:00.000Z');
 assert.equal(res.body.h3.expected_attempt,'2026-10-30T06:35:00Z');
 assert.deepEqual(res.body.positions,[]);assert.deepEqual(res.body.trades,[]);
 // A verified publication recovers status; its original intention is read only.
 h3.generated_at='2026-10-30T08:52:00Z';h3.operations.next_expected_attempt_at='2026-10-30T09:35:00Z';
 await handler({},res);assert.equal(res.body.delivery.collection_delayed,false);
 assert.deepEqual(res.body.pending_intentions,h3.pending_intentions);
 assert.deepEqual(res.body.trades,[]);
});

test('recorded plans are labelled as unfilled intentions and escape symbols',()=>{
 const html=ui.intentions({pending_intentions:{signal_date:'2026-10-29',targets:[{ticker:'<SPY>',weight:.78}]}});
 assert.match(html,/inga genomförda affärer/);assert.match(html,/78,00 %/);assert.match(html,/&lt;SPY&gt;/);
 assert.match(ui.intentions({errors:['delayed'],pending_intentions:null}),/inväntar verifierad uppföljning/);
});
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
