/* Whole-share sizing for the separately versioned Avanza paper decision aid. */
(function (root) {
  'use strict';
  const version = 'avanza10-paper-v1';
  const slots = 10;
  const validNumber = value => Number.isFinite(value) && value > 0;
  const tickerPattern = /^[A-Z][A-Z0-9.-]{0,14}$/;
  const monthFormat = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'America/New_York', year: 'numeric', month: '2-digit'
  });

  function parseHoldings(text) {
    const holdings = {};
    for (const line of text.trim().toUpperCase().split(/\n/).filter(line => line.trim())) {
      const [ticker, raw, extra] = line.trim().split(/\s+/);
      const quantity = Number(raw);
      if (!tickerPattern.test(ticker) || !/^\d+$/.test(raw) || extra ||
          !Number.isSafeInteger(quantity) || quantity <= 0 || Object.hasOwn(holdings, ticker)) {
        throw new Error('Ange varje innehav på egen rad, till exempel AAPL 3. Använd hela aktier och en rad per ticker.');
      }
      holdings[ticker] = quantity;
    }
    return holdings;
  }

  function buyCost(quantity, price, fx) {
    if (!quantity) return 0;
    const notional = quantity * price * 1.02;
    const usd = notional + Math.max(1, notional * .0025) + notional * .004;
    return Math.ceil(usd * fx * 100) / 100;
  }

  function affordable(price, fx, budget, limit = Number.MAX_SAFE_INTEGER) {
    let low = 0;
    let high = Math.min(limit, Math.floor(budget / (price * fx)));
    while (low < high) {
      const mid = low + Math.ceil((high - low) / 2);
      if (buyCost(mid, price, fx) <= budget) low = mid;
      else high = mid - 1;
    }
    return low;
  }

  function targetRows(rows, capital, fx, excluded) {
    const selected = [];
    const issuers = new Set();
    const industries = new Map();
    const divisions = new Map();
    for (const row of rows) {
      if (excluded.has(row.ticker) || issuers.has(row.cik) || !validNumber(row.price_usd)) continue;
      const industry = String(row.sic).slice(0, 2);
      if ((industries.get(industry) || 0) >= 2 || (divisions.get(row.division) || 0) >= 4) continue;
      const target = affordable(row.price_usd, fx, capital / slots);
      if (!target) continue;
      selected.push({...row, target, rank: selected.length + 1});
      issuers.add(row.cik);
      industries.set(industry, (industries.get(industry) || 0) + 1);
      divisions.set(row.division, (divisions.get(row.division) || 0) + 1);
      if (selected.length === slots) break;
    }
    return selected;
  }

  function plan(report, settings, now = new Date()) {
    const {capital, cash, holdings, excluded} = settings;
    if (!validNumber(capital) || capital > 1e9 || !Number.isFinite(cash) || cash < 0 || cash > 1e9) {
      throw new Error('Ange ett positivt portföljkapital och en tillgänglig kassa på minst 0 kr.');
    }
    const snapshot = report.avanza10;
    const fx = report.fx?.usdsek;
    const month = monthFormat.format(now);
    const current = report.delivery?.verified === true && !report.operations?.delayed &&
      snapshot?.version === version && snapshot.market_verified && snapshot.quotes_as_of === report.price_as_of &&
      Number.isFinite(Date.parse(report.generated_at)) && Date.parse(report.generated_at) <= +now &&
      +now - Date.parse(report.generated_at) <= 4 * 86400000 &&
      Number.isFinite(Date.parse(report.price_as_of)) && Date.parse(report.price_as_of) <= +now &&
      +now - Date.parse(report.price_as_of) <= 5 * 86400000;
    const risk = current && typeof report.risk_on === 'boolean' ? report.risk_on : null;
    const selection = snapshot?.selection;
    const selectionReady = risk === true && validNumber(fx) && snapshot.selection_verified &&
      selection?.month === month && validNumber(selection.usdsek) && Array.isArray(selection.rows);
    const target = selectionReady ? targetRows(selection.rows, capital, selection.usdsek, excluded) : [];
    const rows = target.map(row => ({
      ...row, current: holdings[row.ticker] || 0, price: snapshot.quotes[row.ticker], buy: 0, reserved: 0
    }));
    const targetNames = new Set(rows.map(row => row.ticker));
    let available = Math.floor(cash * 100) / 100;

    // Reserve one whole share per new position before topping up any position.
    for (const row of rows) {
      if (row.current || !validNumber(row.price)) continue;
      const cost = buyCost(1, row.price, fx);
      if (cost > Math.min(available, capital / slots)) continue;
      row.buy = 1;
      row.reserved = cost;
      available = Math.round((available - cost) * 100) / 100;
    }
    for (const row of rows) {
      if (!validNumber(row.price) || row.current >= row.target) continue;
      const budget = Math.max(0, capital / slots - row.current * row.price * fx);
      row.buy = affordable(row.price, fx, Math.min(available + row.reserved, budget), row.target - row.current);
      const cost = buyCost(row.buy, row.price, fx);
      available = Math.round((available + row.reserved - cost) * 100) / 100;
      row.reserved = cost;
    }

    for (const row of rows) {
      const delta = row.target - row.current;
      row.signal = delta < 0 && validNumber(row.price) ? 'MINSKA' : row.buy ? 'KÖP' : row.current ? 'BEHÅLL' : 'KASSA';
      row.quantity = row.signal === 'MINSKA' ? -delta : row.buy;
      row.amount = validNumber(row.price) && row.quantity ? row.quantity * row.price * fx : null;
      row.reason = !validNumber(row.price) ? 'Verifierad dagskurs saknas' :
        delta > row.buy ? 'Kassa eller prisgräns begränsar köpet' : '';
    }
    for (const [ticker, quantity] of Object.entries(holdings)) {
      if (targetNames.has(ticker)) continue;
      const sell = risk === false || selectionReady;
      const price = snapshot?.quotes[ticker];
      rows.push({ticker, current: quantity, target: sell ? 0 : null, quantity: sell ? quantity : 0,
        amount: sell && validNumber(fx) && validNumber(price) ? quantity * price * fx : null,
        signal: sell ? 'SÄLJ' : 'PAUS', reason: risk === false ? 'RISK OFF' : selectionReady ? 'Utanför målet' : 'Verifierat underlag saknas'});
    }
    return {risk, selectionReady, rows, targetCount: target.length,
      fundedCount: rows.filter(row => row.rank && row.current + row.buy > 0).length,
      remainingCash: available, marketVerified: current, fx};
  }

  const api = {version, slots, parseHoldings, buyCost, plan};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Avanza10Plan = api;
})(globalThis);
