const fs = require("node:fs/promises");
const path = require("node:path");

const MODEL = "momentum-diversified-regime-research-v1";
const COHORT = "portfolio-global-regime-forward-v1-20261029";
const SOURCE = "https://raw.githubusercontent.com/tartkennet/MomentumCloud/refs/heads/h3-observed-snapshots/public/data/h3.json";

function validate(data) {
  if (data.schema_version !== 1 || data.model !== MODEL || data.cohort !== COHORT ||
      data.live_approved !== false || data.broker_orders_enabled !== false ||
      data.source_fingerprint !== "e89ab72e0354d1983a4055ec330cc8b5234cf73615cdf1805bb0bb2517c09921") {
    throw new Error("Invalid H3 observation identity");
  }
  return data;
}

module.exports = async function handler(_request, response) {
  response.setHeader("Content-Type", "application/json; charset=utf-8");
  response.setHeader("Cache-Control", "no-store");
  try {
    const upstream = await fetch(SOURCE, {signal: AbortSignal.timeout(5000), headers: {accept:"application/json", "cache-control":"no-cache"}});
    if (!upstream.ok) throw new Error("Observation delivery failed");
    const data = validate(await upstream.json());
    const next = Date.parse(data.operations?.next_expected_attempt_at);
    const grace = Number(data.operations?.delay_grace_minutes || 90) * 60000;
    const delayed = Number.isFinite(next) && Date.now() > next + grace;
    if (delayed) {
      data.status = "MONITOR_DELAYED";
      data.pending_intentions = null;
      data.operations.errors = [...(data.operations.errors || []), "Nästa schemalagda uppföljning har inte publicerats i tid."];
    }
    data.delivery = {source:"observed_snapshot_branch", verified:!delayed, checked_at:new Date().toISOString()};
    return response.status(200).json(data);
  } catch (_error) {
    let data;
    try { data = validate(JSON.parse(await fs.readFile(path.join(process.cwd(), "public/data/h3.json"), "utf8"))); }
    catch { data = {model:MODEL, cohort:COHORT, metrics:null, holdings:[], curve:[], sessions:0, live_approved:false, broker_orders_enabled:false}; }
    data.status = "DELIVERY_BLOCKED";
    data.pending_intentions = null;
    data.delivery = {source:"bundled_fallback", verified:false, checked_at:new Date().toISOString()};
    data.operations = {...data.operations, errors:["Den senaste H3-journalen kunde inte hämtas. Eventuella värden nedan är äldre, inte aktuella signaler."]};
    return response.status(503).json(data);
  }
};

module.exports.validate = validate;
