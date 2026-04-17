/**
 * Alerts Route — GET /api/alerts
 *
 * Returns alert records filtered by any combination of asset symbol,
 * alert type, severity, backtest ID, and session ID. Conditions are
 * composed dynamically so that absent filters do not narrow the result set.
 *
 * Query Parameters:
 *   limit        {number}  Max rows to return (default 100, max 500).
 *   asset_symbol {string}  Filter by asset ticker (e.g., 'BTC').
 *   alert_type   {string}  Filter by type ('divergence', 'volume_spike', etc.).
 *   severity     {string}  Filter by severity ('info', 'warning', 'critical').
 *   backtest_id  {number}  Filter by backtest run ID.
 *   session_id   {number}  Filter by live session ID.
 */

import express from "express";
import { QueryTypes } from "sequelize";
import sequelize, { hasDbConfig } from "../database/index.js";
import { parseLimit, parsePositiveInt, parseString } from "../utils/query.js";

const router = express.Router();

/**
 * GET /api/alerts
 * Returns paginated alert records ordered by most recent event timestamp.
 */
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

  // Build WHERE clause dynamically — only active filters are appended
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
