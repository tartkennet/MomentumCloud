const fs = require("node:fs");
const path = require("node:path");

module.exports = function handler(_request, response) {
  const snapshot = path.join(process.cwd(), "public", "data", "dashboard.json");
  const available = fs.existsSync(snapshot);
  response.setHeader("Cache-Control", "no-store");
  response.status(available ? 200 : 503).json({
    status: available ? "ok" : "waiting",
    snapshot: available,
  });
};
