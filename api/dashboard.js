const fs = require("node:fs/promises");
const path = require("node:path");

module.exports = async function handler(_request, response) {
  try {
    const file = path.join(process.cwd(), "public", "data", "dashboard.json");
    const payload = await fs.readFile(file, "utf8");
    response.setHeader("Content-Type", "application/json; charset=utf-8");
    response.setHeader("Cache-Control", "public, max-age=60, stale-while-revalidate=300");
    response.status(200).send(payload);
  } catch (_error) {
    response.status(503).json({error: "No successful production snapshot is available yet"});
  }
};
