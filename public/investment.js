(function(){
'use strict';
const $=id=>document.getElementById(id);
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const n=(x,d=2)=>finite(x)?x.toLocaleString('sv-SE',{maximumFractionDigits:d,minimumFractionDigits:d}):'—';
const money=x=>finite(x)?n(x,0)+' kr':'—';
const usd=x=>finite(x)?n(x,2)+' USD':'—';
const pct=x=>finite(x)?(x>0?'+':'')+n(x,2)+' %':'—';
const cls=x=>finite(x)?x>=0?'positive':'negative':'';
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stamp=x=>x&&Number.isFinite(Date.parse(x))?new Date(x).toLocaleString('sv-SE',{timeZone:'Europe/Stockholm',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}):'—';
const date=x=>x?new Date(x+'T12:00:00Z').toLocaleDateString('sv-SE',{day:'numeric',month:'short',year:'numeric'}):'—';
let current=null,period='all',filter='all',tab='overview',chartRows=[];
function stat(label,value,detail='',color=''){return `<article class="summary-stat"><span>${esc(label)}</span><strong class="${color}">${esc(value)}</strong>${detail?`<small>${esc(detail)}</small>`:''}</article>`}
function empty(title,copy){return `<div class="empty"><strong>${esc(title)}</strong><small>${esc(copy)}</small></div>`}
function row(label,value){return `<div class="detail-row"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`}
function mode(mark){return mark?.mode==='REALTIME'?`Realtidskälla · ${stamp(mark.at)}`:mark?.mode==='DELAYED'?`Fördröjd visning · datatid ${stamp(mark.at)}`:mark?.mode==='CLOSE'?`Stängningskurs · ${date(mark.session)}`:'Kurs saknas'}
function holdings(rows,detail=false){
 if(!rows?.length)return empty('Portföljen är redo att börja.','Innehav visas först när H3:s första simulerade köp har registrerats.');
 return rows.map(p=>`<article class="holding"><div class="holding-header"><span class="ticker-icon">${esc(p.ticker.slice(0,4))}</span><div class="holding-name"><b>${esc(p.ticker)}</b><span>${p.ticker==='SPY'?'S&P 500 · ETF':'H3 momentum'} · ${n(p.weight_pct,1)} %</span></div><div class="holding-value"><b>${money(p.value_sek)}</b><span class="${cls(p.pnl_sek)}">${finite(p.pnl_sek)?money(p.pnl_sek)+' · '+pct(p.return_pct):'Inköpsvärde saknas'}</span></div></div>${detail?`<div class="holding-grid"><div><span>Simulerat antal</span><b>${n(p.quantity,4)}</b></div><div><span>Snittköp inkl. avgift</span><b>${usd(p.average_cost_usd)}</b></div><div><span>Aktuell kurs</span><b>${usd(p.mark?.usd)}</b></div><div><span>Inköpsvärde i SEK</span><b>${money(p.cost_sek)}</b></div></div><p class="mark-note">${esc(mode(p.mark))} · fraktionella visningsenheter</p>`:''}</article>`).join('');
}
function tradeLabel(side){return ({BUY:'Köpt',SELL:'Sålt',BUY_CANCELLED_NO_OPEN:'Köp annullerat'})[side]||'Företagshändelse'}
function trades(rows,detail=false){
 if(!rows?.length)return empty('Här börjar din affärshistorik.','Köp och försäljningar dyker upp automatiskt när verkliga H3-sessioner har bokförts.');
 return rows.map(t=>`${detail?'<article class="trade-item">':''}<div class="trade"><span class="trade-icon ${t.side==='SELL'?'sell':''}">${t.side==='BUY'?'↙':t.side==='SELL'?'↗':'·'}</span><div class="trade-info"><b>${tradeLabel(t.side)} ${esc(t.ticker)}</b><span>${n(t.quantity,4)} st · ${t.at?stamp(t.at):date(t.date)}</span></div><div class="trade-money"><b>${money(t.notional_sek)}</b><span>${usd(t.price)} / aktie</span></div></div>${detail?`<p class="caption">Avgift ${finite(t.fee_sek)?money(t.fee_sek):usd(t.fee_usd)} · signal ${esc(t.signal_date||'företagshändelse')}<br>${t.at?'Simulerat vid ordinarie USA-öppning':'Företagshändelsens datum'} · ${t.fx?'USD/SEK '+n(t.fx.usdsek,4)+' ('+date(t.fx.date)+')':'Växelkurs saknas'}</p></article>`:''}`).join('');
}
function chart(rows,width=800){
 if(rows.some(r=>!finite(r.nav_sek)||!finite(r.spy_sek)))return '<div class="chart-empty"><h3>En del valutaunderlag saknas.</h3><p>Ingen ofullständig SEK-kurva visas. De ursprungliga H3-observationerna är bevarade.</p></div>';
 const valid=rows.filter(r=>finite(r.nav_sek)&&finite(r.spy_sek));
 if(valid.length<2)return '<div class="chart-empty"><span class="empty-symbol"><svg><use href="#i-stats"/></svg></span><h3>Första kapitlet börjar snart.</h3><p>Här växer din portföljkurva fram när riktiga H3-sessioner har registrerats. Ingen historisk avkastning fylls i i förväg.</p></div>';
 const w=Math.max(280,width),h=285,left=62,right=12,top=24,bottom=45;
 const values=valid.flatMap(r=>[r.nav_sek,r.spy_sek]),min=Math.min(...values),max=Math.max(...values),gap=(max-min)*.12||100;
 const low=min-gap,high=max+gap;
 const x=i=>left+i/(valid.length-1)*(w-left-right),y=v=>top+(high-v)/(high-low)*(h-top-bottom);
 const line=key=>valid.map((r,i)=>`${i?'L':'M'}${x(i).toFixed(2)},${y(r[key]).toFixed(2)}`).join(' ');
 const grid=[0,1,2,3].map(i=>{const value=low+(high-low)*i/3,Y=y(value);return `<line class="gridline" x1="${left}" x2="${w-right}" y1="${Y}" y2="${Y}"/><text x="${left-10}" y="${Y+5}" text-anchor="end">${n(value/1000,0)} tkr</text>`}).join('');
 const start=date(valid[0].date).replace(/ 20\d\d$/,''),end=date(valid.at(-1).date).replace(/ 20\d\d$/,'');
 return `<svg class="value-chart" viewBox="0 0 ${w} ${h}" role="img" aria-label="Registrerade H3- och SPY-portföljvärden i SEK"><defs><linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#18aa91" stop-opacity=".16"/><stop offset="1" stop-color="#18aa91" stop-opacity="0"/></linearGradient></defs>${grid}<path fill="url(#chart-fill)" d="${line('nav_sek')} L${x(valid.length-1)},${h-bottom} L${left},${h-bottom}Z"/><path class="spyline" d="${line('spy_sek')}"/><path class="navline" d="${line('nav_sek')}"/><circle class="chart-point" cx="${x(valid.length-1)}" cy="${y(valid.at(-1).nav_sek)}" r="5"/><text x="${left}" y="${h-12}">${esc(start)}</text><text x="${w-right}" y="${h-12}" text-anchor="end">${esc(end)}</text><rect class="chart-touch" x="${left}" y="${top}" width="${w-left-right}" height="${h-top-bottom}"/></svg><div class="chart-tooltip" hidden></div>`;
}
function renderChart(){
 if(!current)return;
 let rows=current.curve||[];
 if(period!=='all'&&rows.length){const last=new Date(rows.at(-1).date+'T12:00:00Z');last.setUTCMonth(last.getUTCMonth()-(period==='1m'?1:3));rows=rows.filter(r=>r.date>=last.toISOString().slice(0,10));}
 chartRows=rows.filter(r=>finite(r.nav_sek)&&finite(r.spy_sek));
 $('main-chart').innerHTML=chart(rows,$('main-chart').clientWidth||800);
 const hit=$('main-chart').querySelector('.chart-touch');
 if(hit){hit.addEventListener('pointermove',event=>{const rect=hit.getBoundingClientRect(),ratio=Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)),r=chartRows[Math.round(ratio*(chartRows.length-1))];const tip=$('main-chart').querySelector('.chart-tooltip');tip.hidden=false;tip.textContent=`${date(r.date)} · H3 ${money(r.nav_sek)} · SPY ${money(r.spy_sek)}`});hit.addEventListener('pointerleave',()=>{$('main-chart').querySelector('.chart-tooltip').hidden=true});}
}
function displayTrades(){if(!current)return;const query=$('trade-search').value.trim().toUpperCase();const rows=(current.trades||[]).slice().reverse().filter(t=>(filter==='all'||t.side===filter)&&(!query||t.ticker.toUpperCase().includes(query)));$('all-trades').innerHTML=trades(rows,true);}
function statistics(rows){
 if(rows.some(r=>!finite(r.nav_sek)))return {dd:null,sharpe:null};
 const values=rows.filter(r=>finite(r.nav_sek)).map(r=>r.nav_sek);if(values.length<2)return {dd:null,sharpe:null};
 let peak=values[0],dd=0;for(const v of values){peak=Math.max(peak,v);dd=Math.min(dd,100*(v/peak-1))}
 const returns=values.slice(1).map((v,i)=>v/values[i]-1),mean=returns.reduce((a,b)=>a+b,0)/returns.length;
 const variance=returns.length>1?returns.reduce((s,x)=>s+(x-mean)**2,0)/(returns.length-1):0;
 return {dd,sharpe:variance?Math.sqrt(252)*mean/Math.sqrt(variance):null};
}
function render(d){
 current=d;const m=d.metrics,h=d.h3||{},positions=d.positions||[],all=d.trades||[],executed=all.filter(t=>['BUY','SELL'].includes(t.side));
 const errors=d.errors||[];$('connection-alert').hidden=!errors.length;$('connection-alert').textContent=errors.join(' ');
 $('value-label').textContent=m?'Senast verifierade portföljvärde':'Planerat startkapital';
 $('portfolio-value').innerHTML=finite(m?.nav_sek)?`${n(m.nav_sek,0)} <small>kr</small>`:'100 000 <small>kr</small>';
 $('portfolio-return').className='hero-return '+cls(m?.pnl_sek);
 $('portfolio-return').textContent=m?`${m.pnl_sek>0?'+':''}${money(m.pnl_sek)}  (${pct(m.return_pct)}) sedan start`:d.sessions?'SEK-värderingen inväntar verifierade kurser eller valuta':'Inväntar den första registrerade sessionen';
 $('portfolio-status').textContent=d.delivery?.verified===false?'Anslutningsproblem':errors.length?'Kontroll behövs':d.sessions?'Paper trading pågår':'Redo för första sessionen';
 const marks=positions.map(p=>p.mark).concat(d.quotes?.SPY?[d.quotes.SPY]:[]);
 const modes=new Set(marks.map(x=>x?.mode));const modeText=modes.has('REALTIME')?'Realtidskälla · hämtas var 15:e minut':modes.has('DELAYED')?'Fördröjd visning · hämtas var 15:e minut':modes.has('CLOSE')?'Senaste stängningskurser':'Kursunderlag inväntas';
 const newest=marks.map(x=>x?.session).filter(Boolean).sort().at(-1);const newestAt=marks.map(x=>x?.at).filter(Boolean).sort().at(-1);
 $('valuation-time').textContent=`${modeText}${newestAt?' · datatid '+stamp(newestAt):newest?' · '+date(newest):''} · hämtat ${stamp(d.generated_at)}`;
 const decision=d.latest_decision;$('risk-status').textContent=decision?(decision.risk_on?'RISK ON':'RISK OFF'):'Inväntar H3';
 $('risk-status').className=decision?.risk_on?'positive':'';
 $('risk-copy').textContent=decision?decision.risk_on?'H3:s senaste beslut tillåter exponering mot momentumaktier och SPY.':'H3:s senaste beslut söker skydd i kassa. Beslut fylls enligt den frysta modellen.':'Marknadsläget visas när H3 har registrerat sitt första beslut.';
 $('next-decision').textContent=stamp(h.next_attempt);
 $('summary-metrics').innerHTML=stat('H3 sedan start',pct(m?.return_pct),'SEK efter modellens kostnader',cls(m?.return_pct))+stat('S&P 500 via SPY',pct(m?.spy_return_pct),'Samma valutagrund',cls(m?.spy_return_pct))+stat('Skillnad mot SPY',finite(m?.edge_pct)?n(m.edge_pct)+' pp':'—','Procentenheter',cls(m?.edge_pct))+stat('Bokförda sessioner',n(d.sessions||0,0),'Verkligt insamlade observationer');
 $('portfolio-metrics').innerHTML=stat('Portföljvärde',money(m?.nav_sek))+stat('Resultat sedan start',money(m?.pnl_sek),'Inklusive dollarutveckling',cls(m?.pnl_sek))+stat('Aktieinnehav',n(positions.length,0))+stat('Referenskurs USD/SEK',n(d.fx?.usdsek,4),d.fx?date(d.fx.date):'Verifierad valutakurs saknas');
 $('positions-count').textContent=positions.length+' innehav';$('overview-holdings').innerHTML=holdings(positions.slice(0,4));$('all-holdings').innerHTML=holdings(positions,true);
 $('cash-value').textContent=money(m?.cash_sek);$('cash-note').textContent=m?`Kassan hålls i USD och är här omräknad till SEK. Fordringar: ${money(m.receivables_sek)}.`:'100 000 SEK är valt startkapital. Den registrerade kassan visas efter första sessionen och valutaförankringen.';
 $('overview-trades').innerHTML=trades(executed.slice(-3).reverse());$('export-trades').disabled=!all.length;displayTrades();renderChart();
 const s=statistics(d.curve||[]);$('stats-metrics').innerHTML=stat('Total avkastning',pct(m?.return_pct),'Separat SEK-visning',cls(m?.return_pct))+stat('Maximal nedgång',pct(s.dd),'Bokförda sessioner i SEK')+stat('Sharpe',n(s.sharpe),'Daglig · riskfri ränta 0')+stat('Simulerade affärer',n(executed.length,0),'Från den ursprungliga journalen');
 $('benchmark-comparison').innerHTML=m?`<div class="comparison"><div class="comparison-title"><b>H3 i SEK</b><strong class="${cls(m.return_pct)}">${pct(m.return_pct)}</strong></div><div class="comparison-track"><i style="width:${Math.max(3,Math.min(100,Math.abs(m.return_pct)/Math.max(Math.abs(m.return_pct),Math.abs(m.spy_return_pct),1)*100))}%"></i></div></div><div class="comparison spy"><div class="comparison-title"><b>SPY i SEK</b><strong class="${cls(m.spy_return_pct)}">${pct(m.spy_return_pct)}</strong></div><div class="comparison-track"><i style="width:${Math.max(3,Math.min(100,Math.abs(m.spy_return_pct)/Math.max(Math.abs(m.return_pct),Math.abs(m.spy_return_pct),1)*100))}%"></i></div></div>`:empty('Jämförelsen väntar på riktiga observationer.','H3 och SPY börjar på samma valutakonverterade startkapital.');
 $('data-details').innerHTML=row('Kurser',modeText)+row('Senaste kursdag',date(newest))+row('Kursens senaste datatid',newestAt?stamp(newestAt):'Daglig stängningskurs')+row('Värdering kontrollerad',stamp(d.generated_at))+row('H3 bokförd till',date(d.source_as_of))+row('Senaste H3-uppdatering',stamp(h.generated_at))+row('USD/SEK',d.fx?n(d.fx.usdsek,4)+' · '+date(d.fx.date):'Saknas')+row('Valutakälla','ECB:s dagliga referensfixing')+row('Realtidsrättigheter',d.capability?.realtime_verified?'Verifierade':'Inte verifierade')+row('Leverantörens fördröjning',d.capability?.provider_latency==='UNVERIFIED'?'Ej verifierad, se kursens datatid':'Se leverantörens tidsmärkning')+row('Livehandel','Avstängd');
 const v=h.validation||{};$('validation-details').innerHTML=`<p>${d.sessions||0} insamlade sessioner. ${v.observed_periods||0} av ${v.required_periods||30} fullständiga månadsperioder.</p><div class="progress-track"><i style="width:${Math.min(100,(v.observed_periods||0)/30*100)}%"></i></div><p>${v.remaining_periods??30} perioder återstår. Full finansiell prövning tidigast ${esc(v.earliest_assessment_month||'2029-05')}. Ett historiskt godkännande är inte en live-GO.</p><p class="caption">Status: ${esc(v.status||'COLLECTING')} · originalkonton i USD. Kostnader, likviditet och exekvering måste också kunna granskas. H3:s parametrar och GO-gränser är oförändrade.</p>`;
 const hist=h.historical?.metrics;$('historical-details').innerHTML=hist?`<p>Utvecklingsdata 2024-01-01–2026-10-28. Separat från din fiktiva portfölj.</p>${row('H3 historiskt',pct(hist.TotalReturn_pct))}${row('SPY historiskt',pct(hist.SPYTotalReturn_pct))}${row('Maximal nedgång',pct(hist.DailyMaxDrawdown_pct))}${row('Sharpe',n(hist.DailySharpe_zero_rf))}<p class="caption">Samtliga 40 historiska scenarier passerade. Detta är inte orörd out-of-sample-data eller tillstånd för riktig handel.</p>`:'Den historiska sammanfattningen är inte tillgänglig just nu.';
}
function selectTab(name){
 if(!['overview','portfolio','trades','stats','more'].includes(name))name='overview';tab=name;
 document.querySelectorAll('[data-panel]').forEach(p=>p.hidden=p.dataset.panel!==name);
 document.querySelectorAll('[data-tab]').forEach(b=>{const active=b.dataset.tab===name;b.classList.toggle('active',active);if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});
 history.replaceState(null,'','#'+name);window.scrollTo({top:0,left:0,behavior:'instant'});if(name==='overview')renderChart();
}
function setTheme(theme){document.documentElement.dataset.theme=theme;try{localStorage.setItem('momentum-theme',theme)}catch{}document.querySelector('meta[name="color-scheme"]').content=theme==='light'?'only light':'dark';document.querySelector('meta[name="theme-color"]').content=theme==='dark'?'#111e2a':'#f5f8fb';$('theme-toggle').setAttribute('aria-label',theme==='dark'?'Byt till ljust tema':'Byt till mörkt tema');$('theme-toggle').innerHTML=`<svg><use href="#i-${theme==='dark'?'sun':'moon'}"/></svg>`;}
async function load(){
 try{const response=await fetch('/api/portfolio',{cache:'no-store',signal:AbortSignal.timeout(12000)});const d=await response.json();if(d.start_capital_sek!==100000)throw Error('Invalid portfolio');render(d)}
 catch{$('connection-alert').hidden=false;$('connection-alert').textContent='Anslutningen till portföljen fungerar inte just nu. Tidigare värden är inte aktuella signaler. Vyn försöker automatiskt igen.';$('portfolio-status').textContent='Anslutningsproblem';}
}
function exportCSV(){if(!current?.trades?.length)return;const cells=v=>'"'+String(v??'').replace(/"/g,'""')+'"';const columns=['date','at','side','ticker','quantity','price','fee_usd','fee_sek','notional_sek','signal_date','time_basis'];const text='\uFEFF'+[columns.join(';'),...current.trades.map(t=>columns.map(k=>cells(t[k])).join(';'))].join('\r\n');const a=document.createElement('a'),url=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));a.href=url;a.download='MomentumCloud-H3-simulerade-affarer.csv';a.click();URL.revokeObjectURL(url);}
if(typeof module!=='undefined')module.exports={chart,statistics,esc,pct};
if(typeof document!=='undefined'){
 document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>selectTab(b.dataset.tab)));
 document.querySelectorAll('[data-goto]').forEach(b=>b.addEventListener('click',()=>selectTab(b.dataset.goto)));
 document.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>{period=b.dataset.period;document.querySelectorAll('[data-period]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',x===b?'true':'false')});renderChart()}));
 document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));displayTrades()}));
 $('trade-search').addEventListener('input',displayTrades);$('export-trades').addEventListener('click',exportCSV);$('refresh-data').addEventListener('click',load);
 $('theme-toggle').addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
 setTheme(document.documentElement.dataset.theme==='dark'?'dark':'light');selectTab(location.hash.slice(1)==='h3-paper'?'overview':location.hash.slice(1));load();setInterval(()=>{if(!document.hidden)load()},60000);window.addEventListener('resize',()=>{if(tab==='overview')renderChart()});document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
}
}());
