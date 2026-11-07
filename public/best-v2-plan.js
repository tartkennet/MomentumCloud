(function(root){'use strict';
const money=x=>Math.round(x*100)/100;
const valid=x=>Number.isFinite(x)&&x>0;
const caps={ticker:15,cluster:35};
const sum=(a,f)=>a.reduce((s,x)=>s+f(x),0);
function buyCost(q,p,fx){if(!q)return 0;const n=q*p*1.02;return Math.ceil((n+Math.max(1,n*.0025)+n*.004)*fx*100)/100;}
function minimums(rows,fx){const cents=r=>Math.round(buyCost(1,r.price,fx)*100);const total=sum(rows,cents);const capital=Math.max(total,...Object.entries(caps).flatMap(([key,cap])=>rows.map(r=>Math.ceil(sum(rows.filter(x=>x[key]===r[key]),cents)*100/cap))));return {total:total/100,capital:capital/100};}
function allocate(rows,capital,fx){for(const r of rows){r.target=1;r.reservedTarget=buyCost(1,r.price,fx);}let remain=1,open=[...rows];const weights={};while(open.length){const total=sum(open,r=>1/Math.max(.20,r.vol63)/Math.sqrt(rows.filter(x=>x.sector===r.sector).length));const clipped=open.filter(r=>remain/(Math.max(.20,r.vol63)*Math.sqrt(rows.filter(x=>x.sector===r.sector).length)*total)>.15);if(!clipped.length){for(const r of open)weights[r.ticker]=remain/(Math.max(.20,r.vol63)*Math.sqrt(rows.filter(x=>x.sector===r.sector).length)*total);break;}for(const r of clipped){weights[r.ticker]=.15;remain-=.15;}open=open.filter(r=>!clipped.includes(r));}
for(const r of rows){let low=1,high=Math.max(1,Math.floor(capital*weights[r.ticker]/(r.price*fx*1.02)));while(low<high){const mid=low+Math.ceil((high-low)/2);r.reservedTarget=buyCost(mid,r.price,fx);const fits=sum(rows,x=>x.reservedTarget)<=capital+.001&&Object.entries(caps).every(([key,cap])=>sum(rows.filter(x=>x[key]===r[key]),x=>x.reservedTarget)<=capital*cap/100+.001);if(fits)low=mid;else high=mid-1;}r.target=low;r.reservedTarget=buyCost(low,r.price,fx);}
while(true){const feasible=[];for(const r of rows){const before=r.reservedTarget;r.reservedTarget=buyCost(r.target+1,r.price,fx);const fits=sum(rows,x=>x.reservedTarget)<=capital+.000001&&Object.entries(caps).every(([key,cap])=>sum(rows.filter(x=>x[key]===r[key]),x=>x.reservedTarget)<=capital*cap/100+.000001);r.reservedTarget=before;if(fits)feasible.push(r);}if(!feasible.length)break;feasible.sort((a,b)=>(weights[b.ticker]-b.reservedTarget/capital)-(weights[a.ticker]-a.reservedTarget/capital)||(a.ticker<b.ticker?1:-1));const r=feasible[0];r.target++;r.reservedTarget=buyCost(r.target,r.price,fx);}}
function plan(report,settings,now=new Date()){
 const {capital,cash}=settings;const snapshot=report.signal;const fx=report.fx?.usdsek;
 if((capital!==null&&!valid(capital))||!Number.isFinite(cash)||cash<0)throw Error('Ogiltigt kapital eller kassa.');
 const time=Date.parse(report.generated_at),quote=Date.parse(report.price_as_of);
 const current=report.delivery?.verified===true&&!report.operations?.delayed&&snapshot?.version==='best-signal-v2'&&snapshot.market_verified&&snapshot.quotes_as_of===report.price_as_of&&Number.isFinite(time)&&time<=+now&&+now-time<=4*86400000&&Number.isFinite(quote)&&quote<=+now&&+now-quote<=5*86400000;
 const risk=current&&typeof report.risk_on==='boolean'?report.risk_on:null;
 const month=new Intl.DateTimeFormat('sv-SE',{timeZone:'America/New_York',year:'numeric',month:'2-digit'}).format(now);
 const selection=snapshot?.selection;
 const ready=risk===true&&snapshot.selection_verified&&selection?.month===month&&selection.rows?.length===10;
 const rows=ready?selection.rows.map((r,i)=>({...r,rank:i+1,price:snapshot.quotes[r.ticker],current:0,buy:0,reserved:0})):[];
 const live=rows.length===10&&valid(fx)&&rows.every(r=>valid(r.price));const minimum=live?minimums(rows,fx):null;
 const use=capital??(minimum?Math.max(25000,minimum.capital):null);const gap=minimum&&capital!==null?money(Math.max(0,minimum.capital-capital)):0;
 const cashGap=minimum?money(Math.max(0,minimum.total-cash)):null;
 if(live){allocate(rows,Math.max(use,minimum.capital),fx);if(!gap&&!cashGap){let available=cash;for(const r of rows){r.buy=1;r.reserved=buyCost(1,r.price,fx);available=money(available-r.reserved);}for(const r of rows){const rest=rows.filter(x=>x!==r);let low=1,high=r.target;while(low<high){const mid=low+Math.ceil((high-low)/2),cost=buyCost(mid,r.price,fx);if(cost-r.reserved<=available+.001&&Object.entries(caps).every(([key,cap])=>cost+sum(rest.filter(x=>x[key]===r[key]),x=>x.reserved)<=use*cap/100+.001))low=mid;else high=mid-1;}const cost=buyCost(low,r.price,fx);available=money(available+r.reserved-cost);r.buy=low;r.reserved=cost;}}}
 for(const r of rows){r.targetCost=live?buyCost(r.target,r.price,fx):null;r.reason=!live?'Verifierad kurs saknas':r.buy?'Målberäkning, inte ett genomfört innehav.':'Kapital eller kassa räcker inte till tio positioner.';}
 return {risk,selectionReady:ready,rows,targetCount:rows.length,minimumTotal:minimum?.total??null,minimumCapital:minimum?.capital??null,suggestedCapital:minimum?Math.max(25000,minimum.capital):null,capitalShortfall:gap,cashShortfall:cashGap,fx};}
const api={plan,buyCost,minimums};if(typeof module==='object'&&module.exports)module.exports=api;else root.BestV2Plan=api;
})(globalThis);
