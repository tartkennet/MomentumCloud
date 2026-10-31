const test=require('node:test'),assert=require('node:assert/strict');
const ui=require('../public/stocks10.js');
test('missing curve is never fabricated',()=>assert.match(ui.chart([]),/saknas/));
test('chart separates replay and benchmark without arbitrary HTML',()=>{const s=ui.chart([{date:'<bad>',nav_sek:20000,spy_sek:20000},{date:'2026-10-28',nav_sek:15000,spy_sek:30000}]);assert.match(s,/Stocks10/);assert.match(s,/&lt;bad&gt;/);assert.doesNotMatch(s,/<bad>/);assert.match(s,/stroke-dasharray/)});
test('NO_GO and failed gates remain visible',()=>{const s=ui.variant({variant:'A',status:'NO_GO',completed:20,passed:0,gates:[{gate:'drawdown',pass:false,value:-30,requirement:'>= -20%'}]});assert.match(s,/NO_GO/);assert.match(s,/✕/);assert.match(s,/[−-]30/)});
