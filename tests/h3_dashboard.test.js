const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const handler=require('../api/h3');
const ui=require('../public/h3');
const actual=JSON.parse(fs.readFileSync('public/data/h3.json','utf8'));
const copy=()=>structuredClone(actual);
function response(){return {headers:{},setHeader(k,v){this.headers[k]=v},status(code){this.code=code;return this},json(body){this.body=body;return this}}}

test('delivery rejects a changed model, source or enabled trading flag',()=>{
  handler.validate(copy());
  for(const [key,value] of [['model','other'],['source_fingerprint','other'],['live_approved',true],['broker_orders_enabled',true]]){
    const bad=copy();bad[key]=value;assert.throws(()=>handler.validate(bad));
  }
});
test('fresh real waiting journal has null performance and no fake fills',async t=>{
  const data=copy();data.operations.next_expected_attempt_at=new Date(Date.now()+3600000).toISOString();
  t.mock.method(global,'fetch',async()=>({ok:true,json:async()=>data}));
  const res=response();await handler({},res);
  assert.equal(res.code,200);assert.equal(res.body.delivery.verified,true);
  assert.equal(res.body.metrics,null);assert.equal(res.body.sessions,0);assert.deepEqual(res.body.curve,[]);
});
test('late monitor and failed delivery never show actionable intentions',async t=>{
  const data=copy();data.operations.next_expected_attempt_at='2020-01-01T00:00:00Z';data.pending_intentions={targets:[{ticker:'SPY',weight:1}]};
  t.mock.method(global,'fetch',async()=>({ok:true,json:async()=>data}));
  let res=response();await handler({},res);
  assert.equal(res.body.status,'MONITOR_DELAYED');assert.equal(res.body.pending_intentions,null);
  global.fetch=async()=>{throw new Error('unreachable')};
  res=response();await handler({},res);
  assert.equal(res.code,503);assert.equal(res.body.status,'DELIVERY_BLOCKED');assert.equal(res.body.delivery.verified,false);assert.equal(res.body.pending_intentions,null);
});
test('UI leaves empty or single-observation curves empty and escapes data',()=>{
  assert.doesNotMatch(ui.curve([]),/<svg/);assert.doesNotMatch(ui.curve([{date:'2026-10-29',nav:100000,spy_nav:100000}]),/<svg/);
  assert.equal(ui.pct(null),'—');assert.equal(ui.escape('<script>'), '&lt;script&gt;');
});
