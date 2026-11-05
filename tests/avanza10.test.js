const test = require('node:test');
const assert = require('node:assert/strict');
const {version, buyCost, parseHoldings, plan} = require('../public/avanza10-plan');
const now = new Date('2026-11-05T20:00:00Z');

function snapshot() {
  const rows = Array.from({length: 13}, (_, i) => ({
    ticker: 'S' + i, cik: 'C' + i, sic: 2000 + i * 100,
    division: 'Sector ' + Math.floor(i / 4), price_usd: i === 0 ? 220 : 42
  }));
  return {
    generated_at: '2026-11-05T19:00:00Z', price_as_of: '2026-11-04',
    delivery: {verified: true}, fx: {usdsek: 10}, risk_on: true,
    avanza10: {version, market_verified: true, selection_verified: true, quotes_as_of: '2026-11-04',
      selection: {month: '2026-11', usdsek: 10, rows},
      quotes: Object.fromEntries(rows.map(r => [r.ticker, r.price_usd]))}
  };
}
const settings = {capital: 20000, cash: 20000, holdings: {}, excluded: new Set()};

test('funds ten whole-share positions after expensive and broker-excluded stocks', () => {
  const r = plan(snapshot(), {...settings, excluded: new Set(['S2'])}, now);
  assert.equal(r.targetCount, 10);
  assert.equal(r.fundedCount, 10);
  assert.ok(r.rows.every(x => x.signal === 'KÖP' && x.quantity === 4));
  assert.ok(!r.rows.some(x => ['S0', 'S2'].includes(x.ticker)));
  assert.equal(r.remainingCash, Number((20000 - r.rows.reduce((a, x) => a + x.reserved, 0)).toFixed(2)));
  assert.equal(r.rows[0].reserved, buyCost(4, 42, 10));
});

test('buys one per position before topping up and never uses planned sale proceeds', () => {
  const r = plan(snapshot(), {...settings, cash: 1000, holdings: {S4: 8, OLD: 5, S5: 4}}, now);
  assert.equal(r.rows.find(x => x.ticker === 'S4').signal, 'MINSKA');
  assert.equal(r.rows.find(x => x.ticker === 'S5').signal, 'BEHÅLL');
  assert.equal(r.rows.find(x => x.ticker === 'OLD').signal, 'SÄLJ');
  assert.equal(r.rows.filter(x => x.signal === 'KÖP').length, 2);
  assert.ok(r.rows.every(x => x.buy === undefined || x.buy <= 1));
  assert.ok(r.remainingCash >= 0);
  assert.equal(plan(snapshot(), {...settings, capital: 1000, cash: 1000}, now).targetCount, 0);
});

test('data failure pauses signals and fresh risk off takes precedence over selection', () => {
  const r = snapshot(), account = {...settings, holdings: {S1: 4}};
  r.risk_on = false;
  r.avanza10.selection_verified = false;
  let result = plan(r, account, now);
  assert.equal(result.rows[0].signal, 'SÄLJ');
  assert.equal(result.rows[0].amount, 1680);
  r.operations = {delayed: true};
  result = plan(r, account, now);
  assert.equal(result.risk, null);
  assert.equal(result.rows[0].signal, 'PAUS');
  assert.throws(() => parseHoldings('AAA 2\nAAA 3'));
  assert.throws(() => parseHoldings('AAA 1.5'));
  assert.deepEqual(parseHoldings('aaa 2\nBRK.B 1'), {AAA: 2, 'BRK.B': 1});
});

test('the frozen month remains stable while an unavailable daily price blocks a buy', () => {
  const r = snapshot();
  delete r.avanza10.quotes.S1;
  const result = plan(r, settings, now);
  assert.equal(result.rows[0].signal, 'KASSA');
  assert.equal(result.rows[0].rank, 1);
  assert.equal(result.fundedCount, 9);
  r.avanza10.selection.month = '2026-10';
  assert.equal(plan(r, settings, now).targetCount, 0);
});

test('whole-share savings can fund the tenth position above its slot guideline', () => {
  const r = snapshot();
  r.avanza10.selection.rows = r.avanza10.selection.rows.slice(0, 10);
  const result = plan(r, settings, now);
  assert.equal(result.targetCount, 10);
  assert.equal(result.fundedCount, 10);
  assert.equal(result.rows[0].ticker, 'S0');
  assert.equal(result.rows[0].quantity, 1);
  assert.ok(result.rows[0].reserved > 2000 && result.rows[0].reserved <= 4000);
  assert.ok(result.remainingCash >= 0);
  r.avanza10.selection.rows[0].price_usd = 500;
  assert.equal(plan(r, settings, now).targetCount, 9);
});
