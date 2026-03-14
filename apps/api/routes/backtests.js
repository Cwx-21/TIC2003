import express from "express";
import { QueryTypes } from "sequelize";
import sequelize, { hasDbConfig } from "../database/index.js";
import { parseLimit, parsePositiveInt, parseString } from "../utils/query.js";

const router = express.Router();

router.get("/", async (req, res) => {
  if (!hasDbConfig || !sequelize) {
    return res.status(500).json({ error: "DATABASE_URL is not configured" });
  }

  // /api/backtests?limit=10&status=completed&id=9001
  const limit = parseLimit(req.query.limit, 50, 200);
  /* 
  trims whitespace
  returns null if empty or invalid
  */
  const status = parseString(req.query.status);
  const id = parsePositiveInt(req.query.id);

  const conditions = [];
  const replacements = { limit };

  if (status) {
    conditions.push("br.status = :status");
    replacements.status = status;
  }

  if (id) {
    conditions.push("br.id = :id");
    replacements.id = id;
  }

  const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";

  const query = `
    SELECT
      br.id,
      br.name,
      br.dataset_source,
      br.status,
      br.start_time,
      br.end_time,
      br.parameters,
      br.total_rows,
      br.processed_rows,
      br.error_count,
      br.created_at,
      COALESCE(c.correlation_points, 0) AS correlation_points,
      c.avg_divergence,
      c.avg_sentiment,
      c.avg_price_change_pct,
      COALESCE(a.alert_count, 0) AS alert_count,
      a.latest_alert_at
    FROM backtest_runs br
    LEFT JOIN (
      SELECT
        backtest_id,
        COUNT(*)::int AS correlation_points,
        AVG(sentiment_price_divergence) AS avg_divergence,
        AVG(avg_sentiment) AS avg_sentiment,
        AVG(price_change_pct) AS avg_price_change_pct
      FROM sentiment_price_correlation
      WHERE backtest_id IS NOT NULL
      GROUP BY backtest_id
    ) c ON c.backtest_id = br.id
    LEFT JOIN (
      SELECT
        backtest_id,
        COUNT(*)::int AS alert_count,
        MAX(event_timestamp) AS latest_alert_at
      FROM alerts
      WHERE backtest_id IS NOT NULL
      GROUP BY backtest_id
    ) a ON a.backtest_id = br.id
    ${whereClause}
    ORDER BY br.created_at DESC
    LIMIT :limit;
  `;

  try {
    const rows = await sequelize.query(query, {
      type: QueryTypes.SELECT,
      replacements,
    });
    return res.json({ data: rows });
  } catch (error) {
    console.error("Failed to load backtests", error);
    return res.status(500).json({ error: "Failed to load backtests" });
  }
});

export default router;
