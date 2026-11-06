/* Whole-share sizing for the separately versioned Avanza paper decision aid. */
(function (root) {
  'use strict';
  const version = 'avanza10-paper-v2';
  const slots = 10;
  const maxMoney = Number.MAX_SAFE_INTEGER / 100;
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

  function membership(rows, excluded) {
    const selected = [];
    const issuers = new Set();
    for (const row of rows) {
      if (excluded.has(row.ticker) || issuers.has(row.cik) || !validNumber(row.price_usd)) continue;
      const industry = String(row.sic).slice(0, 2);
      if (selected.filter(x => x.industry === industry).length >= 2 ||
          selected.filter(x => x.division === row.division).length >= 4) continue;
      selected.push({...row, industry, rank: selected.length + 1});
      issuers.add(row.cik);
      if (selected.length === slots) break;
    }
    return selected;
  }

  const money = value => Math.round(value * 100) / 100;
  const ceilMoney = value => Math.ceil(value * 100) / 100;
  const sum = (rows, value) => rows.reduce((total, row) => total + value(row), 0);

  function minimums(rows, priceKey, fx) {
    const cost = row => buyCost(1, row[priceKey], fx);
    const cents = row => Math.round(cost(row) * 100);
    const total = sum(rows, cents) / 100;
    const capital = Math.max(Math.round(total * 100), ...rows.flatMap(row => [
      cents(row) * 5,
      Math.ceil(sum(rows.filter(x => x.industry === row.industry), cents) * 10 / 3),
      sum(rows.filter(x => x.division === row.division), cents) * 2
    ])) / 100;
    return {total, capital};
  }

  function allocation(rows, fx, capital) {
    for (const row of rows) {
      row.target = 1;
      row.allocation = buyCost(1, row.price_usd, fx);
    }
    for (const row of rows) {
      const rest = rows.filter(x => x !== row);
      const budget = Math.min(capital / slots, capital * .20,
        capital * .30 - sum(rest.filter(x => x.industry === row.industry), x => x.allocation),
        capital * .50 - sum(rest.filter(x => x.division === row.division), x => x.allocation),
        capital - sum(rest, x => x.allocation));
      row.target = Math.max(1, affordable(row.price_usd, fx, Math.max(0, budget)));
      row.allocation = buyCost(row.target, row.price_usd, fx);
    }
  }

  function plan(report, settings, now = new Date()) {
    const {capital, cash, holdings, excluded} = settings;
    if ((capital !== null && (!validNumber(capital) || capital > maxMoney)) ||
        !Number.isFinite(cash) || cash < 0 || cash > maxMoney) {
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
    const rows = selectionReady ? membership(selection.rows, excluded) : [];
    const targetNames = new Set(rows.map(row => row.ticker));
    const targetCount = rows.length;
    for (const row of rows) {
      row.current = holdings[row.ticker] || 0;
      row.price = snapshot.quotes[row.ticker];
      row.buy = 0;
      row.reserved = 0;
    }

    const monthly = targetCount === slots ? minimums(rows, 'price_usd', selection.usdsek) : null;
    const live = monthly && rows.every(row => validNumber(row.price)) ? minimums(rows, 'price', fx) : null;
    const planningCapital = monthly ? Math.max(capital ?? cash, monthly.capital) : null;
    if (monthly) allocation(rows, selection.usdsek, planningCapital);
    const minimumCash = live ? money(sum(rows.filter(row => !row.current), row => buyCost(1, row.price, fx))) : null;
    const targetCost = live ? money(sum(rows, row => buyCost(row.target, row.price, fx))) : null;
    const targetCash = live ? money(sum(rows, row => buyCost(Math.max(0, row.target - row.current), row.price, fx))) : null;
    let available = Math.floor(cash * 100) / 100;
    const capitalShortfall = live && capital !== null ? money(Math.max(0, live.capital - capital)) : 0;
    const cashShortfall = minimumCash === null ? null : money(Math.max(0, minimumCash - available));
    const targetCashShortfall = targetCash === null ? null : money(Math.max(0, targetCash - available));
    const limitCapital = live ? capital ?? Math.max(cash, live.capital) : 0;
    const baseExposure = row => row.current ? row.current * row.price * fx * 1.02 : buyCost(1, row.price, fx);
    const withinLimits = live && rows.every(row => baseExposure(row) <= limitCapital * .20 + .01 &&
      sum(rows.filter(x => x.industry === row.industry), baseExposure) <= limitCapital * .30 + .01 &&
      sum(rows.filter(x => x.division === row.division), baseExposure) <= limitCapital * .50 + .01);

    if (withinLimits && capitalShortfall === 0 && cashShortfall === 0) {
      for (const row of rows) {
        row.buy = row.current ? 0 : 1;
        row.reserved = buyCost(row.buy, row.price, fx);
        available = money(available - row.reserved);
      }
      for (const row of rows) {
        if (row.current >= row.target) continue;
        const rest = rows.filter(x => x !== row);
        const exposure = x => x.current * x.price * fx * 1.02 + x.reserved;
        const budget = Math.min(limitCapital * .20,
          limitCapital * .30 - sum(rest.filter(x => x.industry === row.industry), exposure),
          limitCapital * .50 - sum(rest.filter(x => x.division === row.division), exposure))
          - row.current * row.price * fx * 1.02;
        const bound = Math.max(row.reserved, money(Math.min(available + row.reserved, budget)));
        row.buy = affordable(row.price, fx, bound, row.target - row.current);
        const cost = buyCost(row.buy, row.price, fx);
        available = money(available + row.reserved - cost);
        row.reserved = cost;
      }
    }

    for (const row of rows) {
      const delta = row.target === undefined ? null : row.target - row.current;
      row.signal = live && delta < 0 ? 'MINSKA' : row.buy ? 'KÖP' : row.current ? 'BEHÅLL' : 'KASSA';
      row.quantity = row.signal === 'MINSKA' ? -delta : row.buy;
      row.amount = validNumber(row.price) && row.quantity ? row.quantity * row.price * fx : null;
      row.targetCost = live ? buyCost(row.target, row.price, fx) : null;
      row.reason = !validNumber(row.price) ? 'Verifierad dagskurs eller prisbasis saknas' :
        !live ? 'Hela målportföljen kan ännu inte prissättas' :
        delta > row.buy ? 'Kapital, kassa eller viktgräns begränsar köpet' : '';
    }
    for (const [ticker, quantity] of Object.entries(holdings)) {
      if (targetNames.has(ticker)) continue;
      const sell = risk === false || Boolean(live);
      const price = snapshot?.quotes[ticker];
      rows.push({ticker, current: quantity, target: sell ? 0 : null, quantity: sell ? quantity : 0,
        amount: sell && validNumber(fx) && validNumber(price) ? quantity * price * fx : null,
        signal: sell ? 'SÄLJ' : 'PAUS', reason: risk === false ? 'RISK OFF' : sell ? 'Utanför målet' : 'Verifierat underlag saknas'});
    }
    return {risk, selectionReady, rows, targetCount, planningCapital, minimumTotal: live?.total ?? null,
      minimumCapital: live?.capital ?? null, targetCost, minimumCash, capitalShortfall, cashShortfall,
      targetCash, targetCashShortfall, remainingCash: available, marketVerified: current, fx,
      fundedCount: rows.filter(row => row.rank && row.current + row.buy > 0).length};
  }

  const api = {version, slots, parseHoldings, buyCost, plan};
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Avanza10Plan = api;
})(globalThis);
