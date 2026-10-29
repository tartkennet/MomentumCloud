const test=require('node:test'),assert=require('node:assert/strict');
const {validate}=require('../api/portfolio'),ui=require('../public/investment');
const actual=require('../public/data/h3-display.json');
test('SEK delivery preserves identity and never accepts a fabricated anchor-free NAV',()=>{
 validate(structuredClone(actual));
 const wrong=structuredClone(actual);wrong.metrics={nav_sek:100000,spy_nav_sek:100000};wrong.anchor=null;
 assert.throws(()=>validate(wrong));
 const live=structuredClone(actual);live.broker_orders_enabled=true;assert.throws(()=>validate(live));
});
test('empty and single-session charts never interpolate fake history',()=>{
 assert.doesNotMatch(ui.chart([],390),/<svg/);
 assert.doesNotMatch(ui.chart([{nav_sek:100000,spy_sek:100000,date:'2026-10-29'}],390),/<svg/);
 assert.equal(ui.pct(null),'—');assert.equal(ui.esc('<img>'),'&lt;img&gt;');
});
test('chart uses real coordinates and refuses missing currency intervals',()=>{
 const rows=[{nav_sek:100000,spy_sek:100000,date:'2026-10-29'},{nav_sek:101000,spy_sek:99000,date:'2026-10-30'}];
 assert.match(ui.chart(rows,390),/viewBox="0 0 390 285"/);assert.doesNotMatch(ui.chart(rows,390),/NaN|Infinity/);
 rows[1].nav_sek=null;assert.doesNotMatch(ui.chart(rows,390),/<svg/);
 assert.equal(ui.statistics(rows).sharpe,null);assert.equal(ui.statistics(rows).dd,null);
});
