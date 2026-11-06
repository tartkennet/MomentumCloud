const test=require('node:test');
const assert=require('node:assert/strict');
const handler=require('../api/avanza10');
const source=require('../public/data/quality-earnings.json');
const response=()=>({setHeader(){},status(c){this.code=c;return this;},json(b){this.body=b;return this;}});
function paper(){return {model:'avanza10-observed-paper-v1',mode:'PAPER_ONLY',live_approved:false,
 broker_orders_enabled:false,status:'BLOCKED',blockers:['UNFUNDED_OR_RISK_LIMITED_MINIMUM_BASKET'],
 generated_at:new Date().toISOString(),positions:[],trades:[],curve:[],
 statistics_audit:{status:'PASS'},audits:{strategy:{status:'PASS'},benchmark:{status:'PASS'}}};}
test('Avanza API never exposes frozen Quality trades as the new account',async t=>{
 const r=structuredClone(source);r.generated_at=new Date().toISOString();r.trades=[{ticker:'WRONG_ACCOUNT'}];
 r.avanza_paper=paper();t.mock.method(global,'fetch',async()=>({ok:true,json:async()=>r}));
 const res=response();await handler({},res);
 assert.equal(res.code,200);assert.equal(res.body.paper.automation_verified,true);
 assert.equal(res.body.paper.effective_status,'BLOCKED');assert.deepEqual(res.body.paper.trades,[]);
 assert.equal(res.body.trades,undefined);assert.equal(res.body.live_approved,false);
});
test('missing or wrong identity cannot become an active paper account',async t=>{
 const r=structuredClone(source);r.generated_at=new Date().toISOString();
 r.avanza_paper={...paper(),model:'momentum10-quality-earnings-net-v1'};
 t.mock.method(global,'fetch',async()=>({ok:true,json:async()=>r}));
 const res=response();await handler({},res);
 assert.equal(res.body.paper.automation_verified,false);assert.equal(res.body.paper.effective_status,'BLOCKED');
 assert.deepEqual(res.body.paper.trades,[]);assert.equal(res.body.paper.initial_sek,null);
 assert.throws(()=>handler.validatePaper({...paper(),positions:[{ticker:'SPY'}]}));
});
test('outage keeps the API explicitly blocked',async t=>{
 t.mock.method(global,'fetch',async()=>{throw Error('outage');});
 const res=response();await handler({},res);
 assert.equal(res.code,503);assert.equal(res.body.paper.automation_verified,false);
 assert.equal(res.body.broker_orders_enabled,false);
});
