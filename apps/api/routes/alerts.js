import express from "express";
import { QueryTypes } from "sequelize";
import sequelize, { hasDbConfig } from "../database/index.js";
import { parseLimit, parsePositiveInt, parseString } from "../utils/query.js";

const router = express.Router();

router.get("/", async (req, res) => {
  if (!hasDbConfig || !sequelize) {
    return res.status(500).json({ error: "DATABASE_URL is not configured" });
  }

  const limit = parseLimit(req.query.limit, 100, 500);
  const assetSymbol = parseString(req.query.asset_symbol);
  const alertType = parseString(req.query.alert_type);
  const severity = parseString(req.query.severity);
  const backtestId = parsePositiveInt(req.query.backtest_id);
  const sessionId = parsePositiveInt(req.query.session_id);

  const conditions = [];
  const replacements = { limit };

  if (assetSymbol) {
    conditions.push("asset_symbol = :assetSymbol");
    replacements.assetSymbol = assetSymbol;
  }

  if (alertType) {
    conditions.push("alert_type = :alertType");
    replacements.alertType = alertType;
  }

  if (severity) {
    conditions.push("severity = :severity");
    replacements.severity = severity;
  }

  if (backtestId) {
    conditions.push("backtest_id = :backtestId");
    replacements.backtestId = backtestId;
  }

  if (sessionId) {
    conditions.push("session_id = :sessionId");
    replacements.sessionId = sessionId;
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const query = `
    SELECT
      id,
      asset_symbol,
      alert_type,
      severity,
      message,
      details,
      event_timestamp,
      backtest_id,
      session_id,
      is_acknowledged,
      created_at
    FROM alerts
    ${whereClause}
    ORDER BY event_timestamp DESC
    LIMIT :limit;
  `;

  try {
    const rows = await sequelize.query(query, {
      type: QueryTypes.SELECT,
      replacements,
    });
    return res.json({ data: rows });
  } catch (error) {
    console.error("Failed to load alerts", error);
    return res.status(500).json({ error: "Failed to load alerts" });
  }
});

export default router;
