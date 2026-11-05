const quality = require('./quality');
const MODEL = 'avanza10-observed-paper-v1';
function validatePaper(p) {
  if (!p || p.model !== MODEL || p.mode !== 'PAPER_ONLY' || p.live_approved !== false ||
      p.broker_orders_enabled !== false || !Array.isArray(p.trades) || !Array.isArray(p.positions) ||
      !Array.isArray(p.curve) || p.positions.length > 10 ||
      p.positions.some(x => x.ticker === 'SPY') ||
      p.trades.some(x => x.ticker === 'SPY')) throw Error('Invalid Avanza account');
  return p;
}
module.exports = async (req, res) => {
  let report, code;
  await quality(req, {setHeader() {}, status(value) {code = value; return this;}, json(value) {report = value;}});
  let paper;
  try {paper = validatePaper(report.avanza_paper);} catch {
    paper = {model: MODEL, mode: 'PAPER_ONLY', live_approved: false, broker_orders_enabled: false,
      status: 'BLOCKED', blockers: ['AUTOMATIC_ACCOUNT_NOT_YET_VERIFIED'], paper_started: false,
      positions: [], trades: [], curve: [], decisions: [], initial_sek: 20000};
  }
  const verified = code === 200 && report.delivery?.verified === true && !report.operations?.delayed;
  const paperCurrent = verified && Number.isFinite(Date.parse(paper.generated_at)) &&
    Date.parse(paper.generated_at) <= Date.now() && Date.now() - Date.parse(paper.generated_at) < 4 * 86400000 &&
    paper.audits?.strategy?.status === 'PASS' && paper.audits?.benchmark?.status === 'PASS';
  const result = {model: MODEL, generated_at: report.generated_at, price_as_of: report.price_as_of,
    risk_on: report.risk_on, fx: report.fx, avanza10: report.avanza10,
    delivery: report.delivery, operations: report.operations, errors: report.errors || [],
    live_approved: false, broker_orders_enabled: false, economic_status: 'NO_GO_INSUFFICIENT_EVIDENCE',
    paper: {...paper, automation_verified: paperCurrent, effective_status: paperCurrent ? paper.status : 'BLOCKED',
      delivery_blockers: paperCurrent ? [] : ['AUTOMATION_OR_DELIVERY_NOT_VERIFIED']}};
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  return res.status(verified ? 200 : 503).json(result);
};
module.exports.validatePaper = validatePaper;
