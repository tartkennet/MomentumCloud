const SOURCE='https://raw.githubusercontent.com/tartkennet/MomentumCloud/refs/heads/best-observed-snapshots/public/data/momentum-best.json';
const BASELINE='https://raw.githubusercontent.com/tartkennet/MomentumCloud/refs/heads/quality-observed-snapshots/public/data/quality-earnings.json';
const MODEL='momentum10-best-v1';
function nextAttempt(from){const t=new Date(from);for(let i=0;i<9;i++){const d=new Date(Date.UTC(t.getUTCFullYear(),t.getUTCMonth(),t.getUTCDate()+i));if([0,6].includes(d.getUTCDay()))continue;for(const[h,m]of[[8,22],[14,52],[15,52],[22,22]]){const x=new Date(d);x.setUTCHours(h,m,0,0);if(x>t)return x.toISOString();}}throw Error('No attempt');}
function validate(d){const p=d.paper;if(d.model!==MODEL||p?.model!==MODEL||p.live_approved!==false||p.broker_orders_enabled!==false||!Array.isArray(p.positions)||!Array.isArray(p.trades)||!Array.isArray(p.curve)||p.positions.some(x=>x.ticker==='SPY')||p.trades.some(x=>x.ticker==='SPY'))throw Error('Invalid BEST identity');return d;}
async function fetchJson(url){const r=await fetch(url+'?minute='+Math.floor(Date.now()/60000),{signal:AbortSignal.timeout(7000),headers:{'cache-control':'no-cache'}});if(!r.ok)throw Error('Delivery');return r.json();}
function comparison(best,legacy){const p=legacy?.avanza_paper;if(p?.model!=='avanza10-observed-paper-v1'||p.live_approved!==false||p.broker_orders_enabled!==false)return {status:'BASELINE_UNAVAILABLE',rows:[]};const dates=new Map((p.curve||[]).map(x=>[x.date,x]));const common=(best.curve||[]).filter(x=>dates.has(x.date)&&Number.isFinite(x.nav_sek)&&Number.isFinite(dates.get(x.date).nav_sek));if(common.length<2||!best.paper_started||!p.paper_started)return {status:'AWAITING_COMMON_OBSERVED_DATES',rows:[]};const a=common[0].nav_sek,b=dates.get(common[0].date).nav_sek;return {status:'OBSERVED_COMMON_CLOSES',from:common[0].date,rows:common.map(x=>({date:x.date,best_index:100*x.nav_sek/a,avanza_index:100*dates.get(x.date).nav_sek/b})),convention:'Net NAV indexed at first common observed close; excludes earlier costs/returns.'};}
module.exports=async(_req,res)=>{res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');try{
 const [own,old]=await Promise.allSettled([fetchJson(SOURCE),fetchJson(BASELINE)]);if(own.status!=='fulfilled')throw Error('BEST delivery unavailable');const d=validate(own.value);const p=d.paper;
 const stamp=Date.parse(d.generated_at),next=nextAttempt(d.generated_at);const delayed=Date.now()>Date.parse(next)+45*60000;
 const fresh=Number.isFinite(stamp)&&stamp<=Date.now()&&Date.now()-stamp<4*86400000&&!delayed;
 const verified=fresh&&d.technical_readiness?.status==='PASS'&&p.statistics_audit?.status==='PASS'&&p.audits?.strategy?.status==='PASS';
 const signal={...d.signal,quotes:Object.fromEntries((d.signal?.selection?.rows||[]).map(r=>[r.ticker,d.signal.quotes[r.ticker]]))};
 const light=r=>{const {returns63,...rest}=r;return rest;};if(signal.selection)signal.selection={...signal.selection,rows:signal.selection.rows.map(light)};
 const {excluded_names,...diagnostics}=d.diagnostics||{};diagnostics.excluded_name_count=excluded_names?.length;
 const body={model:MODEL,generated_at:d.generated_at,price_as_of:d.price_as_of,risk_on:d.risk_on,fx:d.fx,signal,
  diagnostics,strong_pool:(d.strong_pool||[]).map(light),formation_skips:d.formation_skips,provenance:d.provenance,journal_evidence:d.journal_evidence,
  live_approved:false,broker_orders_enabled:false,economic_status:'NO_GO_INSUFFICIENT_EVIDENCE',experiment_label:'PAPER_EXPERIMENT',
  delivery:{verified:fresh,source:'independent_best_prospective_journal'},operations:{delayed,next_attempt:next},errors:d.errors||[],technical_readiness:d.technical_readiness,
  paper:{...p,automation_verified:verified,effective_status:verified?p.status:'BLOCKED',delivery_blockers:verified?[]:['BEST_AUTOMATION_OR_DELIVERY_NOT_VERIFIED']},
  promotion_ready:verified&&d.technical_readiness.funded===true&&p.paper_started===true&&p.positions.length===10&&p.positions.every(x=>Number.isInteger(x.quantity)&&x.quantity>=1),
  baseline_comparison:comparison(p,old.status==='fulfilled'?old.value:null)};
 return res.status(fresh?200:503).json(body);
 }catch{return res.status(503).json({model:MODEL,signal:{},delivery:{verified:false},errors:['BEST-journalen kan inte hämtas eller verifieras.'],promotion_ready:false,live_approved:false,broker_orders_enabled:false,
  paper:{model:MODEL,status:'BLOCKED',effective_status:'BLOCKED',automation_verified:false,paper_started:false,initial_sek:null,positions:[],trades:[],curve:[],blockers:['BEST_AUTOMATION_OR_DELIVERY_NOT_VERIFIED']}});}};
module.exports.validate=validate;module.exports.comparison=comparison;
