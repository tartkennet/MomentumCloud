'use strict';

const $ = id => document.getElementById(id);
const storageKey = 'momentum-avanza10-paper-v1';
const fields = ['capital', 'cash', 'holdings', 'excluded'];
const kr = new Intl.NumberFormat('sv-SE', {style: 'currency', currency: 'SEK', maximumFractionDigits: 0});
const stockholm = new Intl.DateTimeFormat('sv-SE', {
  dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Stockholm'
});
const nyMonth = new Intl.DateTimeFormat('sv-SE', {year: 'numeric', month: '2-digit', timeZone: 'America/New_York'});
const monthName = new Intl.DateTimeFormat('sv-SE', {month: 'long', year: 'numeric', timeZone: 'UTC'});
let report = {};

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
    for (const key of fields) if (typeof saved[key] === 'string') $(key).value = saved[key];
    document.documentElement.dataset.theme = localStorage.getItem('momentum-theme') === 'dark' ? 'dark' : 'light';
  } catch {}
}

function item(tag, content, className) {
  const node = document.createElement(tag);
  node.textContent = content;
  if (className) node.className = className;
  return node;
}

function facts(node, pairs) {
  node.replaceChildren(...pairs.map(([name, value]) => {
    const pair = document.createElement('div');
    pair.append(item('dt', name), item('dd', value));
    return pair;
  }));
}

function settings() {
  const capital = Number($('capital').value);
  const holdings = Avanza10Plan.parseHoldings($('holdings').value);
  const cash = $('cash').value === '' ? (Object.keys(holdings).length ? 0 : capital) : Number($('cash').value);
  const excluded = new Set($('excluded').value.toUpperCase().split(/[\s,]+/).filter(Boolean));
  return {capital, cash, holdings, excluded};
}

function draw() {
  const input = settings();
  const now = new Date();
  const result = Avanza10Plan.plan(report, input, now);
  const selected = report.avanza10?.selection;
  const month = nyMonth.format(now);
  const [year, monthNumber] = month.split('-').map(Number);
  const next = monthName.format(new Date(Date.UTC(year, monthNumber, 1)));
  $('status').textContent = result.risk === false ? 'Riskkontroll aktiv' : result.selectionReady ?
    'Månadsurval verifierat för simulering' : 'DATA BLOCKED · signaler pausade';
  $('regime').textContent = result.risk === true ? 'RISK ON' : result.risk === false ? 'RISK OFF' : 'Marknadsläge saknas';
  const checked = report.delivery?.verified && Number.isFinite(Date.parse(report.generated_at)) ?
    stockholm.format(new Date(report.generated_at)) : 'Saknas';
  const selectionText = selected?.month === month ? 'Första verifierade körningen i ' + next :
    'Vid nästa verifierade körning i innevarande månad';
  facts($('facts'), [
    ['Senast verifierade uppdatering', checked],
    ['Stängningskurser', report.price_as_of || 'Saknas'],
    ['Valutafix', report.fx?.date || 'Saknas'],
    ['Månadsurvalets kursdatum', selected?.as_of || 'Saknas'],
    ['Nästa ombalansering', selectionText],
    ['Aktuell datatäckning', Number.isFinite(report.coverage) ? Math.round(report.coverage * 100) + ' % · krav 90 %' : 'Saknas']
  ]);
  $('notice').textContent = (report.errors || []).join(' ') || (result.marketVerified ?
    'Signalerna använder observerade stängningskurser och uppskattade kostnader.' :
    'Källan saknar en aktuell, verifierad observation. Inga nya affärssignaler visas.');
  $('budget').textContent = `${result.targetCount} av 10 mål · ${result.fundedCount} finansierade eller befintliga · ${kr.format(result.remainingCash)} kvar av angiven kassa efter köpreserver`;
  $('empty').hidden = result.rows.length > 0;
  $('signals').replaceChildren(...result.rows.map(row => {
    const card = item('article', '', 'signal');
    card.append(item('h3', row.rank ? `${row.rank}. ${row.ticker}` : row.ticker),
      item('p', row.name || ''), item('span', row.signal, 'tag'));
    const details = document.createElement('dl');
    details.className = 'facts';
    facts(details, [
      ['Innehav → mål', `${row.current} → ${row.target ?? '—'}`],
      ['Antal i signal', row.quantity || '—'],
      ['Ordervärde ca', row.amount == null ? '—' : kr.format(row.amount)],
      ['Köpreserv', row.reserved ? kr.format(row.reserved) : '—']
    ]);
    card.append(details, item('p', row.reason || '', 'caption'));
    return card;
  }));
}

function update() {
  try { draw(); $('form-error').textContent = ''; }
  catch (error) { $('form-error').textContent = error.message; $('signals').replaceChildren(); $('budget').textContent = ''; }
}

async function load() {
  try {
    const response = await fetch('/api/quality', {cache: 'no-store'});
    report = await response.json();
  } catch {
    report = {errors: ['Den verifierade källan gick inte att hämta.']};
  }
  update();
}

loadSettings();
$('settings').addEventListener('submit', event => {
  event.preventDefault();
  update();
  if (!$('form-error').textContent) {
    try { localStorage.setItem(storageKey, JSON.stringify(Object.fromEntries(fields.map(key => [key, $(key).value])))); } catch {}
  }
});
$('theme').addEventListener('click', () => {
  const mode = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = mode;
  try { localStorage.setItem('momentum-theme', mode); } catch {}
});
load();
setInterval(load, 5 * 60 * 1000);
