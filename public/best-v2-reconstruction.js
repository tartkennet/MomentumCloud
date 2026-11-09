'use strict';
/* Read-only historical paper illustration. Never writes/rewrites the verified BEST account. */
(async function(){
  const $=id=>document.getElementById(id);
  const kr=n=>new Intl.NumberFormat('sv-SE',{style:'currency',currency:'SEK',maximumFractionDigits:0}).format(n);
  const cash=n=>new Intl.NumberFormat('sv-SE',{style:'currency',currency:'SEK',maximumFractionDigits:2}).format(n);
  const pc=n=>new Intl.NumberFormat('sv-SE',{maximumFractionDigits:2,signDisplay:'exceptZero'}).format(n)+' %';
  const e=(tag,value,cls)=>{const node=document.createElement(tag);if(value!==undefined)node.textContent=String(value);if(cls)node.className=cls;return node;};
  try{
    const r=await fetch('/data/best-v2-paper-start.json',{cache:'no-store'});
    if(!r.ok) return;
    const d=await r.json();
    if(d.kind!=='HYPOTHETICAL_PAPER_RECONSTRUCTION'||d.signal_model!=='momentum10-best-v2'||d.trade_day!=='2026-11-09'||d.holdings.length!==10) return;
    const fx=d.fx_rate_sek_per_usd;
    const items=d.holdings.map(h=>{
      const notional=h.quantity*h.open_usd, broker=Math.max(1,notional*.0025), cost=broker+notional*.004;
      return {...h,notional,cost,invested_sek:(notional+cost)*fx,value_sek:h.quantity*h.mark_usd*fx,pnl_sek:(h.quantity*h.mark_usd-notional-cost)*fx};
    });
    const invested=items.reduce((a,h)=>a+h.invested_sek,0), cashLeft=d.initial_sek-invested;
    if(cashLeft < -0.01 || items.some(h=>h.quantity<1 || !Number.isInteger(h.quantity)))return;
    const nav=cashLeft+items.reduce((a,h)=>a+h.value_sek,0),pnl=nav-d.initial_sek,percent=pnl/d.initial_sek*100;
    const note='Simulerade köp från 9 nov, baserade på öppningskurser. Inte utförda order i den automatiska journalen. FIGS överskred den ursprungliga köpgränsen. Värdering med senast sparade minutkurser och oförändrad referensvaluta.';
    function panel(title){
      const article=e('article',undefined,'panel');article.dataset.paperReconstruction='true';
      article.append(e('p','PAPERPORTFÖLJ · 9 NOV','eyebrow'),e('h2',title));return article;
    }
    const overview=$('overview');
    if(overview){
      const card=panel('Dagens simulerade innehav');
      const metrics=e('div',undefined,'metric-grid');
      for(const [label,value] of [['Portföljvärde',kr(nav)],['Förändring',kr(pnl)+' ('+pc(percent)+')'],['Investerat',kr(invested)],['Kassa',kr(cashLeft)]]){const metric=e('article',undefined,'metric');metric.append(e('p',label),e('strong',value));metrics.append(metric);}
      card.append(metrics,e('p',note+' Senaste kursobservation: '+new Intl.DateTimeFormat('sv-SE',{dateStyle:'short',timeStyle:'short',timeZone:'Europe/Stockholm'}).format(new Date(d.mark_observed_at)),'caption'));
      const anchor=overview.querySelector('.paper-grid')||overview.querySelector('.hero');
      anchor?.before(card);
    }
    function renderTable(container,head,values){
      const wrap=e('div',undefined,'table-scroll'),table=e('table'),thead=e('thead'),tr=e('tr');
      for(const h of head)tr.append(e('th',h));thead.append(tr);const tbody=e('tbody');
      for(const row of values){const r=e('tr');for(const item of row)r.append(e('td',item));tbody.append(r);}
      table.append(thead,tbody);wrap.append(table);container.append(wrap);
    }
    const portfolio=$('portfolio');
    if(portfolio){
      const card=panel('Mina simulerade aktier');
      renderTable(card,['Aktie','Antal','Köp USD','Senast USD','Utveckling'],items.map(h=>[h.ticker,h.quantity,h.open_usd.toFixed(2),h.mark_usd.toFixed(2),cash(h.pnl_sek)]));
      card.append(e('p',note,'caption'));
      const anchor=portfolio.querySelector('article.panel');
      if(anchor)anchor.before(card);else portfolio.append(card);
    }
    const trade=$('trades');
    if(trade){
      const card=panel('Simulerade köp · 9 november');
      renderTable(card,['Aktie','Antal','Antagen köpkurs (USD)','Värde SEK'],items.map(h=>[h.ticker,h.quantity,h.open_usd.toFixed(2),kr(h.invested_sek)]));
      card.append(e('p','Startscenario separat från kontots faktiska orderjournal. '+note,'caption'));
      trade.querySelector('article.panel')?.before(card);
    }
    const stats=$('statistics');
    if(stats){
      const card=panel('Simulerad utveckling sedan öppningen 9 november');
      card.append(e('p',kr(nav)+' · '+pc(percent)),e('p',note,'caption'));
      stats.querySelector('article.panel')?.before(card);
    }
  }catch(error){/* Original app remains available and unchanged if reconstruction is unavailable. */}
})();