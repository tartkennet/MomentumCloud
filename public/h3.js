(function () {
  "use strict";
  const finite = value => typeof value === "number" && Number.isFinite(value);
  const num = (value, digits=2) => finite(value) ? value.toLocaleString("sv-SE", {minimumFractionDigits:digits, maximumFractionDigits:digits}) : "—";
  const pct = value => finite(value) ? `${value > 0 ? "+" : ""}${num(value)} %` : "—";
  const usd = value => finite(value) ? `${num(value)} USD` : "—";
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const stamp = value => value ? new Date(value).toLocaleString("sv-SE", {timeZone:"Europe/Stockholm", dateStyle:"medium", timeStyle:"short"}) : "—";
  const names = {PAPER_WAITING_FOR_SESSIONS:"Väntar på första sessionen", PAPER_COLLECTING:"Samlar framtida observationer", PAPER_ONLY:"Paper only", NO_GO:"Framåttestet klarar inte kraven", DATA_BLOCKED:"Dataproblem behöver kontrolleras", MONITOR_DELAYED:"Uppföljningen är försenad", DELIVERY_BLOCKED:"Journalen kan inte hämtas"};
  const gateNames = {at_least_30_periods:"30 fullständiga månadsperioder", positive_net_return:"Positiv nettoavkastning", beats_spy:"Bättre än SPY efter kostnader", drawdown:"Maximal nedgång högst 20 %", hit_rate:"Minst 50 % positiva perioder"};
  function metric(label, value, detail="") {return `<article class="h3-metric"><span>${escape(label)}</span><strong>${escape(value)}</strong>${detail ? `<small>${escape(detail)}</small>` : ""}</article>`;}
  function curve(rows) {
    if (rows.length < 2) return '<p class="h3-empty">Kurvan visas när minst två verkliga sessionsobservationer finns.</p>';
    const values=rows.flatMap(r=>[r.nav,r.spy_nav]);
    if (!values.every(finite)) return '<p class="h3-empty">Kurvans data behöver kontrolleras.</p>';
    const low=Math.min(...values), high=Math.max(...values), span=high-low || 1;
    const line=field=>rows.map((r,i)=>`${(i/(rows.length-1)*900+20).toFixed(2)},${(220-(r[field]-low)/span*190).toFixed(2)}`).join(" ");
    return `<svg class="h3-chart" viewBox="0 0 940 250" role="img" aria-label="Insamlat paper-portföljvärde för H3 och SPY"><line x1="20" y1="220" x2="920" y2="220" class="h3-chart-axis"/><polyline points="${line("spy_nav")}" class="h3-spy-line"/><polyline points="${line("nav")}" class="h3-nav-line"/><text x="20" y="245">${escape(rows[0].date)}</text><text x="920" y="245" text-anchor="end">${escape(rows.at(-1).date)}</text></svg><p class="h3-legend"><span>● H3 paper</span><span>● SPY efter kostnader</span></p>`;
  }
  function render(data) {
    const $ = id=>document.getElementById(id);
    const m=data.metrics, validation=data.validation || {}, errors=data.operations?.errors || [];
    const blocked=["DATA_BLOCKED","MONITOR_DELAYED","DELIVERY_BLOCKED"].includes(data.status);
    $("h3-status").textContent=names[data.status] || "Kontrollerar journalen";
    $("h3-status").className=`h3-status ${blocked ? "h3-status-error" : ""}`;
    $("h3-asof").textContent=data.as_of ? `Accepterad journal till ${data.as_of} · kontrollerad ${stamp(data.generated_at)}` : `Ingen paper-session registrerad · kontrollerad ${stamp(data.generated_at)}`;
    $("h3-metrics").innerHTML=[metric("Portföljvärde",usd(m?.FinalNAV_USD),m ? "Senast accepterade paper-värde" : "Planerat startkapital 100 000 USD"),metric("H3 sedan paper-start",pct(m?.TotalReturn_pct)),metric("SPY samma period",pct(m?.SPYTotalReturn_pct)),metric("Skillnad mot SPY",finite(m?.TotalEdgeVsSPY_pct)?`${num(m.TotalEdgeVsSPY_pct)} procentenheter`:"—"),metric("Maximal nedgång",pct(m?.DailyMaxDrawdown_pct)),metric("Sharpe",num(m?.DailySharpe_zero_rf),"Daglig, riskfri ränta 0"),metric("Handelskostnader",usd(m?.ActualFees_USD),"Simulerad kostnad 15 bp per sida"),metric("Observerade sessioner",num(data.sessions,0))].join("");
    const observed=validation.observed_periods || 0, required=validation.required_periods || 30;
    $("h3-progress").value=observed;$("h3-progress").max=required;
    $("h3-progress-copy").textContent=`${observed} av ${required} fullständiga månadsperioder · ${validation.remaining_periods ?? required} återstår`;
    $("h3-period-note").textContent=`Full prövning tidigast ${validation.earliest_assessment_month || "maj 2029"}. Första delmånaden räknas inte som en full period.`;
    const status=validation.status;
    $("h3-validation-status").textContent=status==="FORWARD_PASS_REVIEW_REQUIRED" ? "Finansiella framåtkrav klarade. Oberoende exekveringsprövning och ditt uttryckliga godkännande återstår." : status==="FORWARD_NO_GO" ? "Den förregistrerade framåtperioden klarar inte samtliga krav." : status==="DATA_BLOCKED" ? "Valideringen är spärrad av ett dataproblem." : "Samlar observationer. Ingen live-GO kan utfärdas ännu.";
    $("h3-curve").innerHTML=curve(data.curve || []);
    const holdings=data.holdings || [];
    $("h3-holdings").innerHTML=holdings.length ? holdings.map(r=>`<article class="h3-position"><div><b>${escape(r.ticker)}</b><small>${escape(r.sleeve)}${r.fractional_entitlement ? " · fraktionell rättighet" : ""}</small></div><span>${num(r.quantity,finite(r.quantity)&&Number.isInteger(r.quantity)?0:4)} st</span><strong>${finite(r.weight_pct)?num(r.weight_pct)+" %":"Vikt saknas"}</strong><span>${usd(r.value_usd)}</span></article>`).join("") : '<p class="h3-empty">Inga insamlade simulerade innehav ännu.</p>';
    $("h3-cash").textContent=m ? `Kassa ${usd(data.cash_usd)} · fordringar ${usd(data.receivables_usd)}` : "Startkapitalet är en inställning, inte ett registrerat paper-resultat.";
    const decision=data.latest_decision;
    $("h3-decision").textContent=decision ? `${decision.date}: ${decision.risk_on ? "Risk-on, allokering mellan momentumaktier och SPY" : "Risk-off, hela aktieportföljen till kassa"}.` : "Inget framåtriktat handelsbeslut är registrerat ännu.";
    $("h3-intentions").textContent=data.pending_intentions && !blocked ? `Registrerade intentioner för nästa observerade börsöppning: ${data.pending_intentions.targets.map(r=>`${r.ticker} ${num(100*r.weight,1)} %`).join(", ") || "kassa"}. Detta är simulering, inga brokerordrar.` : blocked ? "Inga aktuella intentioner visas medan journalen är spärrad eller försenad." : "Ingen simulerad order väntar på nästa börsöppning.";
    $("h3-trades").innerHTML=(data.recent_trades || []).slice().reverse().map(r=>`<div class="h3-trade"><span>${escape(r.date)}</span><b>${escape(r.ticker)}</b><span>${escape(({BUY:"Simulerat köp",SELL:"Simulerad försäljning",BUY_CANCELLED_NO_OPEN:"Köp annullerat, öppningskurs saknas"})[r.side] || "Företagshändelse")}</span><span>${num(r.quantity,2)} st · ${usd(r.fee)} kostnad</span></div>`).join("") || '<p class="h3-empty">Inga simulerade transaktioner har genomförts.</p>';
    const probe=data.operations?.readiness;
    const access=probe?.live_probe ? probe : probe?.last_live_probe;
    $("h3-readiness").textContent=access?.status==="PASS" ? `Dagskurser, historiskt register, splitar och utdelningar verifierade ${stamp(access.checked_at)}.` : "Marknadsåtkomsten inväntar verifiering eller kräver kontroll.";
    $("h3-execution").textContent="Handelsavgifter och slippage är modellerade vid 15 och 30 bp per sida. Spread, verkligt kurtage och likviditet i öppningsauktionen är ännu inte verifierade. Det spärrar livebedömning.";
    $("h3-errors").innerHTML=errors.length ? `<p class="h3-error-title">Visar senast accepterade journal. Aktuell insamling behöver kontrolleras.</p><ul>${errors.map(e=>`<li>${escape(e)}</li>`).join("")}</ul>` : '<p class="h3-ok">Inga rapporterade drift- eller datafel.</p>';
    $("h3-next").textContent=`Nästa schemalagda kontroll: ${stamp(data.operations?.next_expected_attempt_at)}. GitHub kan fördröja starten.`;
    $("h3-first").textContent=`Första observationsförsöket: ${stamp(data.schedule?.first_expected_attempt_at)} för sessionen 29 oktober 2026, när slutliga dagsdata finns.`;
    $("h3-gates").innerHTML=(validation.gates?.["15bp"] || []).map(g=>`<div class="h3-gate"><span>${escape(gateNames[g.gate] || g.gate)}</span><b>${data.sessions ? (g.pass ? "Uppnått hittills" : "Ej uppnått") : "Inväntar observationer"}</b></div>`).join("");
    const history=data.historical?.metrics;
    $("h3-history").innerHTML=history ? `<p>Utvecklingsdata 2024-01-01–2026-10-28. Samtliga 40 historiska scenarier passerar. Detta ingår inte i paper-journalen.</p><div class="h3-historical-metrics">${metric("Historisk H3",pct(history.TotalReturn_pct))}${metric("Historisk SPY",pct(history.SPYTotalReturn_pct))}${metric("Historisk nedgång",pct(history.DailyMaxDrawdown_pct))}${metric("Historisk Sharpe",num(history.DailySharpe_zero_rf))}</div>` : "Historikens verifierade sammanfattning kunde inte hämtas.";
  }
  async function load() {
    try {
      const response=await fetch("/api/h3",{cache:"no-store"});
      const data=await response.json();
      if (!data || data.model!=="momentum-diversified-regime-research-v1") throw new Error("Wrong observation response");
      render(data);
    } catch (_error) {
      document.getElementById("h3-status").textContent="Journalen kan inte hämtas";
      document.getElementById("h3-errors").textContent="Anslutningen till H3-uppföljningen fungerar inte. Tidigare värden är inte aktuella signaler.";
      document.getElementById("h3-intentions").textContent="Inga aktuella intentioner visas.";
    }
  }
  if (typeof module!=="undefined") module.exports={curve,escape,pct};
  if (typeof document!=="undefined") {load();setInterval(load,60000);}
}());
