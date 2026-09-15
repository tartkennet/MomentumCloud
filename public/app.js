const number = (value, digits = 1) => value == null ? "—" : new Intl.NumberFormat("sv-SE", {maximumFractionDigits: digits}).format(value);
const pct = value => value == null ? "—" : `${value >= 0 ? "+" : ""}${number(value, 1)} %`;
const money = value => value == null ? "—" : new Intl.NumberFormat("sv-SE", {style:"currency", currency:"USD", maximumFractionDigits:2}).format(value);
const compact = value => value == null ? "—" : new Intl.NumberFormat("sv-SE", {notation:"compact", maximumFractionDigits:1}).format(value);
const tone = value => value == null ? "" : value >= 0 ? "positive" : "negative";
const escapeHtml = value => String(value ?? "").replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));

function metric(label, value, className = "") { return `<div class="metric"><small>${escapeHtml(label)}</small><strong class="${className}">${escapeHtml(value)}</strong></div>`; }

function stockCard(row, chip) { return `<article class="stock-card">
  <div class="stock-head"><div><span class="rank">${row.target_rank ? `MÅL ${row.target_rank} · ` : ""}RANK ${row.rank}</span><div class="ticker">${escapeHtml(row.ticker)}</div></div><span class="score">${number(row.score,1)}</span></div>
  <div class="stock-meta"><span>Kurs<b>${money(row.price_usd)}</b></span><span>Vikt<b>${number(row.weight_pct,1)} %</b></span><span>Antal<b>${number(row.quantity,0)}</b></span></div>
  <span class="signal-chip">${escapeHtml(chip)}</span>
</article>`; }

function render(data) {
  document.querySelector("#market-date").textContent = data.market_date || "Ingen data";
  document.querySelector("#hero-copy").textContent = data.risk?.risk_on
    ? "Marknaden är positiv. Månadens kapitalanpassade målportfölj är låst; Buy now visar bara köp som faktiskt återstår att genomföra."
    : "Riskregimen är avstängd. Inga nya köp görs och målportföljen hålls i kassa.";
  const regime = document.querySelector("#regime-card");
  regime.className = `regime-card ${data.risk?.risk_on ? "on" : "off"}`;
  document.querySelector("#regime-status").textContent = data.risk?.status || "VÄNTAR";
  document.querySelector("#regime-reason").textContent = data.risk?.reason || "SPY / SMA200";

  const buys = data.buy_now || [];
  document.querySelector("#buy-count").textContent = buys.length;
  const buyGrid = document.querySelector("#buy-grid");
  buyGrid.className = buys.length ? "stock-grid" : "stock-grid empty-state";
  buyGrid.innerHTML = buys.length
    ? buys.map(row => stockCard(row, "KÖP")).join("")
    : data.risk?.risk_on
      ? "Inga öppna köporder. Kontrollera målportföljen och registrerade innehav."
      : "RISK OFF – inga köp tillåts.";

  const target = data.target_portfolio || [];
  document.querySelector("#target-count").textContent = target.length;
  const targetGrid = document.querySelector("#target-grid");
  targetGrid.className = target.length ? "stock-grid" : "stock-grid empty-state";
  targetGrid.innerHTML = target.length
    ? target.map(row => stockCard(row, "MÅLPORTFÖLJ")).join("")
    : data.risk?.risk_on ? "Målportföljen kunde inte skapas." : "100 % kassa i RISK OFF.";

  const statusLabel = {TARGET:"Mål", RESERVE:"Reserv", UNAFFORDABLE:"För dyr"};
  document.querySelector("#candidate-rows").innerHTML = (data.candidates || []).map(row => `<tr><td>${row.rank}</td><td><b>${escapeHtml(row.ticker)}</b></td><td><span class="candidate-status ${String(row.selection_status || "").toLowerCase()}">${escapeHtml(statusLabel[row.selection_status] || "—")}</span></td><td>${number(row.score,1)}</td><td>${money(row.price_usd)}</td><td class="${tone(row.momentum_12_2_pct)}">${pct(row.momentum_12_2_pct)}</td><td class="${tone(row.momentum_6_2_pct)}">${pct(row.momentum_6_2_pct)}</td><td>${number(row.volatility_pct,1)} %</td><td>${compact(row.adv20_usd)}</td></tr>`).join("");

  const holdings = data.holdings || [];
  const holdingGrid = document.querySelector("#holding-grid");
  holdingGrid.className = holdings.length ? "metric-grid" : "metric-grid empty-state";
  holdingGrid.innerHTML = holdings.length ? holdings.map(row => metric(`${row.ticker} · ${number(row.quantity,0)} st`, pct(row.return_pct), tone(row.return_pct))).join("") : "Inga registrerade innehav.";

  document.querySelector("#rebalance-badge").textContent = data.rebalance_due ? "OMALLOKERING NU" : "Nästa månad";
  const signals = data.signals || [];
  const signalList = document.querySelector("#signal-list");
  signalList.className = signals.length ? "signal-list" : "signal-list empty-state";
  signalList.innerHTML = signals.length ? signals.map(row => `<div class="signal-row"><b class="action ${row.action.toLowerCase()}">${escapeHtml(row.action)}</b><strong>${escapeHtml(row.ticker)}</strong><small>${escapeHtml(row.reason.replaceAll("_"," "))}</small></div>`).join("") : "Inga åtgärder just nu.";

  const risk = data.risk || {};
  document.querySelector("#risk-metrics").innerHTML = [
    metric("SPY", money(risk.spy_close)), metric("SMA200", money(risk.spy_sma200)),
    metric("Stop loss", `${number(data.config?.stop_loss_pct,0)} %`), metric("Regim", risk.status || "—")
  ].join("");
  const exposure = risk.exposure_pct || 0;
  document.querySelector("#exposure-ring").textContent = `${number(exposure,0)}%`;
  document.querySelector(".ring").style.setProperty("--exposure", `${exposure}%`);

  const perf = data.performance || {};
  document.querySelector("#performance-grid").innerHTML = [
    metric("Portfölj", pct(perf.portfolio_return_pct), tone(perf.portfolio_return_pct)),
    metric("SPY 1 månad", pct(perf.spy_1m_pct), tone(perf.spy_1m_pct)),
    metric("CAGR", pct(perf.cagr_pct), tone(perf.cagr_pct)), metric("Sharpe", number(perf.sharpe,2)),
    metric("Sortino", number(perf.sortino,2)), metric("Max drawdown", pct(perf.max_drawdown_pct), tone(perf.max_drawdown_pct))
  ].join("");
  document.querySelector("#performance-note").textContent = perf.status || "";

  const history = (data.history || []).slice(-30).reverse();
  const historyList = document.querySelector("#history-list");
  historyList.className = history.length ? "timeline" : "timeline empty-state";
  historyList.innerHTML = history.length ? history.map(row => `<div class="timeline-row"><span>${escapeHtml(row.EntryDate || "—")}</span><b>${escapeHtml(row.Ticker || "—")}</b><span>Rank ${escapeHtml(row.EntryRank || "—")} · ${pct(row.Return_Since_Entry_pct)}</span></div>`).join("") : "Historik skapas efter första produktionskörningen.";

  document.querySelector("#limitation").textContent = data.limitation || "Current limitation: survivorship bias";
  const system = data.system || {};
  document.querySelector("#system-grid").innerHTML = [
    ["Senaste uppdatering", data.generated_at ? new Date(data.generated_at).toLocaleString("sv-SE") : "Väntar"],
    ["GitHub Action", system.github_action_status || "—"], ["Polygon", system.polygon_status || "—"],
    ["Urval", `${number(system.eligible_security_count,0)} aktier`], ["Modell", data.config?.selection_model || "—"]
  ].map(([label,value]) => `<div class="status-row"><span>${escapeHtml(label)}</span><b class="ok">${escapeHtml(value)}</b></div>`).join("");
}

async function load() {
  try {
    let response = await fetch("/api/dashboard", {cache:"no-store"});
    if (!response.ok) response = await fetch("/data/dashboard.json", {cache:"no-store"});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    render(await response.json());
  } catch (error) {
    document.querySelector("#hero-copy").textContent = "Ingen framgångsrik produktionskörning är publicerad ännu.";
    console.error(error);
  }
}
load();
