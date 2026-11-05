const test = require('node:test');
const assert = require('node:assert/strict');
const {version, buyCost, parseHoldings, plan} = require('../public/avanza10-plan');
const now = new Date('2026-11-05T20:00:00Z');

function snapshot() {
  const rows = Array.from({length: 13}, (_, i) => ({
    ticker: 'S' + i, cik: 'C' + i, sic: 2000 + i * 100,
    division: 'Sector ' + Math.floor(i / 4), price_usd: i === 0 ? 550 : 42
  }));
  return {
    generated_at: '2026-11-05T19:00:00Z', price_as_of: '2026-11-04',
    delivery: {verified: true}, fx: {usdsek: 10}, risk_on: true,
    avanza10: {version, market_verified: true, selection_verified: true, quotes_as_of: '2026-11-04',
      selection: {month: '2026-11', usdsek: 10, rows},
      quotes: Object.fromEntries(rows.map(r => [r.ticker, r.price_usd]))}
  };
}
const settings = {capital: 40000, cash: 40000, holdings: {}, excluded: new Set()};

test('capital and cash do not alter the ten ranked stocks', () => {
  const r = snapshot();
  const full = plan(r, settings, now);
  const short = plan(r, {...settings, capital: 5000, cash: 3000}, now);
  assert.equal(full.targetCount, 10);
  assert.equal(full.fundedCount, 10);
  assert.deepEqual(short.rows.map(x => x.ticker), full.rows.map(x => x.ticker));
  assert.equal(short.rows[0].ticker, 'S0');
  assert.ok(short.rows.every(x => x.target >= 1 && Number.isInteger(x.target) && x.buy === 0));
  const cost = buyCost(1, 550, 10) + 9 * buyCost(1, 42, 10);
  assert.equal(short.minimumTotal, Number(cost.toFixed(2)));
  assert.equal(short.cashShortfall, Number((cost - 3000).toFixed(2)));
  assert.equal(short.capitalShortfall, Number((short.minimumCapital - 5000).toFixed(2)));
  assert.ok(short.minimumCapital >= buyCost(1, 550, 10) / .20);
  assert.equal(short.remainingCash, 3000);
  const excluded = plan(r, {...settings, excluded: new Set(['S0'])}, now);
  assert.equal(excluded.targetCount, 10);
  assert.equal(excluded.rows[0].ticker, 'S1');
});

test('whole shares respect cash while reporting the gap to fully funded targets', () => {
  const r = snapshot(), input = {...settings, capital: 60000, holdings: {S0: 2, OLD: 5, S5: 13}};
  const full = plan(r, input, now);
  const constrained = plan(r, {...input, cash: full.minimumCash}, now);
  assert.equal(constrained.rows.find(x => x.ticker === 'S0').signal, 'MINSKA');
  assert.equal(constrained.rows.find(x => x.ticker === 'S5').signal, 'BEHÅLL');
  assert.equal(constrained.rows.find(x => x.ticker === 'OLD').signal, 'SÄLJ');
  assert.equal(constrained.rows.filter(x => x.signal === 'KÖP').length, 8);
  assert.ok(constrained.rows.every(x => x.buy === undefined || x.buy <= 1));
  assert.equal(constrained.remainingCash, 0);
  assert.equal(constrained.cashShortfall, 0);
  assert.ok(constrained.targetCashShortfall > 0);
  assert.equal(plan(r, {...input, cash: full.minimumCash - 1}, now).rows.filter(x => x.buy > 0).length, 0);
});

test('fresh daily risk off takes precedence and unavailable data pauses exits', () => {
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

test('missing quote preserves the names and stops full-basket quotes and buys', () => {
  const r = snapshot();
  delete r.avanza10.quotes.S0;
  const result = plan(r, settings, now);
  assert.equal(result.targetCount, 10);
  assert.equal(result.rows[0].signal, 'KASSA');
  assert.equal(result.minimumTotal, null);
  assert.equal(result.fundedCount, 0);
  r.avanza10.selection.month = '2026-10';
  assert.equal(plan(r, settings, now).targetCount, 0);
});

test('zero entered capital shows a sized proposal and shortage from verified prices', () => {
  const r = snapshot(), input = {...settings, capital: null, cash: 0};
  const first = plan(r, input, now);
  assert.equal(first.targetCount, 10);
  assert.equal(first.minimumCash, first.minimumTotal);
  assert.equal(first.cashShortfall, first.minimumTotal);
  assert.equal(first.planningCapital, first.minimumCapital);
  assert.ok(first.rows.every(x => x.target >= 1 && x.targetCost > 0 && x.quantity === 0));
  r.avanza10.quotes.S0 = 650;
  const second = plan(r, input, now);
  assert.deepEqual(second.rows.map(x => x.target), first.rows.map(x => x.target));
  assert.ok(second.minimumTotal > first.minimumTotal);
});
