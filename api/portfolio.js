const fs=require('node:fs/promises');
const path=require('node:path');
const {validate:validateH3}=require('./h3');
const BASE='https://raw.githubusercontent.com/tartkennet/MomentumCloud/refs/heads/h3-observed-snapshots/public/data/';
const FP='e89ab72e0354d1983a4055ec330cc8b5234cf73615cdf1805bb0bb2517c09921';
function validate(data){
  if(data.schema_version!==1||data.source_fingerprint!==FP||data.live_approved!==false||data.broker_orders_enabled!==false||data.start_capital_sek!==100000||data.method!=='PROPORTIONAL_VIRTUAL_UNITS'||!Number.isFinite(Date.parse(data.generated_at)))throw Error('Invalid display identity');
  if(data.metrics&&(!data.anchor||!Number.isFinite(data.metrics.nav_sek)||!Number.isFinite(data.metrics.spy_nav_sek)))throw Error('Invalid SEK valuation');
  return data;
}
async function remote(file){
  const r=await fetch(`${BASE}${file}?minute=${Math.floor(Date.now()/60000)}`,{signal:AbortSignal.timeout(6000),headers:{'cache-control':'no-cache'}});
  if(!r.ok)throw Error('Delivery unavailable');return r.json();
}
module.exports=async(_req,res)=>{
  res.setHeader('Content-Type','application/json; charset=utf-8');res.setHeader('Cache-Control','no-store');
  try{
    const [data,h3]=await Promise.all([remote('h3-display.json').then(validate),remote('h3.json').then(validateH3)]);
    const errors=[...(data.errors||[])];
    const late=Date.now()>Date.parse(h3.operations.next_expected_attempt_at)+90*60000;
    const sync=data.source_as_of===h3.as_of;
    if(!sync)errors.push('En ny H3-session har registrerats. SEK-värderingen inväntar synkronisering.');
    if(late)errors.push('Den schemalagda H3-insamlingen är försenad.');
    errors.push(...h3.operations.errors);
    const now=new Date(),sessionHours=now.getUTCDay()>0&&now.getUTCDay()<6&&now.getUTCHours()>=13&&now.getUTCHours()<23;
    const valuationLate=sessionHours&&Date.now()-Date.parse(data.generated_at)>60*60000;
    if(valuationLate)errors.push('Kursuppföljningen är försenad. Senast verifierade värdering visas med datum.');
    if(errors.length)data.pending_intentions=null;
    data.errors=errors;
    data.delivery={verified:true,synchronized:sync,valuation_delayed:valuationLate,checked_at:now.toISOString()};
    data.h3={status:h3.status,as_of:h3.as_of,sessions:h3.sessions,generated_at:h3.generated_at,
      next_attempt:h3.operations.next_expected_attempt_at,validation:h3.validation,historical:h3.historical,
      execution:h3.execution,errors:h3.operations.errors,journal:h3.journal_evidence};
    return res.status(200).json(data);
  }catch{
    let data;try{data=validate(JSON.parse(await fs.readFile(path.join(process.cwd(),'public/data/h3-display.json'),'utf8')))}
    catch{data={start_capital_sek:100000,metrics:null,sessions:0,positions:[],trades:[],curve:[],live_approved:false,broker_orders_enabled:false}}
    data.status='DELIVERY_BLOCKED';data.pending_intentions=null;data.delivery={verified:false};
    data.errors=['Senaste portföljunderlaget kunde inte hämtas. Eventuella tidigare värden är inte aktuella signaler.'];
    return res.status(503).json(data);
  }
};
module.exports.validate=validate;
