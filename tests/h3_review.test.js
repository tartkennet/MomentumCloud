const test=require('node:test'),assert=require('node:assert/strict');
const ui=require('../public/h3-review'),d=require('../public/data/h3-first-review.json');
test('published evidence preserves weights, independent score math and original identity',()=>{
 assert.equal(d.audit.status,'PASS');assert.equal(d.positions.length,16);
 assert.ok(Math.abs(d.positions.reduce((sum,r)=>sum+r.weight,0)-1)<1e-12);
 for(const r of d.positions){if(r.ticker==='SPY'){assert.equal(r.rank,null);continue;}
  assert.ok(Math.abs(r.momentum_12_2/r.formation_volatility-r.risk_normalized_score)<1e-10);
  assert.ok(Math.abs(r.formation.end_split_adjusted_close/r.formation.start_split_adjusted_close-1-r.momentum_12_2)<1e-10);
  for(const m of [1,3,6,12])assert.equal(r.returns_latest[m].status,'PASS');
 }
 assert.equal(d.first_fill_review.original_identity_unchanged,true);assert.equal(d.first_fill_review.original_prefix_unchanged,true);
 assert.equal(d.first_fill_review.market_trade_rows,34);assert.equal(d.live_approved,false);assert.equal(d.broker_orders_enabled,false);
});
test('a missing monthly return is displayed as missing, never a fabricated zero',()=>{
 const html=ui.returnGrid({'1':{status:'MISSING'}});assert.match(html,/—/);assert.doesNotMatch(html,/0,00/);
});
test('stock report escapes provider and issuer text and separates targets from historical returns',()=>{
 const r=structuredClone(d.positions[0]);r.classification.name='<script>bad</script>';
 const html=ui.position(r);assert.match(html,/&lt;script&gt;/);assert.doesNotMatch(html,/<script>/);
 assert.match(html,/RANK 1/);assert.match(html,/SIC/);assert.match(html,/2026-10-30/);
});
